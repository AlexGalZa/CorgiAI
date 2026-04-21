#!/usr/bin/env python
"""
Corgi Insurance - Full Test Suite Runner

Usage:
    python run_tests.py                    # Run all tests
    python run_tests.py --quick            # Syntax check only (no DB needed)
    python run_tests.py --module quotes    # Run one module
    python run_tests.py --verbose          # Django verbosity=2
    python run_tests.py --docker           # Run inside Docker (docker compose)
    python run_tests.py --parallel         # Run with --parallel flag
    python run_tests.py --failfast         # Stop on first failure
    python run_tests.py --coverage         # Run with coverage report

Requires: PostgreSQL running (local or Docker) for full test runs.
Use --quick for CI pre-check without a database.
"""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────

ROOT_DIR = Path(__file__).resolve().parent
API_DIR = ROOT_DIR / "api"

# All test modules in dependency order (models before services)
TEST_MODULES = [
    "common.tests",
    "organizations.tests",
    "users.tests",
    "quotes.tests",
    "rating.tests.tests",
    "forms.tests",
    "policies.tests.tests",
    "claims.tests",
    "certificates.tests",
    "admin_api.tests",
]

# Files to syntax-check (tests + factories)
SYNTAX_CHECK_GLOBS = [
    "tests/factories.py",
    "tests/__init__.py",
    "**/tests*.py",
]


def banner(text: str) -> None:
    width = max(len(text) + 4, 60)
    print(f"\n{'=' * width}")
    print(f"  {text}")
    print(f"{'=' * width}\n")


def run(cmd: list[str], cwd: str = None, env: dict = None, check: bool = True) -> subprocess.CompletedProcess:
    """Run a command, streaming output live."""
    merged_env = {**os.environ, **(env or {})}
    result = subprocess.run(
        cmd,
        cwd=cwd or str(API_DIR),
        env=merged_env,
        text=True,
    )
    if check and result.returncode != 0:
        return result  # Don't raise, let caller decide
    return result


def syntax_check() -> bool:
    """Compile all test files to catch syntax errors (no DB needed)."""
    banner("Phase 1: Syntax Check")
    import glob

    errors = 0
    checked = 0
    for pattern in SYNTAX_CHECK_GLOBS:
        for filepath in glob.glob(str(API_DIR / pattern), recursive=True):
            if "__pycache__" in filepath:
                continue
            checked += 1
            try:
                import py_compile
                py_compile.compile(filepath, doraise=True)
                print(f"  [OK] {os.path.relpath(filepath, API_DIR)}")
            except py_compile.PyCompileError as e:
                print(f"  [FAIL] {os.path.relpath(filepath, API_DIR)}: {e}")
                errors += 1

    if errors:
        print(f"\n  [FAIL] {errors}/{checked} files have syntax errors")
        return False
    print(f"\n  [OK] All {checked} test files compile OK")
    return True


def import_check() -> bool:
    """Try importing key modules to catch import errors early."""
    banner("Phase 2: Import Check")
    result = run(
        [sys.executable, "-c", """
import os, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, '.')
try:
    import django
    django.setup()
    from tests.factories import (
        create_test_user, create_test_org, create_test_company,
        create_test_quote, create_test_policy, create_test_claim,
        create_test_form_definition, setup_user_with_org,
    )
    print('  [OK] All factory imports OK')
    print('  [OK] Django setup OK')
except Exception as e:
    print(f'  [FAIL] Import failed: {e}')
    sys.exit(1)
"""],
        check=False,
    )
    return result.returncode == 0


def check_db() -> bool:
    """Verify PostgreSQL is reachable."""
    banner("Phase 3: Database Check")
    result = run(
        [sys.executable, "manage.py", "check", "--database", "default"],
        check=False,
    )
    if result.returncode == 0:
        print("  [OK] Database connection OK")
        return True
    print("  [FAIL] Database not reachable - start PostgreSQL or use --docker / --quick")
    return False


def run_migrations() -> bool:
    """Run migrations against the test database."""
    banner("Phase 4: Migrations")
    result = run(
        [sys.executable, "manage.py", "migrate", "--run-syncdb", "--verbosity=0"],
        check=False,
    )
    if result.returncode == 0:
        print("  [OK] Migrations OK")
        return True
    print("  [FAIL] Migration failed")
    return False


