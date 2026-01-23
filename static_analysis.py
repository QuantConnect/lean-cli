import subprocess
import sys

def display_warning_summary(warnings):
    print("\nWarnings:")
    unused_count = sum(1 for e in warnings if e.startswith('F401:'))
    if unused_count > 0:
        print(f"  - Unused imports: {unused_count}")

    print("  Consider addressing warnings in future updates.")

def run_analysis():
    print("Running static analysis...")
    print("=" * 60)

    all_critical_errors = []
    all_warnings = []

    # Check for missing arguments with mypy - CRITICAL
    print("\n1. Checking for missing function arguments...")
    print("-" * 40)

    result = subprocess.run(
        ["python", "-m", "mypy", "lean/",
         "--show-error-codes",
         "--no-error-summary",
         "--ignore-missing-imports",
         "--check-untyped-defs"],
        capture_output=True,
        text=True
    )

    # Filter for critical call argument mismatches
    call_arg_errors = []

    for line in (result.stdout + result.stderr).split('\n'):
        if not line.strip():
            continue

        # Look for call-arg errors (this covers both "too many" and "missing" arguments)
        if '[call-arg]' in line:
            # Skip false positives
            if any(pattern in line for pattern in
                   ['click.', 'subprocess.', 'Module "', 'has incompatible type "Optional',
                    'validator', 'pydantic', '__call__', 'OnlyValueValidator', 'V1Validator',
                    'QCParameter', 'QCBacktest']):
                continue
            call_arg_errors.append(line.strip())

    # Display call argument mismatches
    if call_arg_errors:
        print("CRITICAL: Missing function arguments found:")
        for error in call_arg_errors:
            # Clean path for better display
            clean_error = error.replace('/home/runner/work/lean-cli/lean-cli/', '')
            print(f"  {clean_error}")

        all_critical_errors.extend(call_arg_errors)
    else:
        print("No argument mismatch errors found")

    # Check for undefined variables with flake8 - CRITICAL
    print("\n2. Checking for undefined variables...")
    print("-" * 40)

    result = subprocess.run(
        ["python", "-m", "flake8", "lean/",
         "--select=F821",
         "--ignore=ALL",
         "--count"],
        capture_output=True,
        text=True
    )

    if result.stdout.strip() and result.stdout.strip() != "0":
        detail = subprocess.run(
            ["python", "-m", "flake8", "lean/", "--select=F821", "--ignore=ALL"],
            capture_output=True,
            text=True
        )

        undefined_errors = [e.strip() for e in detail.stdout.split('\n') if e.strip()]
        print(f"CRITICAL: {len(undefined_errors)} undefined variable(s) found:")

        for error in undefined_errors:
            print(f"  {error}")

        all_critical_errors.extend([f"F821: {e}" for e in undefined_errors])
    else:
        print("No undefined variables found")

    # Check for unused imports with flake8 - WARNING
    print("\n3. Checking for unused imports...")
    print("-" * 40)

    result = subprocess.run(
        ["python", "-m", "flake8", "lean/",
         "--select=F401",
         "--ignore=ALL",
         "--count",
         "--exit-zero"],
        capture_output=True,
        text=True
    )

    if result.stdout.strip() and result.stdout.strip() != "0":
        detail = subprocess.run(
            ["python", "-m", "flake8", "lean/", "--select=F401", "--ignore=ALL", "--exit-zero"],
            capture_output=True,
            text=True
        )

        unused_imports = [e.strip() for e in detail.stdout.split('\n') if e.strip()]
        if unused_imports:
            print(f"WARNING: {len(unused_imports)} unused import(s) found:")

            for error in unused_imports:
                print(f"  {error}")

            all_warnings.extend([f"F401: {e}" for e in unused_imports])
        else:
            print("No unused imports found")
    else:
        print("No unused imports found")

    print("\n" + "=" * 60)

    # Summary
    if all_critical_errors:
        total_errors = len(all_critical_errors)
        print(f"BUILD FAILED: Found {total_errors} critical error(s)")

        print("\nSummary of critical errors:")
        print(f"  - Function call argument mismatches: {len(call_arg_errors)}")
        undefined_count = sum(1 for e in all_critical_errors if e.startswith('F821:'))
        print(f"  - Undefined variables: {undefined_count}")

        if all_warnings:
            display_warning_summary(all_warnings)

        return 1

    if all_warnings:
        print(f"BUILD PASSED with {len(all_warnings)} warning(s)")
        display_warning_summary(all_warnings)
        return 0

    print("SUCCESS: All checks passed with no warnings")
    return 0

if __name__ == "__main__":
    sys.exit(run_analysis())
