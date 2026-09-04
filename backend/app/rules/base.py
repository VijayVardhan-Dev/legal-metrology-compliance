from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class RuleDefinition:
    rule_id: str
    rule_family: str
    legal_reference: str
    requirement: str
    applicability_conditions: dict[str, Any]
    exemptions: list[str]
    required_declaration: str | None
    validation_type: str
    severity: str
    rule_version: str
    source_url: str
    notes: str
    title: str
    category: str
    description: str
    is_active: bool = True
    effective_from: str | None = None
    effective_to: str | None = None
