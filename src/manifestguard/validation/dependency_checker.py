import re
from pathlib import Path
from typing import Any
from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import InvalidVersion, Version
from .base import DiagnosticSeverity, ManifestValidator, ValidationResult

def _m0060(_m0164: list[str], _m0192: SpecifierSet) -> bool:
    if not _m0164:
        return True
    for pin in _m0164:
        try:
            if Version(pin) in _m0192:
                return True
        except InvalidVersion:
            continue
    return False

def _m0064(_m0192: SpecifierSet) -> tuple[tuple[Version, bool] | None, tuple[Version, bool] | None]:
    _m0142: tuple[Version, bool] | None = None
    _m0121: tuple[Version, bool] | None = None
    for _m0134 in _m0192:
        try:
            _m0204 = Version(_m0134.version)
        except InvalidVersion:
            continue
        _m0157 = _m0134._m0158
        if _m0157 in {'>=', '>'}:
            _m0114 = _m0157 == '>'
            if _m0142 is None or _m0204 > _m0142[0] or (_m0204 == _m0142[0] and _m0114 and (not _m0142[1])):
                _m0142 = (_m0204, _m0114)
        elif _m0157 in {'<=', '<'}:
            _m0114 = _m0157 == '<'
            if _m0121 is None or _m0204 < _m0121[0] or (_m0204 == _m0121[0] and _m0114 and (not _m0121[1])):
                _m0121 = (_m0204, _m0114)
        elif _m0157 == '==':
            return ((_m0204, False), (_m0204, False))
        elif _m0157 == '~=':
            if _m0142 is None or _m0204 > _m0142[0]:
                _m0142 = (_m0204, False)
    return (_m0142, _m0121)

def _m0016(_m0121: tuple[Version, bool], _m0142: tuple[Version, bool]) -> bool:
    _m0125, _m0124 = _m0121
    _m0146, _m0145 = _m0142
    if _m0125 < _m0146:
        return True
    if _m0125 > _m0146:
        return False
    return _m0124 or _m0145

def _m0017(_m0193: SpecifierSet, _m0194: SpecifierSet) -> bool:
    _m0143, _m0122 = _m0064(_m0193)
    _m0144, _m0123 = _m0064(_m0194)
    if _m0122 is not None and _m0144 is not None and _m0016(_m0122, _m0144):
        return False
    if _m0123 is not None and _m0143 is not None and _m0016(_m0123, _m0143):
        return False
    return True

def _m0031(_m0205: list[str], _m0206: list[str]) -> bool:
    _m0111 = {_m0202 for _m0202 in _m0205 if _m0202.startswith('==')}
    _m0112 = {_m0202 for _m0202 in _m0206 if _m0202.startswith('==')}
    if _m0111 and _m0112:
        return not _m0111.isdisjoint(_m0112)
    return False

