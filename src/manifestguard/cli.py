"""Public Free entry.

The releaser copies this file to ``manifestguard/cli.py`` in the public checkout.
The monorepo command module stays the full editable entry and is not copied.
This module validates local manifests. It does not download a protected wheel.
"""

from __future__ import annotations

import sys
from pathlib import Path

import click

from manifestguard import __version__
from manifestguard.free_beacon import note_free_run
from manifestguard.validation.base import DiagnosticSeverity
from manifestguard.validation.entry_points import EntryPointValidator
from manifestguard.validation.pyproject_validator import PyprojectValidator
from manifestguard.validation.requirements_validator import RequirementsValidator
from manifestguard.validation.setuppy_validator import SetupPyValidator

_ABOUT = f"""\
ManifestGuard {__version__} (Free)

This install validates local manifests (pyproject.toml, setup.py, requirements).
It does not download a Pro wheel and it does not run Pro commands.
Trial and Pro ship through Streamingzebra after activation:
https://www.ready-4-it.com/mgpy
"""


def run_manifest_check(workspace: Path) -> int:
    """Validate manifest files in ``workspace``. Return 0 when no error is present."""
    validators = (
        PyprojectValidator(workspace),
        SetupPyValidator(workspace),
        RequirementsValidator(workspace),
        EntryPointValidator(workspace),
    )
    failed = False
    for validator in validators:
        result = validator.validate()
        for diagnostic in result.diagnostics:
            location = diagnostic.file_path
            line = f":{diagnostic.line}" if diagnostic.line else ""
            click.echo(f"{diagnostic.severity}: {diagnostic.code} {location}{line} {diagnostic.message}")
            if diagnostic.severity == DiagnosticSeverity.ERROR:
                failed = True
    if not failed:
        click.echo(f"manifest check passed ({workspace})")
    return 1 if failed else 0


def _workspace(path: Path | None) -> Path:
    if path is None:
        return Path.cwd()
    if path.is_file():
        return path.parent
    return path


@click.group(invoke_without_command=True)
@click.option("--version", is_flag=True, help="Show the Free edition version and exit.")
@click.pass_context
def cli(ctx: click.Context, version: bool) -> None:
    """Free ManifestGuard."""
    if version:
        click.echo(f"manifestguard {__version__}")
        raise SystemExit(0)
    if ctx.invoked_subcommand is None:
        click.echo(_ABOUT, nl=False)


@cli.command("beacon-uninstall", hidden=True)
def beacon_uninstall_command() -> None:
    """Send a best-effort uninstall count. The main entry already posted it."""


@cli.command("about")
def about_command() -> None:
    """Show the Free edition and where Pro comes from."""
    click.echo(_ABOUT, nl=False)


@cli.command("check")
@click.argument("path", required=False, type=click.Path(exists=True, path_type=Path))
def check_command(path: Path | None) -> None:
    """Validate pyproject.toml, setup.py, requirements, and entry points."""
    raise SystemExit(run_manifest_check(_workspace(path)))


def main(argv: list[str] | None = None) -> int:
    """Run the Free command.

    The console script calls ``main()`` with no list. ``None`` means the
    process arguments. An explicit list is for tests.
    """
    args = sys.argv[1:] if argv is None else list(argv)
    if args[:1] == ["beacon-uninstall"]:
        note_free_run(__version__, event="uninstall")
    else:
        note_free_run(__version__)
    try:
        cli.main(args=args, prog_name="manifestguard", standalone_mode=False)
    except click.ClickException as exc:
        exc.show()
        return int(exc.exit_code or 2)
    except SystemExit as exc:
        code = exc.code
        if code in (None, 0):
            return 0
        return code if isinstance(code, int) else 1
    return 0
