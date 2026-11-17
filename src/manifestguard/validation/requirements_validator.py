import re
from pathlib import Path
from re import Pattern
from typing import Any
from packaging.requirements import InvalidRequirement, Requirement
from .base import DiagnosticSeverity, ManifestValidator, ValidationResult

class RequirementsValidator(ManifestValidator):
    _m0009: Pattern = re.compile('^([a-zA-Z0-9\\-_.]+)(?:\\[([^\\]]+)\\])?(?:\\s*([<>=!~]+)\\s*([0-9.*]+(?:[.][0-9.*]+)*))?')
    _m0007: Pattern = re.compile('^(https?|git\\+https?|git\\+ssh)://')

    def __init__(self, project_root: Path, config: dict[str, Any] | None=None):
        super().__init__(project_root, config)
        self.requirements_files = ['requirements.txt', 'requirements-dev.txt', 'requirements-test.txt']

    def validate(self) -> ValidationResult:
        result = ValidationResult()
        for req_file in self.requirements_files:
            _m0175 = self.project_root / req_file
            if _m0175.exists():
                result.validated_files.append(_m0175)
                self._m0075(_m0175, result)
        return result

    def _m0075(self, file_path: Path, result: ValidationResult) -> None:
        try:
            _m0139 = file_path.read_text(encoding='utf-8').splitlines()
        except Exception as e:
            result.add_diagnostic(self._create_diagnostic(code='REQ-001', message=f'Error reading {file_path.name}: {e}', severity=DiagnosticSeverity.ERROR, file_path=file_path))
            return
        _m0186: dict[str, int] = {}
        for _m0138, line in enumerate(_m0139, start=1):
            _m0195 = line.strip()
            if not _m0195 or _m0195.startswith('#'):
                continue
            if _m0195.startswith('-'):
                continue
            self._m0077(_m0195, _m0138, file_path, result, _m0186)

    def _m0077(self, line: str, _m0138: int, file_path: Path, result: ValidationResult, _m0186: dict[str, int]) -> None:
        if self._m0007.match(line):
            if '@' not in line:
                result.add_diagnostic(self._create_diagnostic(code='REQ-006', message=f'URL dependency without version/commit: {line}', severity=DiagnosticSeverity.WARNING, file_path=file_path, line=_m0138, _m0117='Pin to specific commit: url@git+https://...#egg=package'))
            return
        try:
            _m0176 = Requirement(line)
        except InvalidRequirement as exc:
            result.add_diagnostic(self._create_diagnostic(code='REQ-002', message=f'Invalid requirement syntax: {line} ({exc})', severity=DiagnosticSeverity.ERROR, file_path=file_path, line=_m0138, _m0117='Use valid PEP 508 requirement, e.g. package>=1.0.0'))
            return
        _m0162 = _m0176.name.lower()
        if _m0162 in _m0186:
            result.add_diagnostic(self._create_diagnostic(code='REQ-004', message=f"Duplicate dependency '{_m0162}' (also on line {_m0186[_m0162]})", severity=DiagnosticSeverity.ERROR, file_path=file_path, line=_m0138, _m0117='Remove duplicate entry'))
        _m0186[_m0162] = _m0138
        if not _m0176.specifier:
            result.add_diagnostic(self._create_diagnostic(code='REQ-005', message=f"Unpinned dependency '{_m0162}' (no version specified)", severity=DiagnosticSeverity.WARNING, file_path=file_path, line=_m0138, _m0117=f'Pin version: {_m0162}==X.Y.Z or use >= operator'))
        else:
            for _m0191 in _m0176.specifier:
                if _m0191.operator == '==' and _m0191.version.endswith('*'):
                    result.add_diagnostic(self._create_diagnostic(code='REQ-003', message=f'Wildcard version not recommended: {line}', severity=DiagnosticSeverity.WARNING, file_path=file_path, line=_m0138, _m0117='Use specific version or >= operator'))
