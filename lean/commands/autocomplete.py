# QUANTCONNECT.COM - Democratizing Finance, Empowering Individuals.
# Lean CLI v1.0. Copyright 2021 QuantConnect Corporation.

import os
import subprocess
from pathlib import Path
from platform import system
from click import group, argument, Choice, echo, option, command
from lean.components.util.click_aliased_command_group import AliasedCommandGroup


def get_all_commands(grp, path=''):
    import click
    res = []
    if isinstance(grp, click.Group):
        for name, sub in grp.commands.items():
            full_path = (path + name).strip()
            res.append(full_path)  # always add the command/group itself
            if isinstance(sub, click.Group):
                res.extend(get_all_commands(sub, path + name + ' '))  # drill into subcommands
    return res


def detect_shell() -> str:
    """Auto-detect the current shell environment."""
    if system() == 'Windows':
        # On Windows, default to powershell
        parent = os.environ.get('PSModulePath', '')
        if parent:
            return 'powershell'
        return 'powershell'  # CMD falls back to powershell
    else:
        # Unix: check $SHELL env var
        shell_path = os.environ.get('SHELL', '/bin/bash')
        shell_name = Path(shell_path).name.lower()
        if 'zsh' in shell_name:
            return 'zsh'
        elif 'fish' in shell_name:
            return 'fish'
        return 'bash'


def get_powershell_script():
    from lean.commands.lean import lean
    commands_list = get_all_commands(lean)
    commands_csv = ','.join(commands_list)
    script = rf"""
Register-ArgumentCompleter -Native -CommandName lean -ScriptBlock {{
    param($wordToComplete, $commandAst, $cursorPosition)

    $lean_commands = '{commands_csv}' -split ','

    $cmdLine = $commandAst.ToString().TrimStart()
    $cmdLine = $cmdLine -replace '^(lean)\s*', ''

    if (-not $wordToComplete) {{
        $prefix = $cmdLine
    }} else {{
        if ($cmdLine.EndsWith($wordToComplete)) {{
            $prefix = $cmdLine.Substring(0, $cmdLine.Length - $wordToComplete.Length).TrimEnd()
        }} else {{
            $prefix = $cmdLine
        }}
    }}

    $possible = @()
    if (-not $prefix) {{
        $possible = $lean_commands | Where-Object {{ $_ -notmatch ' ' }}
    }} else {{
        $possible = $lean_commands | Where-Object {{ $_.StartsWith($prefix + ' ') }} | ForEach-Object {{
            $suffix = $_.Substring($prefix.Length + 1)
            $suffix.Split(' ')[0]
        }}
    }}

    $validPossible = $possible | Select-Object -Unique
    if ($wordToComplete) {{
        $validPossible = $validPossible | Where-Object {{ $_.StartsWith($wordToComplete) }}
    }}

    $validPossible | ForEach-Object {{
        [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterValue', $_)
    }}
}}

try {{
    Set-PSReadLineOption -PredictionSource HistoryAndPlugin -ErrorAction SilentlyContinue
    Set-PSReadLineOption -PredictionViewStyle InlineView -ErrorAction SilentlyContinue
}} catch {{}}

try {{
    Set-PSReadLineKeyHandler -Key Tab -Function MenuComplete -ErrorAction SilentlyContinue
}} catch {{}}
"""
    return script.strip()


def get_bash_zsh_script(shell: str) -> str:
    from lean.commands.lean import lean
    commands_list = get_all_commands(lean)
    commands_csv = ' '.join(commands_list)

    script = f"""
# lean CLI autocomplete
_lean_complete() {{
    local IFS=$'\\n'
    local LEAN_COMMANDS=({commands_csv})
    local cur="${{COMP_WORDS[*]:1:${{#COMP_WORDS[@]}}-1}}"
    cur="${{cur% }}"  # strip trailing space
    local word="${{COMP_WORDS[$COMP_CWORD]}}"
    local prefix="${{cur% $word}}"

    local possible=()
    if [ -z "$prefix" ]; then
        for cmd in "${{LEAN_COMMANDS[@]}}"; do
            if [[ "$cmd" != *" "* ]]; then
                possible+=("$cmd")
            fi
        done
    else
        for cmd in "${{LEAN_COMMANDS[@]}}"; do
            if [[ "$cmd" == "$prefix "* ]]; then
                local suffix="${{cmd#$prefix }}"
                local next_word="${{suffix%% *}}"
                possible+=("$next_word")
            fi
        done
    fi

    local filtered=()
    for p in "${{possible[@]}}"; do
        if [[ "$p" == "$word"* ]]; then
            filtered+=("$p")
        fi
    done

    COMPREPLY=("${{filtered[@]}}")
}}
complete -F _lean_complete lean
"""
    return script.strip()


