from __future__ import annotations

from pathlib import Path
from typing import Any, ClassVar

from .base import DiagnosticSeverity, ManifestValidator, ValidationResult
from .license_guardrail import (
    NormalizedLicenseKind,
    find_first_existing_license_file,
    load_pyproject_project_license,
    scan_python_source_header_marker_sets,
    scan_python_source_headers,
    validate_license_consistency,
)


class LicenseGuardrailValidator(ManifestValidator):
    """License consistency guardrail.

    Purpose: prevent AI-induced license drift between:
    - `pyproject.toml` metadata
    - `LICENSE` file text
    - source header markers (SPDX / MIT / proprietary markers)

    Diagnostic Codes:
    - LIC-001: Missing/empty [project].license
    - LIC-002: Unknown/unrecognized [project].license token
    - LIC-003: Missing LICENSE file
    - LIC-004: License mismatch
    - LIC-005: Multiple license markers in headers
    """

    MAX_FILES_TO_SCAN = 300
    IGNORE_DIR_NAMES: ClassVar[set[str]] = {
        ".git",
        ".venv",
        "venv",
        "node_modules",
        "dist",
        "build",
        "out",
        "coverage",
        "__pycache__",
        ".pytest_cache",
    }

    def __init__(self, project_root: Path, config: dict[str, Any] | None = None):
        super().__init__(project_root, config)
        self.pyproject_path = self.project_root / "pyproject.toml"
        # Used as fallback path for diagnostics if no candidate file exists.
        self.license_path = self.project_root / "LICENSE"

    def validate(self) -> ValidationResult:
        result = ValidationResult(validated_files=[self.pyproject_path])

        # If there is no pyproject.toml, the dedicated pyproject validator will report that.
        if not self.pyproject_path.exists():
            return result

        try:
            pyproject_text = self.pyproject_path.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            result.add_diagnostic(
                self._create_diagnostic(
                    code="LIC-002",
                    message=f"Unable to read pyproject.toml for license guardrail: {e}",
                    severity=DiagnosticSeverity.WARNING,
                    file_path=self.pyproject_path,
                ),
            )
            return result

        pyproject_license_token = load_pyproject_project_license(pyproject_text)

        license_text: str | None = None
        license_file_path = find_first_existing_license_file(self.project_root)
        if license_file_path is not None:
            try:
                license_text = license_file_path.read_text(encoding="utf-8", errors="replace")
                result.validated_files.append(license_file_path)
            except OSError:
                license_text = None

        # Scan python headers (best-effort, bounded)
        src_root = self.project_root / "src"
        py_files: list[Path] = []
        if src_root.exists():
            for p in src_root.rglob("*.py"):
                if self._is_ignored_path(p):
                    continue
                py_files.append(p)
                if len(py_files) >= self.MAX_FILES_TO_SCAN:
                    break

        marker_sets = scan_python_source_header_marker_sets(py_files)
        header_kinds = scan_python_source_headers(py_files)

        issues = validate_license_consistency(
            pyproject_license_token=pyproject_license_token,
            license_file_text=license_text,
            header_marker_sets=marker_sets,
        )

        for issue in issues:
            self._emit_issue(
                issue.type, issue.message, issue.expected, issue.found, header_kinds, result
            )

        return result

    def _is_ignored_path(self, path: Path) -> bool:
        return any(part in self.IGNORE_DIR_NAMES for part in path.parts)

    def _emit_issue(
        self,
        issue_type: str,
        message: str,
        expected: str | None,
        found: str | None,
        header_kinds: set[NormalizedLicenseKind],
        result: ValidationResult,
    ) -> None:
        file_path = self.pyproject_path
        severity = DiagnosticSeverity.WARNING
        code = "LIC-002"
        fix: str | None = None

        if issue_type == "missingProjectLicense":
            code = "LIC-001"
            severity = DiagnosticSeverity.WARNING
            fix = (
                "Set [project].license in pyproject.toml to a machine-readable value "
                '(e.g., "LicenseRef-Proprietary" or "MIT").'
            )
            file_path = self.pyproject_path

        elif issue_type == "unknownLicenseDeclaration":
            code = "LIC-002"
            severity = DiagnosticSeverity.WARNING
            fix = (
                "Use an SPDX-like token for [project].license "
                '(e.g., "MIT", "Apache-2.0") or a clear LicenseRef-... value.'
            )
            file_path = self.pyproject_path

        elif issue_type == "missingLicenseFile":
            code = "LIC-003"
            severity = DiagnosticSeverity.WARNING
            fix = "Add a LICENSE file at project root (or ensure it is included in the package)."
            file_path = self.license_path

        elif issue_type == "licenseMismatch":
            code = "LIC-004"
            severity = DiagnosticSeverity.ERROR
            fix = "Align pyproject.toml [project].license with LICENSE text and remove conflicting header markers."
            file_path = self.pyproject_path

        elif issue_type == "multipleHeaderLicenses":
            code = "LIC-005"
            severity = DiagnosticSeverity.ERROR
            fix = "Remove conflicting SPDX/license markers in source headers (single license declaration only)."
            file_path = self.pyproject_path

        data = {
            "issue_type": issue_type,
            "expected": expected,
            "found": found,
            "header_kinds": sorted(header_kinds),
        }

        result.add_diagnostic(
            self._create_diagnostic(
                code=code,
                message=message,
                severity=severity,
                file_path=file_path,
                fix_suggestion=fix,
                data=data,
            ),
        )
