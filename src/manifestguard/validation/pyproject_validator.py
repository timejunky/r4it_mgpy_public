import sys
from pathlib import Path
from typing import Any, ClassVar
if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None
from packaging.requirements import InvalidRequirement, Requirement
from packaging.version import InvalidVersion, Version
from .base import DiagnosticSeverity, ManifestValidator, ValidationResult

class PyprojectValidator(ManifestValidator):
    _m0006: ClassVar[list[str]] = ['name']
    _m0004: ClassVar[list[str]] = ['version', 'description']
    _m0008: ClassVar[list[str]] = ['Development Status', 'Intended Audience', 'License', 'Programming Language', 'Topic']

    def __init__(self, project_root: Path, config: dict[str, Any] | None=None):
        super().__init__(project_root, config)
        self.pyproject_path = self.project_root / 'pyproject.toml'
        self.pyproject_data: dict[str, Any] | None = None

    def validate(self) -> ValidationResult:
        result = ValidationResult(validated_files=[self.pyproject_path])
        if not self.pyproject_path.exists():
            result.add_diagnostic(self._create_diagnostic(code='PYP-001', message='pyproject.toml not found in project root', severity=DiagnosticSeverity.ERROR, file_path=self.pyproject_path, _m0117='Create pyproject.toml with [project] section'))
            return result
        if not self._m0059(result):
            return result
        self._m0065(result)
        self._m0081(result)
        if self.pyproject_data and 'project' in self.pyproject_data:
            project = self.pyproject_data['project']
            self._m0080(project, result)
            self._m0067(project, result)
            self._m0079(project, result)
            self._m0074(project, result)
        return result

    def _m0059(self, result: ValidationResult) -> bool:
        if tomllib is None:
            result.add_diagnostic(self._create_diagnostic(code='PYP-002', message='TOML parser not available (install tomli for Python <3.11)', severity=DiagnosticSeverity.ERROR, file_path=self.pyproject_path, _m0117='pip install tomli'))
            return False
        try:
            with self.pyproject_path.open('rb') as f:
                self.pyproject_data = tomllib.load(f)
            return True
        except tomllib.TOMLDecodeError as e:
            result.add_diagnostic(self._create_diagnostic(code='PYP-002', message=f'Invalid TOML syntax: {e}', severity=DiagnosticSeverity.ERROR, file_path=self.pyproject_path, line=getattr(e, 'lineno', None)))
            return False
        except Exception as e:
            result.add_diagnostic(self._create_diagnostic(code='PYP-002', message=f'Error reading pyproject.toml: {e}', severity=DiagnosticSeverity.ERROR, file_path=self.pyproject_path))
            return False

    def _m0065(self, result: ValidationResult) -> None:
        if not self.pyproject_data or 'build-system' not in self.pyproject_data:
            result.add_diagnostic(self._create_diagnostic(code='PYP-009', message='[build-system] section missing (recommended by PEP 518)', severity=DiagnosticSeverity.WARNING, file_path=self.pyproject_path, _m0117='Add [build-system] with requires = ["setuptools>=68.0", "wheel"]'))
            return
        _m0093 = self.pyproject_data['build-system']
        if not isinstance(_m0093, dict):
            result.add_diagnostic(self._create_diagnostic(code='PYP-009', message='[build-system] must be a table', severity=DiagnosticSeverity.ERROR, file_path=self.pyproject_path, _m0117='Use TOML table syntax: [build-system]'))
            return
        _m0181 = _m0093.get('requires')
        if _m0181 is None:
            result.add_diagnostic(self._create_diagnostic(code='PYP-009', message="[build-system] missing 'requires' field", severity=DiagnosticSeverity.ERROR, file_path=self.pyproject_path, _m0117='Add requires = ["setuptools>=68.0", "wheel"]'))
        elif not isinstance(_m0181, list) or not all((isinstance(_m0134, str) for _m0134 in _m0181)):
            result.add_diagnostic(self._create_diagnostic(code='PYP-009', message='[build-system].requires must be a list of strings', severity=DiagnosticSeverity.ERROR, file_path=self.pyproject_path, _m0117='Example: requires = ["setuptools>=68.0", "wheel"]'))
        _m0092 = _m0093.get('build-backend')
        if _m0092 is None:
            result.add_diagnostic(self._create_diagnostic(code='PYP-009', message="[build-system] missing 'build-backend' field", severity=DiagnosticSeverity.WARNING, file_path=self.pyproject_path, _m0117='Add build-backend = "setuptools.build_meta"'))
        elif not isinstance(_m0092, str):
            result.add_diagnostic(self._create_diagnostic(code='PYP-009', message='[build-system].build-backend must be a string', severity=DiagnosticSeverity.ERROR, file_path=self.pyproject_path))

    def _m0081(self, result: ValidationResult) -> None:
        if not self.pyproject_data or 'project' not in self.pyproject_data:
            result.add_diagnostic(self._create_diagnostic(code='PYP-003', message='[project] section missing (required by PEP 621)', severity=DiagnosticSeverity.ERROR, file_path=self.pyproject_path, _m0117="Add [project] section with at minimum 'name' field"))

    def _m0080(self, project: dict[str, Any], result: ValidationResult) -> None:
        self._m0022(project, result)
        self._m0021(project, result)
        self._m0078(project, result)
        self._m0085(project, result)

    def _m0022(self, project: dict, result: ValidationResult) -> None:
        for field in self._m0006:
            if field not in project:
                _m0117 = f'Add {field} = "your-package-name"' if field == 'name' else None
                result.add_diagnostic(self._create_diagnostic(code='PYP-004', message=f"Required field 'project.{field}' is missing", severity=DiagnosticSeverity.ERROR, file_path=self.pyproject_path, _m0117=_m0117))

    def _m0021(self, project: dict, result: ValidationResult) -> None:
        _m0107 = {_m0134 for _m0134 in project.get('dynamic') or [] if isinstance(_m0134, str)}
        for field in self._m0004:
            if field not in project and field not in _m0107:
                result.add_diagnostic(self._create_diagnostic(code='PYP-004', message=f"Recommended field 'project.{field}' is missing", severity=DiagnosticSeverity._m0002, file_path=self.pyproject_path))

    def _m0078(self, project: dict, result: ValidationResult) -> None:
        if 'name' not in project:
            return
        name = project['name']
        if not isinstance(name, str) or not name:
            result.add_diagnostic(self._create_diagnostic(code='PYP-005', message='project.name must be a non-empty string', severity=DiagnosticSeverity.ERROR, file_path=self.pyproject_path))
        elif not self._m0041(name):
            result.add_diagnostic(self._create_diagnostic(code='PYP-005', message=f"Invalid package name '{name}' (use lowercase, hyphens, no spaces)", severity=DiagnosticSeverity.WARNING, file_path=self.pyproject_path, _m0117='Use lowercase letters, numbers, and hyphens only'))

    def _m0085(self, project: dict, result: ValidationResult) -> None:
        if 'version' not in project:
            return
        version = project['version']
        if not isinstance(version, str) or not version:
            result.add_diagnostic(self._create_diagnostic(code='PYP-006', message='project.version must be a non-empty string', severity=DiagnosticSeverity.ERROR, file_path=self.pyproject_path))
            return
        try:
            Version(version)
        except InvalidVersion as exc:
            result.add_diagnostic(self._create_diagnostic(code='PYP-006', message=f"Invalid version '{version}': {exc}", severity=DiagnosticSeverity.ERROR, file_path=self.pyproject_path, _m0117="Use PEP 440 compliant version, e.g. '1.2.3'"))

    def _m0067(self, project: dict[str, Any], result: ValidationResult) -> None:
        if 'dependencies' in project:
            _m0105 = project['dependencies']
            if not isinstance(_m0105, list):
                result.add_diagnostic(self._create_diagnostic(code='PYP-007', message='project.dependencies must be a list', severity=DiagnosticSeverity.ERROR, file_path=self.pyproject_path))
            else:
                _m0186: set[str] = set()
                for i, _m0102 in enumerate(_m0105):
                    if not isinstance(_m0102, str) or not _m0102.strip():
                        result.add_diagnostic(self._create_diagnostic(code='PYP-007', message=f'Dependency at index {i} must be a non-empty string', severity=DiagnosticSeverity.ERROR, file_path=self.pyproject_path))
                        continue
                    try:
                        _m0177 = Requirement(_m0102)
                    except InvalidRequirement as exc:
                        result.add_diagnostic(self._create_diagnostic(code='PYP-007', message=f"Invalid dependency specifier '{_m0102}': {exc}", severity=DiagnosticSeverity.ERROR, file_path=self.pyproject_path, _m0117="Use valid PEP 508 requirement, e.g. 'package>=1.0.0'"))
                        continue
                    _m0156 = _m0177.name.lower()
                    if _m0156 in _m0186:
                        result.add_diagnostic(self._create_diagnostic(code='PYP-007', message=f"Duplicate dependency '{_m0177.name}' in project.dependencies", severity=DiagnosticSeverity.WARNING, file_path=self.pyproject_path, _m0117='Remove duplicate entry'))
                    else:
                        _m0186.add(_m0156)
                    if not _m0177.specifier:
                        result.add_diagnostic(self._create_diagnostic(code='PYP-007', message=f"Dependency '{_m0177.name}' has no version constraints", severity=DiagnosticSeverity._m0002, file_path=self.pyproject_path, _m0117=f'Add version specifier: {_m0177.name}>=1.0.0'))

    def _m0079(self, project: dict[str, Any], result: ValidationResult) -> None:
        _m0159 = project.get('optional-dependencies')
        if _m0159 is None:
            return
        if not isinstance(_m0159, dict):
            result.add_diagnostic(self._create_diagnostic(code='PYP-007', message='[project.optional-dependencies] must be a table', severity=DiagnosticSeverity.ERROR, file_path=self.pyproject_path))
            return
        for group, _m0105 in _m0159.items():
            if not isinstance(_m0105, list):
                result.add_diagnostic(self._create_diagnostic(code='PYP-007', message=f"Optional dependency group '{group}' must be a list", severity=DiagnosticSeverity.ERROR, file_path=self.pyproject_path))
                continue
            for _m0102 in _m0105:
                if not isinstance(_m0102, str) or not _m0102.strip():
                    result.add_diagnostic(self._create_diagnostic(code='PYP-007', message=f"Optional dependency in group '{group}' must be a non-empty string", severity=DiagnosticSeverity.ERROR, file_path=self.pyproject_path))
                    continue
                try:
                    Requirement(_m0102)
                except InvalidRequirement as exc:
                    result.add_diagnostic(self._create_diagnostic(code='PYP-007', message=f"Invalid optional dependency '{_m0102}' in group '{group}': {exc}", severity=DiagnosticSeverity.ERROR, file_path=self.pyproject_path))

    def _m0074(self, project: dict[str, Any], result: ValidationResult) -> None:
        _m0185 = project.get('scripts')
        if _m0185 is not None:
            self._m0072('project.scripts', _m0185, result)
        _m0119 = project.get('gui-scripts')
        if _m0119 is not None:
            self._m0072('project.gui-scripts', _m0119, result)
        _m0109 = project.get('entry-points')
        if _m0109 is not None:
            if not isinstance(_m0109, dict):
                result.add_diagnostic(self._create_diagnostic(code='PYP-008', message='project.entry-points must be a table', severity=DiagnosticSeverity.ERROR, file_path=self.pyproject_path))
            else:
                for group, _m0108 in _m0109.items():
                    self._m0072(f'project.entry-points.{group}', _m0108, result)

    def _m0072(self, _m0136: str, _m0109: Any, result: ValidationResult) -> None:
        if not isinstance(_m0109, dict):
            result.add_diagnostic(self._create_diagnostic(code='PYP-008', message=f'{_m0136} must be a table of entry points', severity=DiagnosticSeverity.ERROR, file_path=self.pyproject_path))
            return
        for name, _m0198 in _m0109.items():
            if not isinstance(_m0198, str) or not _m0198.strip():
                result.add_diagnostic(self._create_diagnostic(code='PYP-008', message=f"Entry point '{name}' in {_m0136} must be a non-empty string", severity=DiagnosticSeverity.ERROR, file_path=self.pyproject_path))
                continue
            if ':' not in _m0198:
                result.add_diagnostic(self._create_diagnostic(code='PYP-008', message=f"Entry point '{name}' has invalid format (expected 'module:function')", severity=DiagnosticSeverity.ERROR, file_path=self.pyproject_path, _m0117=f"""Change to format like '{name} = "package.module:main"'"""))

    @staticmethod
    def _m0041(name: str) -> bool:
        import re
        return bool(re.match('^[a-z0-9]([a-z0-9\\-_\\.]*[a-z0-9])?$', name, re.IGNORECASE))
