from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Iterable, Literal

Severity = Literal["ERROR", "WARNING", "INFO"]

@dataclass(frozen=True)
class Finding:
    severity: Severity
    code: str
    message: str
    location: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)

    def format(self) -> str:
        """The line the CLI prints: ``[ERROR] E602: Commit message mismatch for 'c0'. (commits.c0.message)``."""
        location = f" ({self.location})" if self.location else ""
        return f"[{self.severity}] {self.code}: {self.message}{location}"

class ValidationResult:
    def __init__(self, findings: Iterable[Finding] | None = None):
        self.findings: list[Finding] = list(findings or [])

    def add(self, severity: Severity, code: str, message: str, location: str | None = None) -> None:
        self.findings.append(Finding(severity, code, message, location))

    def error(self, code: str, message: str, location: str | None = None) -> None:
        self.add("ERROR", code, message, location)

    def warning(self, code: str, message: str, location: str | None = None) -> None:
        self.add("WARNING", code, message, location)

    def info(self, code: str, message: str, location: str | None = None) -> None:
        self.add("INFO", code, message, location)

    def extend(self, other: "ValidationResult") -> None:
        self.findings.extend(other.findings)

    def has_errors(self) -> bool:
        return any(f.severity == "ERROR" for f in self.findings)

    def error_findings(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == "ERROR"]

    def error_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "ERROR")

    def warning_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "WARNING")

    def info_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "INFO")

    def to_dict(self) -> dict:
        return {
            "errors": self.error_count(),
            "warnings": self.warning_count(),
            "infos": self.info_count(),
            "findings": [f.to_dict() for f in self.findings],
        }
