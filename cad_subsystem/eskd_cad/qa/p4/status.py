# -*- coding: utf-8 -*-
"""Статусы и контейнеры отчёта P4."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class CheckStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    WARNING = "WARNING"
    NOT_CHECKED = "NOT_CHECKED"


@dataclass
class CheckResult:
    id: str
    title: str
    category: str  # inputs | geometry | drawing | eskd
    status: CheckStatus
    condition: str
    detail: str = ""
    normative_source: str = "внутреннее инженерное правило"
    normative_point: str = ""
    evidence: str = ""

    def as_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        return d


@dataclass
class QualityReport:
    part_id: str
    code: str
    checks: List[CheckResult] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)
    conditional_geometry: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def add(self, check: CheckResult) -> None:
        self.checks.append(check)
        if check.status == CheckStatus.FAIL:
            self.errors.append(f"{check.id}: {check.detail or check.title}")
        elif check.status == CheckStatus.WARNING:
            self.warnings.append(f"{check.id}: {check.detail or check.title}")

    def counts(self) -> Dict[str, int]:
        c = {s.value: 0 for s in CheckStatus}
        for ch in self.checks:
            c[ch.status.value] += 1
        return c

    @property
    def has_fail(self) -> bool:
        return any(ch.status == CheckStatus.FAIL for ch in self.checks)

    @property
    def has_not_checked(self) -> bool:
        return any(ch.status == CheckStatus.NOT_CHECKED for ch in self.checks)

    @property
    def fully_verified(self) -> bool:
        """Полностью проверен только если нет FAIL и нет NOT_CHECKED."""
        return (not self.has_fail) and (not self.has_not_checked)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "part_id": self.part_id,
            "code": self.code,
            "counts": self.counts(),
            "fully_verified": self.fully_verified,
            "has_fail": self.has_fail,
            "has_not_checked": self.has_not_checked,
            "assumptions": list(self.assumptions),
            "conditional_geometry": list(self.conditional_geometry),
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "checks": [c.as_dict() for c in self.checks],
        }

    def to_markdown(self) -> str:
        lines = [
            f"# Отчёт качества P4 — {self.code}",
            "",
            f"- part_id: `{self.part_id}`",
            f"- fully_verified: **{self.fully_verified}** "
            f"(FAIL запрещён; NOT_CHECKED ≠ PASS)",
            f"- counts: `{self.counts()}`",
            "",
            "## Проверки",
            "",
            "| ID | Категория | Статус | Условие | Источник | Деталь |",
            "|----|-----------|--------|---------|----------|--------|",
        ]
        for c in self.checks:
            src = c.normative_source
            if c.normative_point:
                src = f"{src} / {c.normative_point}"
            lines.append(
                f"| `{c.id}` | {c.category} | **{c.status.value}** | "
                f"{c.condition.replace('|', '/')} | {src} | "
                f"{(c.detail or c.evidence or '—').replace('|', '/')} |"
            )
        if self.errors:
            lines += ["", "## Ошибки (FAIL)", ""] + [f"- {e}" for e in self.errors]
        if self.warnings:
            lines += ["", "## Предупреждения", ""] + [f"- {w}" for w in self.warnings]
        if self.assumptions:
            lines += ["", "## Неподтверждённые допущения", ""] + [
                f"- {a}" for a in self.assumptions
            ]
        if self.conditional_geometry:
            lines += ["", "## Условная геометрия", ""] + [
                f"- {g}" for g in self.conditional_geometry
            ]
        if self.has_not_checked:
            lines += [
                "",
                "## NOT_CHECKED",
                "",
                "Чертёж **не** считается полностью проверенным: "
                "есть проверки, которые автоматика не смогла выполнить.",
            ]
        lines.append("")
        return "\n".join(lines)
