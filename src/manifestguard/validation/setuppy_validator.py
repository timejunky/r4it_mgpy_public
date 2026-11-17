import ast
from pathlib import Path
from typing import Any, ClassVar
from packaging.requirements import InvalidRequirement, Requirement
from .base import DiagnosticSeverity, ManifestValidator, ValidationResult

class SetupPyValidator(ManifestValidator):
    _m0005: ClassVar[list[str]] = ['name', 'version']
    _m0003: ClassVar[list[str]] = ['description', 'author', 'license', 'classifiers']
    _m0000: ClassVar[dict[str, str]] = {'license_file': 'Use license_files (plural) instead', 'test_suite': 'Use pytest or other modern test runner'}

    def __init__(self, project_root: Path, config: dict[str, Any] | None=None):
        super().__init__(project_root, config)
        self.setup_path = self.project_root / 'setup.py'
        self.setup_args: dict[str, Any] = {}

    def validate(self) -> ValidationResult:
        result = ValidationResult(validated_files=[self.setup_path])
        if not self.setup_path.exists():
            return result
        if not self._m0057(result):
            return result
        if not self.setup_args:
            result.add_diagnostic(self._create_diagnostic(code='SET-003', message='No setup() call found in setup.py', severity=DiagnosticSeverity.ERROR, file_path=self.setup_path, _m0117='Add setup() call from setuptools'))
            return result
        self._m0083(result)
        self._m0082(result)
        self._m0020(result)
        self._m0074(result)
        self._m0076(result)
        return result

    def _m0057(self, result: ValidationResult) -> bool:
        try:
            _m0097 = self.setup_path.read_text(encoding='utf-8')
            _m0199 = ast.parse(_m0097, filename=str(self.setup_path))
        except SyntaxError as e:
            result.add_diagnostic(self._create_diagnostic(code='SET-002', message=f'Invalid Python syntax: {e}', severity=DiagnosticSeverity.ERROR, file_path=self.setup_path, line=e.lineno))
            return False
        except Exception as e:
            result.add_diagnostic(self._create_diagnostic(code='SET-002', message=f'Error reading setup.py: {e}', severity=DiagnosticSeverity.ERROR, file_path=self.setup_path))
            return False
        self.setup_args = self._m0032(_m0199)
        return True

    def _m0032(self, _m0199: ast.Module) -> dict[str, Any]:
        args: dict[str, Any] = {}
        for _m0153 in ast.walk(_m0199):
            if isinstance(_m0153, ast.Call):
                _m0118 = self._m0040(_m0153.func)
                if _m0118 == 'setup':
                    for keyword in _m0153.keywords:
                        if keyword.arg:
                            args[keyword.arg] = self._m0035(keyword.value)
        return args

    @staticmethod
    def _m0040(_m0153: ast.expr) -> str | None:
        if isinstance(_m0153, ast.Name):
            return _m0153.id
        if isinstance(_m0153, ast.Attribute):
            return _m0153.attr
        return None

    def _m0035(self, _m0153: ast.expr) -> Any:
        if isinstance(_m0153, ast.Constant):
            return _m0153.value
        if type(_m0153).__name__ == 'Str':
            return getattr(_m0153, 's', None)
        if isinstance(_m0153, (ast.List, ast.Tuple, ast.Set)):
            return [self._m0035(el) for el in _m0153.elts]
        if isinstance(_m0153, ast.Dict):
            return {self._m0035(k): self._m0035(_m0201) for k, _m0201 in zip(_m0153.keys, _m0153.values, strict=False) if k is not None}
        return None

    def _m0083(self, result: ValidationResult) -> None:
        for arg in self._m0005:
            if arg not in self.setup_args:
                result.add_diagnostic(self._create_diagnostic(code='SET-004', message=f"Required argument '{arg}' missing from setup() call", severity=DiagnosticSeverity.ERROR, file_path=self.setup_path, _m0117=f"Add {arg}='...' to setup() call"))
            elif not self.setup_args[arg]:
                result.add_diagnostic(self._create_diagnostic(code='SET-005', message=f"Argument '{arg}' is empty", severity=DiagnosticSeverity.WARNING, file_path=self.setup_path))

    def _m0082(self, result: ValidationResult) -> None:
        for arg in self._m0003:
            if arg not in self.setup_args:
                result.add_diagnostic(self._create_diagnostic(code='SET-004', message=f"Recommended argument '{arg}' missing from setup() call", severity=DiagnosticSeverity._m0002, file_path=self.setup_path))

    def _m0020(self, result: ValidationResult) -> None:
        for arg, message in self._m0000.items():
            if arg in self.setup_args:
                result.add_diagnostic(self._create_diagnostic(code='SET-006', message=f"Deprecated argument '{arg}' used. {message}", severity=DiagnosticSeverity.WARNING, file_path=self.setup_path))

    def _m0074(self, result: ValidationResult) -> None:
        if 'entry_points' not in self.setup_args:
            return
        _m0109 = self.setup_args['entry_points']
        if not isinstance(_m0109, dict):
            result.add_diagnostic(self._create_diagnostic(code='SET-007', message='entry_points must be a dictionary', severity=DiagnosticSeverity.ERROR, file_path=self.setup_path))
            return
        for group, _m0108 in _m0109.items():
            self._m0069(group, _m0108, result)

    def _m0069(self, group: str, _m0108: Any, result: ValidationResult) -> None:
        if isinstance(_m0108, dict):
            for name, _m0197 in _m0108.items():
                self._m0071(group, name, _m0197, result)
            return
        if isinstance(_m0108, list):
            for _m0134 in _m0108:
                self._m0070(group, _m0134, result)
            return
        if isinstance(_m0108, str):
            self._m0073(group, group, _m0108.strip(), result)
            return
        if _m0108 is not None:
            result.add_diagnostic(self._create_diagnostic(code='SET-007', message=f"Entry point group '{group}' must be a list or dict", severity=DiagnosticSeverity.ERROR, file_path=self.setup_path))

    def _m0071(self, group: str, name: Any, _m0197: Any, result: ValidationResult) -> None:
        if not isinstance(name, str) or not isinstance(_m0197, str):
            result.add_diagnostic(self._create_diagnostic(code='SET-007', message=f"Entry point group '{group}' must map strings to strings", severity=DiagnosticSeverity.ERROR, file_path=self.setup_path))
            return
        self._m0073(group, name.strip(), _m0197.strip(), result)

    def _m0070(self, group: str, _m0134: Any, result: ValidationResult) -> None:
        if not isinstance(_m0134, str) or '=' not in _m0134:
            result.add_diagnostic(self._create_diagnostic(code='SET-007', message=f"Invalid entry point declaration in group '{group}': {_m0134}", severity=DiagnosticSeverity.ERROR, file_path=self.setup_path, _m0117="Use format: 'command = package.module:function'"))
            return
        _m0151, _m0010, _m0198 = _m0134.partition('=')
        self._m0073(group, _m0151.strip(), _m0198.strip(), result)

    def _m0073(self, group: str, name: str, _m0197: str, result: ValidationResult) -> None:
        if not _m0197:
            result.add_diagnostic(self._create_diagnostic(code='SET-007', message=f"Entry point '{name}' in group '{group}' is empty", severity=DiagnosticSeverity.ERROR, file_path=self.setup_path))
            return
        if ':' not in _m0197:
            result.add_diagnostic(self._create_diagnostic(code='SET-007', message=f"Entry point '{name}' in group '{group}' must be in 'module:function' format", severity=DiagnosticSeverity.ERROR, file_path=self.setup_path, _m0117=f'Use format: {name} = package.module:function'))
            return
        _m0150, _m0010, _m0091 = _m0197.partition(':')
        if not _m0150 or not _m0091:
            result.add_diagnostic(self._create_diagnostic(code='SET-007', message=f"Entry point '{name}' in group '{group}' must reference module and callable", severity=DiagnosticSeverity.ERROR, file_path=self.setup_path, _m0117=f'Use format: {name} = package.module:function'))

    def _m0076(self, result: ValidationResult) -> None:
        if 'install_requires' not in self.setup_args:
            return
        _m0177 = self._m0052(self.setup_args['install_requires'], result)
        if _m0177 is None:
            return
        _m0185: set[str] = set()
        for _m0130, _m0102 in enumerate(_m0177):
            self._m0084(_m0102, _m0130, _m0185, result)

    def _m0052(self, _m0171: Any, result: ValidationResult) -> list[str] | None:
        if isinstance(_m0171, str):
            return [_m0171]
        if isinstance(_m0171, (list, tuple, set)):
            return [str(_m0134) for _m0134 in _m0171]
        result.add_diagnostic(self._create_diagnostic(code='SET-008', message='install_requires must be a list of strings', severity=DiagnosticSeverity.ERROR, file_path=self.setup_path))
        return None

    def _m0084(self, _m0102: Any, _m0130: int, _m0185: set[str], result: ValidationResult) -> None:
        if not isinstance(_m0102, str) or not _m0102.strip():
            result.add_diagnostic(self._create_diagnostic(code='SET-008', message=f'install_requires entry at index {_m0130} must be a non-empty string', severity=DiagnosticSeverity.ERROR, file_path=self.setup_path))
            return
        try:
            _m0176 = Requirement(_m0102)
        except InvalidRequirement as exc:
            result.add_diagnostic(self._create_diagnostic(code='SET-008', message=f"Invalid requirement '{_m0102}': {exc}", severity=DiagnosticSeverity.ERROR, file_path=self.setup_path, _m0117='Use valid PEP 508 requirement syntax'))
            return
        _m0154 = _m0176.name.lower()
        if _m0154 in _m0185:
            result.add_diagnostic(self._create_diagnostic(code='SET-008', message=f"Duplicate requirement '{_m0176.name}' in install_requires", severity=DiagnosticSeverity.WARNING, file_path=self.setup_path, _m0117='Remove duplicate entry'))
        else:
            _m0185.add(_m0154)
        if not _m0176.specifier:
            result.add_diagnostic(self._create_diagnostic(code='SET-008', message=f"Requirement '{_m0176.name}' has no version constraint", severity=DiagnosticSeverity._m0002, file_path=self.setup_path, _m0117=f'Add version specifier for {_m0176.name}'))