def get_fish_script() -> str:
    from lean.commands.lean import lean
    commands_list = get_all_commands(lean)
    lines = []
    for cmd in commands_list:
        parts = cmd.split(' ')
        if len(parts) == 1:
            lines.append(f"complete -c lean -f -n '__fish_use_subcommand' -a '{cmd}'")
        elif len(parts) == 2:
            lines.append(f"complete -c lean -f -n '__fish_seen_subcommand_from {parts[0]}' -a '{parts[1]}'")
    return '\n'.join(lines)


def get_script_for_shell(shell: str) -> str:
    if shell == 'powershell':
        return get_powershell_script()
    elif shell == 'fish':
        return get_fish_script()
    else:
        return get_bash_zsh_script(shell)


def get_profile_path(shell: str) -> Path:
    if shell == 'powershell':
        try:
            path = subprocess.check_output(
                ['powershell', '-NoProfile', '-Command', 'Write-Host $PROFILE'],
                stderr=subprocess.DEVNULL
            ).decode('utf-8').strip()
            return Path(path)
        except Exception:
            return Path(os.path.expanduser(r'~\Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1'))
    elif shell == 'zsh':
        return Path(os.path.expanduser('~/.zshrc'))
    elif shell == 'fish':
        return Path(os.path.expanduser('~/.config/fish/completions/lean.fish'))
    else:
        return Path(os.path.expanduser('~/.bashrc'))


def manage_profile(shell: str, action: str):
    marker_start = "# >>> lean autocomplete >>>\n"
    marker_end = "# <<< lean autocomplete <<<\n"

    profile_path = get_profile_path(shell)
    script_content = get_script_for_shell(shell) + "\n"

    content = ""
    if profile_path.exists():
        content = profile_path.read_text(encoding='utf-8')

    if action == "install":
        if marker_start in content:
            echo(f"Autocomplete is already installed in {profile_path}.")
            return

        profile_path.parent.mkdir(parents=True, exist_ok=True)
        block = f"\n{marker_start}{script_content}{marker_end}"
        with profile_path.open('a', encoding='utf-8') as f:
            f.write(block)
        echo(f"✓ Installed autocomplete to {profile_path}")
        echo("  Restart your terminal (or open a new window) for changes to take effect.")

    elif action == "uninstall":
        if marker_start not in content:
            echo(f"Autocomplete is not installed in {profile_path}.")
            return

        start_idx = content.find(marker_start)
        end_idx = content.find(marker_end) + len(marker_end)
        new_content = content[:start_idx].rstrip('\n') + "\n" + content[end_idx:].lstrip('\n')

        profile_path.write_text(new_content, encoding='utf-8')
        echo(f"✓ Uninstalled autocomplete from {profile_path}")


@group(name="autocomplete", cls=AliasedCommandGroup)
def autocomplete() -> None:
    """Manage shell autocomplete for Lean CLI.

    Auto-detects your shell. Supports: powershell, bash, zsh, fish.

    \b
    Enable autocomplete (auto-detects shell):
        lean enable-autocomplete

    \b
    Enable for a specific shell:
        lean enable-autocomplete --shell bash

    \b
    Disable autocomplete:
        lean disable-autocomplete
    """
    pass


SHELL_OPTION = option(
    '--shell', '-s',
    type=Choice(['powershell', 'bash', 'zsh', 'fish'], case_sensitive=False),
    default=None,
    help='Target shell. Auto-detected if not specified.'
)


@autocomplete.command(name="show", help="Print the autocomplete script for your shell")
@SHELL_OPTION
def show(shell: str) -> None:
    shell = shell or detect_shell()
    echo(get_script_for_shell(shell))


@command(name="enable-autocomplete", help="Install autocomplete into your shell profile")
@SHELL_OPTION
def enable_autocomplete(shell: str) -> None:
    shell = shell or detect_shell()
    echo(f"Detected shell: {shell}")
    manage_profile(shell, "install")


@command(name="disable-autocomplete", help="Remove autocomplete from your shell profile")
@SHELL_OPTION
def disable_autocomplete(shell: str) -> None:
    shell = shell or detect_shell()
    echo(f"Detected shell: {shell}")
    manage_profile(shell, "uninstall")