class DependencyConflictChecker(ManifestValidator):
    _m0009 = re.compile('([a-zA-Z0-9\\-_.]+)(?:\\[([^\\]]+)\\])?(?:\\s*([<>=!~]+)\\s*([0-9.*]+(?:[.][0-9.*]+)*))?')

    def __init__(self, project_root: Path, config: dict[str, Any] | None=None):
        super().__init__(project_root, config)

    def validate(self) -> ValidationResult:
        result = ValidationResult()
        _m0170 = self._m0047()
        _m0179 = self._m0049()
        self._m0029(_m0170, self.project_root / 'pyproject.toml', result)
        self._m0029(_m0179, self.project_root / 'requirements.txt', result)
        self._m0019(_m0170, _m0179, result)
        return result

    def _m0047(self) -> dict[str, list[str]]:
        _m0105: dict[str, list[str]] = {}
        pyproject_path = self.project_root / 'pyproject.toml'
        if not pyproject_path.exists():
            return _m0105
        try:
            import sys
            if sys.version_info >= (3, 11):
                import tomllib
            else:
                try:
                    import tomli as tomllib
                except ImportError:
                    return _m0105
            with pyproject_path.open('rb') as f:
                data = tomllib.load(f)
            project = data.get('project', {})
            _m0104 = project.get('dependencies', [])
            for _m0102 in _m0104:
                if isinstance(_m0102, str):
                    name, version = self._m0055(_m0102)
                    if name:
                        if name not in _m0105:
                            _m0105[name] = []
                        if version:
                            _m0105[name].append(version)
        except Exception:
            pass
        return _m0105

    def _m0049(self) -> dict[str, list[str]]:
        _m0105: dict[str, list[str]] = {}
        _m0176 = self.project_root / 'requirements.txt'
        if not _m0176.exists():
            return _m0105
        try:
            _m0140 = _m0176.read_text(encoding='utf-8').splitlines()
            for line in _m0140:
                _m0196 = line.strip()
                if not _m0196 or _m0196.startswith('#') or _m0196.startswith('-'):
                    continue
                name, version = self._m0055(_m0196)
                if name:
                    if name not in _m0105:
                        _m0105[name] = []
                    if version:
                        _m0105[name].append(version)
        except Exception:
            pass
        return _m0105

    def _m0055(self, _m0102: str) -> tuple[str | None, str | None]:
        try:
            from packaging.requirements import Requirement
            _m0175 = Requirement(_m0102)
            name = _m0175.name.lower()
            if _m0175.specifier:
                return (name, str(_m0175.specifier))
            return (name, None)
        except Exception:
            pass
        match = self._m0009.match(_m0102)
        if match:
            name = match.group(1).lower()
            _m0158 = match.group(3)
            version = match.group(4)
            if _m0158 and version:
                return (name, f'{_m0158}{version}')
            return (name, None)
        return (None, None)

    def _m0019(self, _m0170: dict[str, list[str]], _m0179: dict[str, list[str]], result: ValidationResult) -> None:
        _m0087 = set(_m0170.keys()) | set(_m0179.keys())
        for package in _m0087:
            _m0171 = _m0170.get(package, [])
            _m0180 = _m0179.get(package, [])
            _m0120 = _m0171 and _m0180 and (not self._m0086(_m0171, _m0180))
            if _m0120:
                result.add_diagnostic(self._create_diagnostic(code='DEP-001', message=f"Dependency conflict for '{package}': pyproject.toml specifies {_m0171}, requirements.txt specifies {_m0180}", severity=DiagnosticSeverity.ERROR, file_path=self.project_root / 'pyproject.toml', _m0117='Align versions between pyproject.toml and requirements.txt'))

    def _m0029(self, _m0105: dict[str, list[str]], file_path: Path, result: ValidationResult) -> None:
        for package, versions in _m0105.items():
            _m0113 = {_m0202 for _m0202 in versions if _m0202.startswith('==')}
            if len(_m0113) > 1:
                result.add_diagnostic(self._create_diagnostic(code='DEP-003', message=f"Package '{package}' pinned to multiple versions {sorted(_m0113)} in {file_path.name}", severity=DiagnosticSeverity.ERROR, file_path=file_path, _m0117='Keep a single exact version pin per package'))

    @staticmethod
    def _m0086(_m0205: list[str], _m0206: list[str]) -> bool:
        try:
            _m0193 = SpecifierSet(','.join(_m0205))
            _m0194 = SpecifierSet(','.join(_m0206))
        except InvalidSpecifier:
            return _m0031(_m0205, _m0206)
        _m0165 = [_m0202[2:].strip() for _m0202 in _m0205 if _m0202.startswith('==')]
        _m0166 = [_m0202[2:].strip() for _m0202 in _m0206 if _m0202.startswith('==')]
        if not _m0060(_m0165, _m0194) or not _m0060(_m0166, _m0193):
            return False
        if _m0165 or _m0166:
            return True
        return _m0017(_m0193, _m0194)
