from __future__ import annotations
import ast
import logging
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from packaging.requirements import InvalidRequirement, Requirement
from .base import DiagnosticSeverity, ManifestValidator, ValidationResult
_m0141 = logging.getLogger(__name__)

def _m0048(pyproject_path: Path) -> dict[str, Any] | None:
    try:
        import sys
        if sys.version_info >= (3, 11):
            import tomllib
        else:
            import tomli as tomllib
        with pyproject_path.open('rb') as handle:
            data = tomllib.load(handle)
    except Exception:
        return None
    return data if isinstance(data, dict) else None

def _m0042(project: dict[str, Any], *, _m0127: bool) -> Iterable[str]:
    _m0105 = project.get('dependencies')
    if isinstance(_m0105, list):
        for raw in _m0105:
            if isinstance(raw, str):
                yield raw
    if not _m0127:
        return
    _m0159 = project.get('optional-dependencies')
    if not isinstance(_m0159, dict):
        return
    for _group, items in _m0159.items():
        if not isinstance(items, list):
            continue
        for raw in items:
            if isinstance(raw, str):
                yield raw

@dataclass(frozen=True)
class _m0011:
    name: str
    _m0177: str
    file_path: Path
    line: int | None = None

class DependencyPolicyValidator(ManifestValidator):

    def validate(self) -> ValidationResult:
        result = ValidationResult()
        _m0184 = self.config or {}
        _m0090 = _m0054(_m0184.get('allowlist'))
        _m0101 = _m0054(_m0184.get('denylist'))
        if not _m0090 and (not _m0101):
            return result
        _m0127 = bool(_m0184.get('includeOptionalDependencies', True))
        _m0128 = bool(_m0184.get('includeRequirementsFiles', True))
        _m0129 = bool(_m0184.get('includeSetupPy', True))
        _m0089 = _m0058(_m0184.get('allowlistSeverity'), _m0099=DiagnosticSeverity.WARNING)
        _m0100 = _m0058(_m0184.get('denylistSeverity'), _m0099=DiagnosticSeverity.ERROR)
        _m0098 = list(self._m0023(_m0127=_m0127, _m0128=_m0128, _m0129=_m0129))
        _m0186: set[tuple[str, str, str, int | None]] = set()
        for _m0102 in _m0098:
            _m0103 = _m0102.name
            if _m0101 and _m0103 in _m0101:
                _m0135 = ('POL-DEP-002', _m0103, str(_m0102.file_path), _m0102.line)
                if _m0135 in _m0186:
                    continue
                _m0186.add(_m0135)
                result.add_diagnostic(self._create_diagnostic(code='POL-DEP-002', message=f"Dependency '{_m0103}' is blocked by denylist policy ({_m0102.file_path.name}{_m0038(_m0102.line)}).", severity=_m0100, file_path=_m0102.file_path, line=_m0102.line, _m0117='Remove the dependency or replace it with an allowed alternative.', data={'dependency': _m0103, 'policy': 'denylist'}))
                continue
            if _m0090 and _m0103 not in _m0090:
                _m0135 = ('POL-DEP-001', _m0103, str(_m0102.file_path), _m0102.line)
                if _m0135 in _m0186:
                    continue
                _m0186.add(_m0135)
                result.add_diagnostic(self._create_diagnostic(code='POL-DEP-001', message=f"Dependency '{_m0103}' is not allowed by allowlist policy ({_m0102.file_path.name}{_m0038(_m0102.line)}).", severity=_m0089, file_path=_m0102.file_path, line=_m0102.line, _m0117='Add the dependency to allowlist or remove it from manifests.', data={'dependency': _m0103, 'policy': 'allowlist'}))
        return result

    def _m0023(self, *, _m0127: bool, _m0128: bool, _m0129: bool) -> Iterable[_m0011]:
        yield from self._m0025(_m0127=_m0127)
        if _m0128:
            yield from self._m0026()
        if _m0129:
            yield from self._m0027()

    def _m0025(self, *, _m0127: bool) -> Iterable[_m0011]:
        pyproject_path = self.project_root / 'pyproject.toml'
        if not pyproject_path.exists():
            return
        data = _m0048(pyproject_path)
        if not data:
            return
        project = data.get('project')
        if not isinstance(project, dict):
            return
        for raw in _m0042(project, _m0127=_m0127):
            _m0175 = _m0056(raw)
            if _m0175 is None:
                continue
            yield _m0011(name=_m0175.name.lower(), _m0177=raw, file_path=pyproject_path, line=None)

    def _m0026(self) -> Iterable[_m0011]:
        _m0116 = ['requirements.txt', 'requirements-dev.txt', 'requirements-test.txt']
        for filename in _m0116:
            path = self.project_root / filename
            if not path.exists():
                continue
            try:
                _m0140 = path.read_text(encoding='utf-8').splitlines()
            except Exception as e:
                _m0141.debug(f'Failed to read {filename}: {e}')
                continue
            for line_no, line in enumerate(_m0140, start=1):
                _m0196 = line.strip()
                if not _m0196 or _m0196.startswith('#'):
                    continue
                if _m0196.startswith('-'):
                    continue
                _m0175 = _m0056(_m0196)
                if _m0175 is None:
                    continue
                yield _m0011(name=_m0175.name.lower(), _m0177=_m0196, file_path=path, line=line_no)

    def _m0027(self) -> Iterable[_m0011]:
        _m0188 = self.project_root / 'setup.py'
        if not _m0188.exists():
            return
        try:
            _m0097 = _m0188.read_text(encoding='utf-8')
            _m0200 = ast.parse(_m0097, filename=str(_m0188))
        except Exception:
            return
        _m0132: list[str] = []
        for _m0154 in ast.walk(_m0200):
            if not isinstance(_m0154, ast.Call):
                continue
            _m0118 = _m0039(_m0154.func)
            if _m0118 != 'setup':
                continue
            for keyword in _m0154.keywords:
                if keyword.arg != 'install_requires':
                    continue
                _m0203 = _m0034(keyword._m0203)
                if _m0203:
                    _m0132.extend(_m0203)
        for raw in _m0132:
            _m0175 = _m0056(raw)
            if _m0175 is None:
                continue
            yield _m0011(name=_m0175.name.lower(), _m0177=raw, file_path=_m0188, line=None)

