from __future__ import annotations
import ast
import importlib.metadata as md
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

@dataclass(frozen=True)
class _m0012:
    _m0153: set[str]
    raw: str
    _m0189: str

class DependencyLicensePolicyValidator(ManifestValidator):

    def validate(self) -> ValidationResult:
        result = ValidationResult()
        _m0184 = self.config or {}
        _m0090 = _m0054(_m0184.get('licenseAllowlist'))
        _m0101 = _m0054(_m0184.get('licenseDenylist'))
        if not _m0090 and (not _m0101):
            return result
        if not bool(_m0184.get('resolveFromInstalled', True)):
            return result
        _m0201 = _m0058(_m0184.get('unknownLicenseSeverity'), _m0099=DiagnosticSeverity.WARNING, _m0088=True)
        _m0169 = _m0058(_m0184.get('licensePolicySeverity'), _m0099=DiagnosticSeverity.ERROR, _m0088=False)
        _m0186: set[tuple[str, str, str, int | None]] = set()
        for _m0102 in self._m0023():
            self._m0066(_m0102, result=result, _m0186=_m0186, _m0090=_m0090, _m0101=_m0101, _m0201=_m0201, _m0169=_m0169)
        return result

    def _m0066(self, _m0102: _DeclaredDependency, *, result: ValidationResult, _m0186: set[tuple[str, str, str, int | None]], _m0090: set[str], _m0101: set[str], _m0201: DiagnosticSeverity | None, _m0169: DiagnosticSeverity) -> None:
        _m0182 = _m0062(_m0102.name)
        if _m0182 is None:
            self._m0014(_m0102, result=result, _m0186=_m0186, _m0201=_m0201)
            return
        if _m0101 and _m0050(_m0101, _m0182):
            self._m0013(_m0102, _m0182, result=result, _m0186=_m0186, code='POL-LIC-001', _m0168='denylist', severity=_m0169, message=f"Dependency '{_m0102.name}' uses a blocked license ({_m0182.raw}) ({_m0102.file_path.name}{_m0038(_m0102.line)}).", _m0117='Remove the dependency or replace it with an allowed alternative.')
            return
        if _m0090 and (not _m0050(_m0090, _m0182)):
            self._m0013(_m0102, _m0182, result=result, _m0186=_m0186, code='POL-LIC-003', _m0168='allowlist', severity=_m0169, message=f"Dependency '{_m0102.name}' license is not allowed by allowlist policy ({_m0182.raw}) ({_m0102.file_path.name}{_m0038(_m0102.line)}).", _m0117='Adjust license allowlist or choose a dependency with an allowed license.')

    def _m0014(self, _m0102: _DeclaredDependency, *, result: ValidationResult, _m0186: set[tuple[str, str, str, int | None]], _m0201: DiagnosticSeverity | None) -> None:
        if _m0201 is None:
            return
        _m0135 = _m0030('POL-LIC-002', _m0102)
        if _m0135 in _m0186:
            return
        _m0186.add(_m0135)
        result.add_diagnostic(self._create_diagnostic(code='POL-LIC-002', message=f"License for dependency '{_m0102.name}' could not be resolved from installed metadata ({_m0102.file_path.name}{_m0038(_m0102.line)}). Interpreting as proprietary (unknown license).", severity=_m0201, file_path=_m0102.file_path, line=_m0102.line, _m0117='Install dependencies in the environment or configure policy to ignore unknown licenses.', data={'dependency': _m0102.name, 'policy': 'unknown', 'assumedLicense': 'proprietary', 'assumption': 'unknown licenses are treated as proprietary'}))

    def _m0013(self, _m0102: _DeclaredDependency, _m0182: _ResolvedLicense, *, result: ValidationResult, _m0186: set[tuple[str, str, str, int | None]], code: str, _m0168: str, severity: DiagnosticSeverity, message: str, _m0117: str) -> None:
        _m0135 = _m0030(code, _m0102)
        if _m0135 in _m0186:
            return
        _m0186.add(_m0135)
        result.add_diagnostic(self._create_diagnostic(code=code, message=message, severity=severity, file_path=_m0102.file_path, line=_m0102.line, _m0117=_m0117, data={'dependency': _m0102.name, 'policy': _m0168, 'licenses': sorted(_m0182._m0153), 'source': _m0182._m0189}))

    def _m0023(self) -> Iterable[_m0011]:
        yield from self._m0025(_m0127=True)
        yield from self._m0026()
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
        for raw in _m0028(_m0200):
            _m0175 = _m0056(raw)
            if _m0175 is None:
                continue
            yield _m0011(name=_m0175.name.lower(), _m0177=raw, file_path=_m0188, line=None)

