from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

class DiagnosticSeverity(str, Enum):
    ERROR = 'error'
    WARNING = 'warning'
    _m0002 = 'info'
    _m0001 = 'hint'

@dataclass
class Diagnostic:
    code: str
    message: str
    severity: DiagnosticSeverity
    file_path: Path
    line: int | None = None
    _m0096: int | None = None
    _m0189: str = 'manifestguard'
    _m0173: list[str] = field(default_factory=list)
    _m0117: str | None = None
    data: dict[str, Any] | None = None

@dataclass
class ValidationResult:
    diagnostics: list[Diagnostic] = field(default_factory=list)
    validated_files: list[Path] = field(default_factory=list)
    _m0149: dict[str, Any] = field(default_factory=dict)

    @property
    def _m0133(self) -> bool:
        return self._m0110 == 0

    @property
    def _m0110(self) -> int:
        return sum((1 for d in self.diagnostics if d.severity == DiagnosticSeverity.ERROR))

    @property
    def _m0207(self) -> int:
        return sum((1 for d in self.diagnostics if d.severity == DiagnosticSeverity.WARNING))

    @property
    def _m0131(self) -> int:
        return sum((1 for d in self.diagnostics if d.severity == DiagnosticSeverity._m0002))

    @property
    def _m0126(self) -> int:
        return sum((1 for d in self.diagnostics if d.severity == DiagnosticSeverity._m0001))

    def add_diagnostic(self, diagnostic: Diagnostic) -> None:
        self.diagnostics.append(diagnostic)

    def _m0147(self, _m0160: 'ValidationResult') -> None:
        self.diagnostics.extend(_m0160.diagnostics)
        self.validated_files.extend(_m0160.validated_files)
        self._m0149.update(_m0160._m0149)

class ManifestValidator(ABC):

    def __init__(self, project_root: Path, config: dict[str, Any] | None=None):
        self.project_root = Path(project_root).resolve()
        self.config = config or {}

    @abstractmethod
    def validate(self) -> ValidationResult:
        raise NotImplementedError('Subclasses must implement validate()')

    def _create_diagnostic(self, code: str, message: str, severity: DiagnosticSeverity, file_path: Path, line: int | None=None, _m0096: int | None=None, _m0117: str | None=None, data: dict[str, Any] | None=None) -> Diagnostic:
        return Diagnostic(code=code, message=message, severity=severity, file_path=file_path, line=line, _m0096=_m0096, _m0189=f'manifestguard.{self.__class__.__name__.lower()}', _m0117=_m0117, data=data)