def _m0056(raw: str) -> Requirement | None:
    try:
        return Requirement(raw)
    except InvalidRequirement:
        return None

def _m0054(_m0203: Any) -> set[str]:
    if not _m0203:
        return set()
    if not isinstance(_m0203, list):
        return set()
    _m0161: set[str] = set()
    for _m0134 in _m0203:
        if isinstance(_m0134, str) and _m0134.strip():
            _m0161.add(_m0134.strip().lower())
    return _m0161

def _m0058(_m0203: Any, *, _m0099: DiagnosticSeverity) -> DiagnosticSeverity:
    if isinstance(_m0203, str):
        _m0202 = _m0203.strip().lower()
        for sev in DiagnosticSeverity:
            if sev._m0203 == _m0202:
                return sev
    return _m0099

def _m0038(line: int | None) -> str:
    return f':{line}' if line else ''

def _m0039(_m0154: ast.expr) -> str | None:
    if isinstance(_m0154, ast.Name):
        return _m0154.id
    if isinstance(_m0154, ast.Attribute):
        return _m0154.attr
    return None

def _m0034(_m0154: ast.expr) -> list[str]:
    if isinstance(_m0154, (ast.List, ast.Tuple)):
        _m0161: list[str] = []
        for el in _m0154.elts:
            if isinstance(el, ast.Constant) and isinstance(el._m0203, str):
                _m0161.append(el._m0203)
        return _m0161
    return []