def _m0063(_m0148: Any) -> list[str]:
    try:
        values = list(_m0148.get_all('Classifier') or [])
    except Exception:
        return []
    return [_m0202 for _m0202 in values if isinstance(_m0202, str)]

def _m0028(_m0200: ast.AST) -> list[str]:
    _m0132: list[str] = []
    for _m0154 in ast.walk(_m0200):
        if not isinstance(_m0154, ast.Call):
            continue
        if _m0039(_m0154.func) != 'setup':
            continue
        for keyword in _m0154.keywords:
            if keyword.arg != 'install_requires':
                continue
            _m0203 = _m0034(keyword._m0203)
            if _m0203:
                _m0132.extend(_m0203)
    return _m0132

def _m0043(_m0138: str, _m0095: list[str]) -> set[str]:
    _m0153: set[str] = set()
    if _m0138 and _m0138.lower() not in {'unknown', 'n/a', 'none'}:
        _m0153.add(_m0053(_m0138))
    for classifier in _m0095:
        if not classifier.startswith('License ::'):
            continue
        _m0197 = classifier.split('::')[-1].strip()
        if _m0197:
            _m0153.add(_m0053(_m0197))
    return _m0153

def _m0061(_m0138: str, _m0095: list[str]) -> str:
    if _m0138:
        return _m0138.strip() or 'UNKNOWN'
    _m0137 = [c for c in _m0095 if c.startswith('License ::')]
    raw = '; '.join(_m0137).strip()
    return raw or 'UNKNOWN'

def _m0062(_m0163: str) -> _m0012 | None:
    try:
        _m0106 = md.distribution(_m0163)
    except Exception:
        return None
    _m0148 = _m0106._m0149
    _m0138 = (_m0148.get('License') or '').strip()
    _m0095 = _m0063(_m0148)
    _m0153 = _m0043(_m0138, _m0095)
    if not _m0153:
        return None
    raw = _m0061(_m0138, _m0095)
    return _m0012(_m0153=_m0153, raw=raw, _m0189='installed')

def _m0053(_m0203: str) -> str:
    return ' '.join(_m0203.strip().lower().split())

def _m0050(_m0167: set[str], _m0182: _ResolvedLicense) -> bool:
    raw = _m0182.raw.lower()
    for _m0134 in _m0167:
        if not _m0134:
            continue
        if any((_m0134 in name for name in _m0182._m0153)):
            return True
        if _m0134 in raw:
            return True
    return False

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

def _m0058(_m0203: Any, *, _m0099: DiagnosticSeverity, _m0088: bool) -> DiagnosticSeverity | None:
    if isinstance(_m0203, str):
        _m0202 = _m0203.strip().lower()
        if _m0088 and _m0202 == 'ignore':
            return None
        for sev in DiagnosticSeverity:
            if sev._m0203 == _m0202:
                return sev
    return _m0099

def _m0038(line: int | None) -> str:
    return f':{line}' if line else ''

def _m0030(code: str, _m0102: _DeclaredDependency) -> tuple[str, str, str, int | None]:
    return (code, _m0102.name, str(_m0102.file_path), _m0102.line)

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
