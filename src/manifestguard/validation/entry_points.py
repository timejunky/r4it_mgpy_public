import ast
from pathlib import Path
from typing import Any
from .base import DiagnosticSeverity, ManifestValidator, ValidationResult

class EntryPointValidator(ManifestValidator):

    def __init__(self, project_root: Path, config: dict[str, Any] | None=None):
        super().__init__(project_root, config)
        self.entry_points: list[tuple[str, str, Path]] = []
        self.source_dirs = self._m0037()
        self.search_roots = self._m0018()

    def validate(self) -> ValidationResult:
        result = ValidationResult()
        self.entry_points.clear()
        self._m0044(result)
        for name, _m0197, _m0190 in self.entry_points:
            self._m0068(name, _m0197, _m0190, result)
        return result

    def _m0037(self) -> list[Path]:
        _m0189: list[Path] = []
        _m0194 = self.project_root / 'src'
        if _m0194.exists() and _m0194.is_dir():
            for _m0134 in _m0194.iterdir():
                if _m0134.is_dir() and (not _m0134.name.startswith('.')):
                    _m0189.append(_m0134)
        for _m0134 in self.project_root.iterdir():
            if _m0134.is_dir() and (not _m0134.name.startswith('.')) and (_m0134 / '__init__.py').exists():
                _m0189.append(_m0134)
        return _m0189

    def _m0018(self) -> list[Path]:
        _m0185: set[Path] = set()
        _m0182: list[Path] = []
        for directory in self.source_dirs:
            if directory not in _m0185:
                _m0182.append(directory)
                _m0185.add(directory)
        _m0194 = self.project_root / 'src'
        if _m0194.exists() and _m0194.is_dir() and (_m0194 not in _m0185):
            _m0182.append(_m0194)
            _m0185.add(_m0194)
        if self.project_root not in _m0185:
            _m0182.append(self.project_root)
        return _m0182

    def _m0044(self, result: ValidationResult) -> None:
        pyproject_path = self.project_root / 'pyproject.toml'
        if pyproject_path.exists():
            self._m0045(pyproject_path, result)
        _m0187 = self.project_root / 'setup.py'
        if _m0187.exists():
            self._m0046(_m0187, result)

    def _m0045(self, pyproject_path: Path, result: ValidationResult) -> None:
        try:
            import sys
            if sys.version_info >= (3, 11):
                import tomllib
            else:
                try:
                    import tomli as tomllib
                except ImportError:
                    return
            with pyproject_path.open('rb') as buffer:
                data = tomllib.load(buffer)
            project = data.get('project', {})
            if not isinstance(project, dict):
                return
            _m0184 = project.get('scripts')
            self._m0024(_m0184, pyproject_path)
            _m0119 = project.get('gui-scripts')
            self._m0024(_m0119, pyproject_path)
            _m0109 = project.get('entry-points')
            if isinstance(_m0109, dict):
                for group in _m0109.values():
                    self._m0024(group, pyproject_path)
            result.validated_files.append(pyproject_path)
        except Exception:
            return

    def _m0046(self, _m0187: Path, result: ValidationResult) -> None:
        try:
            _m0097 = _m0187.read_text(encoding='utf-8')
            _m0199 = ast.parse(_m0097, filename=str(_m0187))
        except (OSError, SyntaxError):
            return
        _m0109 = self._m0033(_m0199)
        if not _m0109:
            return
        for group in _m0109.values():
            self._m0024(group, _m0187)
        result.validated_files.append(_m0187)

    def _m0024(self, raw: Any, _m0190: Path) -> None:
        if isinstance(raw, dict):
            for name, _m0197 in raw.items():
                if isinstance(name, str) and isinstance(_m0197, str):
                    self.entry_points.append((name.strip(), _m0197.strip(), _m0190))
        elif isinstance(raw, list):
            for entry in raw:
                if isinstance(entry, str) and '=' in entry:
                    _m0151, _m0010, _m0198 = entry.partition('=')
                    self.entry_points.append((_m0151.strip(), _m0198.strip(), _m0190))

    def _m0033(self, _m0199: ast.AST) -> dict[str, Any]:
        for _m0153 in ast.walk(_m0199):
            if not isinstance(_m0153, ast.Call):
                continue
            _m0118 = self._m0040(_m0153.func)
            if _m0118 != 'setup':
                continue
            for keyword in _m0153.keywords:
                if keyword.arg == 'entry_points':
                    try:
                        _m0202 = ast.literal_eval(keyword.value)
                    except Exception:
                        return {}
                    if isinstance(_m0202, dict):
                        return _m0202
        return {}

    @staticmethod
    def _m0040(_m0153: ast.expr) -> str | None:
        if isinstance(_m0153, ast.Name):
            return _m0153.id
        if isinstance(_m0153, ast.Attribute):
            return _m0153.attr
        return None

    def _m0068(self, name: str, _m0197: str, _m0190: Path, result: ValidationResult) -> None:
        if ':' not in _m0197:
            result.add_diagnostic(self._create_diagnostic(code='EP-002', message=f"Entry point '{name}' has invalid format (missing ':'): {_m0197}", severity=DiagnosticSeverity.ERROR, file_path=_m0190, _m0117=f'Use format: {name} = "package.module:function"'))
            return
        _m0150, _m0010, _m0091 = _m0197.partition(':')
        if not self._m0051(_m0150):
            result.add_diagnostic(self._create_diagnostic(code='EP-001', message=f"Entry point '{name}' targets non-existent module: {_m0150}", severity=DiagnosticSeverity.ERROR, file_path=_m0190, _m0117=f'Create module {_m0150} or fix the entry point target', data={'entry_point': name, 'module': _m0150, 'target': _m0197, 'attribute': _m0091}))
            return
        _m0149 = self._m0036(_m0150)
        if _m0149 and (not self._m0015(_m0149, _m0091)):
            result.add_diagnostic(self._create_diagnostic(code='EP-003', message=f"Entry point '{name}' targets '{_m0091}' which may not exist in {_m0150}", severity=DiagnosticSeverity.WARNING, file_path=_m0190, _m0117=f'Ensure {_m0091} is defined as a function in {_m0150}', data={'entry_point': name, 'module': _m0150, 'attribute': _m0091, 'target': _m0197}))

    def _m0051(self, _m0150: str) -> bool:
        return self._m0036(_m0150) is not None

    def _m0036(self, _m0150: str) -> Path | None:
        parts = _m0150.split('.')
        for root in self.search_roots:
            _m0173 = parts
            if root.name == parts[0]:
                _m0173 = parts[1:]
            _m0094 = root.joinpath(*_m0173)
            _m0115 = _m0094.with_suffix('.py')
            if _m0115.exists():
                return _m0115
            _m0161 = _m0094 / '__init__.py'
            if _m0161.exists():
                return _m0161
        return None

    def _m0015(self, _m0149: Path, _m0091: str) -> bool:
        try:
            _m0097 = _m0149.read_text(encoding='utf-8')
            _m0199 = ast.parse(_m0097)
            for _m0153 in ast.walk(_m0199):
                if isinstance(_m0153, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)) and _m0153.name == _m0091:
                    return True
            return False
        except Exception:
            return True
