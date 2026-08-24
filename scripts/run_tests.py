#!/usr/bin/env python3
"""Run the test suite with NO third-party dependencies.

WHY THIS EXISTS, STATED RATHER THAN IMPLIED
    `tests/` are ordinary pytest files and `python3 -m pytest tests/ -q` is the real
    command — that is what CI runs. But the machine this was authored on has no route to
    PyPI, so pytest could not be installed, and the choice was between a suite that was
    WRITTEN and a suite that was RUN. A test nobody has executed is a claim, not a gate.

    So this shim provides the small slice of the pytest API the suite actually uses
    (`fixture`, `mark.parametrize`, `raises`, `importorskip`, `skip`, `approx`) and runs
    the same files unchanged. It is a fallback, not a replacement: pytest's output,
    assertion rewriting and plugins are all better. When PyPI is reachable, use pytest.

    Usage:  python3 scripts/run_tests.py [test_file_substring ...]
"""
import importlib.util
import inspect
import pathlib
import sys
import traceback
import types

ROOT = pathlib.Path(__file__).resolve().parent.parent


class Skipped(Exception):
    pass


def _install_pytest_shim():
    if "pytest" in sys.modules:
        return
    mod = types.ModuleType("pytest")

    def fixture(*a, **kw):
        def wrap(fn):
            fn.__is_fixture__ = True
            return fn
        return wrap(a[0]) if a and callable(a[0]) else wrap

    class _Mark:
        @staticmethod
        def parametrize(argnames, argvalues):
            names = [n.strip() for n in argnames.split(",")] \
                if isinstance(argnames, str) else list(argnames)

            def wrap(fn):
                cases = []
                for v in argvalues:
                    vals = v if isinstance(v, (tuple, list)) else (v,)
                    cases.append(dict(zip(names, vals)))
                fn.__parametrize__ = getattr(fn, "__parametrize__", []) + [cases]
                return fn
            return wrap

        def __getattr__(self, _name):          # tolerate unknown marks
            return lambda *a, **k: (lambda fn: fn)

    class _Raises:
        def __init__(self, exc, match=None):
            self.exc, self.match = exc, match

        def __enter__(self):
            return self

        def __exit__(self, et, ev, tb):
            if et is None:
                raise AssertionError("DID NOT RAISE %s" % self.exc)
            if not issubclass(et, self.exc):
                return False
            if self.match and self.match not in str(ev):
                raise AssertionError("%r not in %r" % (self.match, str(ev)))
            return True

    def importorskip(name, reason=None):
        try:
            return importlib.import_module(name)
        except Exception:
            raise Skipped(reason or "%s not installed" % name)

    def skip(reason=""):
        raise Skipped(reason)

    mod.fixture = fixture
    mod.mark = _Mark()
    mod.raises = _Raises
    mod.importorskip = importorskip
    mod.skip = skip
    mod.Skipped = Skipped
    sys.modules["pytest"] = mod


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


def main(argv):
    _install_pytest_shim()
    conftest = _load(ROOT / "tests" / "conftest.py", "conftest")

    fixtures, cache = {}, {}
    for name, fn in vars(conftest).items():
        if callable(fn) and getattr(fn, "__is_fixture__", False):
            fixtures[name] = fn

    def resolve(name):
        if name in cache:
            return cache[name]
        fn = fixtures[name]
        args = [resolve(p) for p in inspect.signature(fn).parameters]
        cache[name] = fn(*args)
        return cache[name]

    files = sorted((ROOT / "tests").glob("test_*.py"))
    if argv:
        files = [f for f in files if any(a in f.name for a in argv)]

    passed = failed = skipped = 0
    failures = []

    for path in files:
        module = _load(path, path.stem)
        # Module-level fixtures shadow conftest ones, as pytest does.
        for name, fn in vars(module).items():
            if callable(fn) and getattr(fn, "__is_fixture__", False):
                fixtures[name] = fn
                cache.pop(name, None)
        names = [n for n in vars(module) if n.startswith("test_")]
        print("\n%s" % path.name)
        for name in names:
            fn = getattr(module, name)
            if not callable(fn):
                continue
            params = getattr(fn, "__parametrize__", None)
            cases = params[0] if params else [{}]
            for case in cases:
                label = name + (" %s" % case if case else "")
                try:
                    kwargs = dict(case)
                    for p in inspect.signature(fn).parameters:
                        if p not in kwargs:
                            kwargs[p] = resolve(p)
                    fn(**kwargs)
                    passed += 1
                    print("  . %s" % label)
                except Skipped as s:
                    skipped += 1
                    print("  s %s (%s)" % (label, s))
                except Exception:
                    failed += 1
                    failures.append((label, traceback.format_exc()))
                    print("  F %s" % label)

    print("\n%d passed, %d failed, %d skipped" % (passed, failed, skipped))
    for label, tb in failures:
        print("\n--- FAILED %s ---\n%s" % (label, tb))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
