# QUANTCONNECT.COM - Democratizing Finance, Empowering Individuals.
# Lean CLI v1.0. Copyright 2021 QuantConnect Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import subprocess
import sys

MYPY_IGNORE_PATTERNS = [
    'click.', 'subprocess.', 'Module "',
    'has incompatible type "Optional',
    'validator', 'pydantic', '__call__',
    'OnlyValueValidator', 'V1Validator',
    'QCParameter', 'QCBacktest'
]

def run_mypy_check():
    result = subprocess.run(
        ["python", "-m", "mypy", "lean/",
         "--show-error-codes",
         "--no-error-summary",
         "--ignore-missing-imports",
         "--check-untyped-defs"],
        capture_output=True,
        text=True
    )

    errors = []
    for line in result.stdout.splitlines() + result.stderr.splitlines():
        if not line.strip() or '[call-arg]' not in line:
            continue

        # Skip false positives
        if any(pattern in line for pattern in MYPY_IGNORE_PATTERNS):
            continue

        errors.append(line.strip())

    return errors

def run_flake8_check(select_code):
    result = subprocess.run(
        ["python", "-m", "flake8", "lean/",
         f"--select={select_code}",
         "--ignore=ALL",
         "--exit-zero"],
        capture_output=True,
        text=True
    )

    errors = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return errors, len(errors)

def display_errors(title, errors, is_critical = True):
    level = "CRITICAL" if is_critical else "WARNING"
    if errors:
        print(f"{level}: {len(errors)} {title} found:")
        for error in errors:
            # Clean path for better display
            clean_error = error.replace('/home/runner/work/lean-cli/lean-cli/', '')
            print(f"  {clean_error}")
    else:
        print(f"No {title} found")

def display_warning_summary(unused_count):
    print("\nWarnings:")
    if unused_count > 0:
        print(f"  - Unused imports: {unused_count}")
    print("  Consider addressing warnings in future updates.")

def run_analysis() -> int:
    print("Running static analysis...")
    print("=" * 60)

    critical_error_count = 0
    warning_count = 0

    # Check for missing function arguments with mypy
    print("\n1. Checking for missing function arguments...")
    print("-" * 40)

    call_arg_errors = run_mypy_check()
    display_errors("function call argument mismatch(es)", call_arg_errors)
    critical_error_count += len(call_arg_errors)

    # Check for undefined variables with flake8
    print("\n2. Checking for undefined variables...")
    print("-" * 40)

    undefined_errors, undefined_count = run_flake8_check("F821")
    display_errors("undefined variable(s)", undefined_errors)
    critical_error_count += undefined_count

    # Check for unused imports with flake8
    print("\n3. Checking for unused imports...")
    print("-" * 40)

    unused_imports, unused_count = run_flake8_check("F401")
    display_errors("unused import(s)", unused_imports, is_critical=False)
    warning_count += unused_count

    # Summary
    print("\n" + "=" * 60)

    if critical_error_count > 0:
        print(f"BUILD FAILED: Found {critical_error_count} critical error(s)")
        print("\nSummary of critical errors:")
        print(f"  - Function call argument mismatches: {len(call_arg_errors)}")
        print(f"  - Undefined variables: {undefined_count}")

        if warning_count > 0:
            display_warning_summary(unused_count)

        return 1

    if warning_count > 0:
        print(f"BUILD PASSED with {warning_count} warning(s)")
        display_warning_summary(unused_count)
        return 0

    print("SUCCESS: All checks passed with no warnings")
    return 0

if __name__ == "__main__":
    sys.exit(run_analysis())
