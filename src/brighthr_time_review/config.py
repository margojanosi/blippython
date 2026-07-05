"""Configuration loader for BrightHR Time Review MVP.

Loads exception_rules.yml and an optional employee_rules.yml, providing
typed access to all thresholds and feature flags used by the rules engine.
"""

import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

# Default path (relative to project root – resolved at runtime)
_DEFAULT_RULES_PATH = Path(__file__).resolve().parents[2] / "config" / "exception_rules.yml"
_DEFAULT_EMPLOYEE_RULES_PATH = (
    Path(__file__).resolve().parents[2] / "config" / "employee_rules.sample.yml"
)


def load_exception_rules(rules_path: Path | None = None) -> dict[str, Any]:
    """Load exception_rules.yml.

    Args:
        rules_path: Optional override path.  Falls back to config/exception_rules.yml.

    Returns:
        Parsed YAML content as a dictionary.
    """
    path = Path(rules_path) if rules_path else _DEFAULT_RULES_PATH
    logger.debug("Loading exception rules from %s", path)
    if not path.exists():
        raise FileNotFoundError(f"Exception rules file not found: {path}")
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    return data or {}


def load_employee_rules(employee_rules_path: Path | None = None) -> list[dict[str, Any]]:
    """Load employee-specific rule overrides.

    Returns an empty list if the file is not provided or does not exist
    (the MVP runs fine without employee-specific rules).

    Args:
        employee_rules_path: Optional path to employee_rules.yml.

    Returns:
        List of employee rule dictionaries.
    """
    path = Path(employee_rules_path) if employee_rules_path else None

    if path is None:
        logger.debug("No employee rules path specified – skipping.")
        return []

    if not path.exists():
        logger.warning("Employee rules file not found – proceeding without employee-specific rules.")
        return []

    logger.debug("Loading employee rules from configured path.")
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    employees: list[dict[str, Any]] = data.get("employees", []) if data else []
    return [e for e in employees if e.get("active", True)]


def get_rule_value(rules: dict[str, Any], key: str, subkey: str = "value") -> Any:
    """Convenience helper to extract a rule value from the rules dict.

    Args:
        rules:  Parsed exception rules dictionary.
        key:    Top-level rule key, e.g. "max_shift_hours_default".
        subkey: Sub-key to extract, defaults to "value".

    Returns:
        The rule value, or None if not found.
    """
    rule = rules.get(key)
    if isinstance(rule, dict):
        return rule.get(subkey)
    return rule


def is_rule_enabled(rules: dict[str, Any], key: str) -> bool:
    """Return True if a named rule is enabled in the config.

    Args:
        rules: Parsed exception rules dictionary.
        key:   Rule key, e.g. "missing_clock_out_enabled".
    """
    rule = rules.get(key)
    if isinstance(rule, dict):
        return bool(rule.get("enabled", True))
    return bool(rule)


def get_employee_override(
    employee_rules: list[dict[str, Any]],
    employee_name: str,
    employee_id: str | None = None,
) -> dict[str, Any] | None:
    """Return the first matching employee override rule, or None.

    Matching is by employee_id (preferred) then by employee_name.

    Args:
        employee_rules: List loaded via load_employee_rules().
        employee_name:  Employee name from the CSV row.
        employee_id:    Employee ID from the CSV row (optional).
    """
    for rule in employee_rules:
        if employee_id and str(rule.get("employee_id", "")) == str(employee_id):
            return rule
        if rule.get("employee_name", "").strip().lower() == employee_name.strip().lower():
            return rule
    return None
