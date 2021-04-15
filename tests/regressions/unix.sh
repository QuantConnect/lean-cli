#!/usr/bin/env bash

set -e
set -x

# Usage: fail <message>
fail () {
    echo "$@" 1>&2
    exit 1
}

# Usage: assert_exit_code <expected code> <command>
assert_exit_code () {
    expected="$1"
    actual=$(eval "${@:2}")

    if [[ "$expected" != "$actual" ]]; then
        fail "'${@:2}' exited with code $actual, expected $expected"
    fi
}

# Usage: assert_output <expected content> <command>
assert_output () {
    expected="$1"
    output=$(eval "${@:2}")

    if [[ "$output" != *"$expected"* ]]; then
        fail "'${@:2}' did not print $expected"
    fi
}

# Usage: assert_file_exists <path>
assert_file_exists () {
    assert_exit_code 0 test -f "$1"
}

# Usage: assert_directory_exists <path>
assert_directory_exists () {
    assert_exit_code 0 test -d "$1"
}

regressions_dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
fixtures_dir="$regressions_dir/fixtures"

timestamp=$(date +"%Y-%m-%d_%H-%M-%S")

if [[ -z "$QC_USER_ID" || -z "$QC_API_TOKEN" ]]; then
    fail "These tests require QC_USER_ID and QC_API_TOKEN to be set"
fi

# Create an empty directory to perform tests in
mkdir regression-testing
cd regression-testing

# Set up CLI configuration
assert_exit_code 0 lean config set user-id "$QC_USER_ID"
assert_exit_code 0 lean config set api-token "$QC_API_TOKEN"
assert_exit_code 0 lean config set default-language python

# Download sample data and LEAN configuration file
assert_exit_code 0 lean init
assert_directory_exists "data"
assert_file_exists "lean.json"

# Generate random data to use in backtests
assert_exit_code 0 lean data generate --start=20150101 --resolution=Daily --symbol-count=1

python_project_name="Python Project $timestamp"
csharp_project_name="CSharp Project $timestamp"

# Create Python project
assert_exit_code 0 lean create-project -l python "$python_project_name"
assert_file_exists "$python_project_name/main.py"
assert_file_exists "$python_project_name/research.ipynb"
assert_file_exists "$python_project_name/config.json"
assert_file_exists "$python_project_name/.vscode/launch.json"
assert_file_exists "$python_project_name/.vscode/settings.json"
assert_file_exists "$python_project_name/.idea/$python_project_name.iml"
assert_file_exists "$python_project_name/.idea/misc.iml"
assert_file_exists "$python_project_name/.idea/modules.iml"
assert_file_exists "$python_project_name/.idea/workspace.iml"

# Create C# project
assert_exit_code 0 lean create-project -l csharp "$csharp_project_name"
assert_file_exists "$csharp_project_name/Main.cs"
assert_file_exists "$csharp_project_name/research.ipynb"
assert_file_exists "$csharp_project_name/config.json"
assert_file_exists "$csharp_project_name/$csharp_project_name.csproj"
assert_file_exists "$csharp_project_name/.vscode/launch.json"
assert_file_exists "$csharp_project_name/.idea/.idea.$csharp_project_name/.idea/workspace.xml"
assert_file_exists "$csharp_project_name/.idea/.idea.$csharp_project_name.dir/.idea/workspace.xml"

# Copy over files which actually do something on the generated data
cp "$fixtures_dir/main.py" "$python_project_name/main.py"
cp "$fixtures_dir/Main.cs" "$python_project_name/Main.cs"

# Backtest Python project
assert_output "Total Trades 1" lean backtest "$python_project_name"

# Backtest C# project
assert_output "Total Trades 1" lean backtest "$csharp_project_name"

# Push projects
assert_exit_code 0 lean cloud push --project "$python_project_name"
assert_exit_code 0 lean cloud push --project "$csharp_project_name"

# Remove some files and see if we can successfully pull them from the cloud
rm "$python_project_name/main.py"
rm "$csharp_project_name/Main.cs"

# Pull projects
assert_exit_code 0 lean cloud pull --project "$python_project_name"
assert_exit_code 0 lean cloud pull --project "$csharp_project_name"

# Ensure deleted files have been pulled
assert_file_exists "$python_project_name/main.py"
assert_file_exists "$csharp_project_name/Main.cs"