def run_tests(
    modules: list[str] = None,
    verbosity: int = 1,
    parallel: bool = False,
    failfast: bool = False,
    coverage: bool = False,
) -> bool:
    """Run Django test suite."""
    target_modules = modules or TEST_MODULES
    module_str = ", ".join(target_modules) if len(target_modules) <= 5 else f"{len(target_modules)} modules"
    banner(f"Phase 5: Running Tests ({module_str})")

    cmd = []
    if coverage:
        cmd = [sys.executable, "-m", "coverage", "run", "--source=.", "--omit=*/migrations/*,*/tests/*,manage.py"]
    else:
        cmd = [sys.executable]

    cmd += ["manage.py", "test"]
    cmd += target_modules
    cmd += [f"--verbosity={verbosity}"]

    if parallel:
        cmd.append("--parallel")
    if failfast:
        cmd.append("--failfast")

    # Force test DB settings
    env = {
        "DJANGO_SETTINGS_MODULE": "config.settings",
    }

    t0 = time.time()
    result = run(cmd, check=False, env=env)
    elapsed = time.time() - t0

    print(f"\n  [TIME]  Tests completed in {elapsed:.1f}s")

    if coverage and result.returncode == 0:
        banner("Coverage Report")
        run([sys.executable, "-m", "coverage", "report", "--show-missing", "--skip-empty"], check=False)

    return result.returncode == 0


def run_docker_tests(modules: list[str] = None, verbosity: int = 1) -> bool:
    """Run tests inside Docker via docker compose."""
    banner("Running Tests via Docker")
    target = " ".join(modules or TEST_MODULES)
    cmd = [
        "docker", "compose", "run", "--rm",
        "-e", "DJANGO_SETTINGS_MODULE=config.settings",
        "django",
        "python", "manage.py", "test",
    ] + (modules or TEST_MODULES) + [f"--verbosity={verbosity}"]

    result = run(cmd, cwd=str(API_DIR), check=False)
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(
        description="Corgi Insurance - Full Test Suite Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_tests.py                     Run everything
  python run_tests.py --quick             Syntax only (no DB)
  python run_tests.py --module quotes     Single module
  python run_tests.py --module rating.tests.tests --verbose
  python run_tests.py --failfast          Stop on first failure
  python run_tests.py --coverage          With coverage report
  python run_tests.py --docker            Via Docker Compose
        """,
    )
    parser.add_argument("--quick", action="store_true", help="Syntax check only (no DB)")
    parser.add_argument("--module", "-m", type=str, help="Run a single test module (e.g. quotes, rating.tests.tests)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output (verbosity=2)")
    parser.add_argument("--docker", action="store_true", help="Run tests via Docker Compose")
    parser.add_argument("--parallel", action="store_true", help="Run tests in parallel")
    parser.add_argument("--failfast", "-f", action="store_true", help="Stop on first failure")
    parser.add_argument("--coverage", action="store_true", help="Run with coverage report")
    parser.add_argument("--skip-import", action="store_true", help="Skip import check phase")
    parser.add_argument("--skip-migrate", action="store_true", help="Skip migration phase")
    args = parser.parse_args()

    print("[Corgi] Test Suite Runner")
    print(f"   API directory: {API_DIR}")

    # Resolve module
    modules = None
    if args.module:
        # Allow shorthand: "quotes" → "quotes.tests"
        mod = args.module
        if not mod.endswith(".tests") and ".tests." not in mod:
            # Check if it's a known module
            candidates = [m for m in TEST_MODULES if m.startswith(mod)]
            if candidates:
                modules = candidates
            else:
                modules = [f"{mod}.tests"]
        else:
            modules = [mod]

    verbosity = 2 if args.verbose else 1

    # ── Phase 1: Syntax ──
    if not syntax_check():
        print("\n[FAIL] Fix syntax errors before running tests.")
        sys.exit(1)

    if args.quick:
        print("\n[PASS] Quick check passed - all test files compile OK.")
        sys.exit(0)

    # ── Docker path ──
    if args.docker:
        ok = run_docker_tests(modules, verbosity)
        sys.exit(0 if ok else 1)

    # ── Phase 2: Import ──
    if not args.skip_import:
        if not import_check():
            print("\n[FAIL] Import check failed. Install dependencies or use --docker.")
            sys.exit(1)

    # ── Phase 3: DB ──
    if not check_db():
        print("\n[TIP] Tip: Start PostgreSQL with:  docker compose -f api/docker-compose.yml up -d postgres")
        sys.exit(1)

    # ── Phase 4: Migrate ──
    if not args.skip_migrate:
        if not run_migrations():
            print("\n[FAIL] Migrations failed.")
            sys.exit(1)

    # ── Phase 5: Tests ──
    ok = run_tests(
        modules=modules,
        verbosity=verbosity,
        parallel=args.parallel,
        failfast=args.failfast,
        coverage=args.coverage,
    )

    if ok:
        print("\n[PASS] All tests passed!")
    else:
        print("\n[FAIL] Some tests failed.")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

