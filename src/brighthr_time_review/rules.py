"""Exception detection rules engine.

Each public function in this module checks a specific type of anomaly
across the normalised DataFrame and returns a list of :class:`ExceptionRecord`
objects.

The ``detect_all`` function is the main entry point: it applies every
enabled rule and returns the combined list.
"""

import logging
from typing import Any

import pandas as pd

from brighthr_time_review.config import (
    get_employee_override,
    get_rule_value,
    is_rule_enabled,
)
from brighthr_time_review.exceptions import ExceptionRecord

logger = logging.getLogger(__name__)


def _fmt_ts(ts: Any) -> str:
    """Format a timestamp (or None) to HH:MM string."""
    if pd.isna(ts) or ts is None:
        return ""
    try:
        return pd.Timestamp(ts).strftime("%H:%M")
    except Exception:
        return str(ts)


def _fmt_date(d: Any) -> str:
    """Format a date (or None) to YYYY-MM-DD string."""
    if pd.isna(d) or d is None:
        return ""
    try:
        return str(d)[:10]
    except Exception:
        return str(d)


def _fmt_hours(h: Any) -> str:
    """Format float hours to 2dp string."""
    if pd.isna(h) or h is None:
        return ""
    return f"{float(h):.2f}"


def _make_base(row: pd.Series) -> dict:
    """Extract common fields from a normalised row."""
    return {
        "employee_name": row.get("employee_name", ""),
        "employee_id": str(row.get("employee_id", "")) if row.get("employee_id") else "",
        "work_date": _fmt_date(row.get("work_date")),
        "clock_in": _fmt_ts(row.get("clock_in")),
        "clock_out": _fmt_ts(row.get("clock_out")),
        "total_shift_hours": _fmt_hours(row.get("calc_shift_hours")),
        "break_minutes": (
            str(int(row["calc_break_minutes"]))
            if row.get("calc_break_minutes") is not None and not pd.isna(row["calc_break_minutes"])
            else ""
        ),
        "source_row": int(row.get("source_row", 0)),
    }


# ---------------------------------------------------------------------------
# Individual rule functions
# ---------------------------------------------------------------------------


def check_missing_clock_out(
    df: pd.DataFrame,
    rules: dict,
    employee_rules: list,
) -> list[ExceptionRecord]:
    """Flag rows where Clock In exists but Clock Out is missing."""
    results = []
    if not is_rule_enabled(rules, "missing_clock_out_enabled"):
        return results
    severity = get_rule_value(rules, "missing_clock_out_enabled", "severity") or "High"
    for _, row in df.iterrows():
        if row.get("has_clock_in") and not row.get("has_clock_out"):
            base = _make_base(row)
            results.append(
                ExceptionRecord(
                    **base,
                    exception_type="Missing Clock Out",
                    severity=severity,
                    raw_value=str(row.get("clock_out_raw", "") or ""),
                    rule_triggered="missing_clock_out_enabled",
                    suggested_action="Confirm actual end time before payroll.",
                )
            )
    return results


def check_missing_clock_in(
    df: pd.DataFrame,
    rules: dict,
    employee_rules: list,
) -> list[ExceptionRecord]:
    """Flag rows where Clock Out exists but Clock In is missing."""
    results = []
    if not is_rule_enabled(rules, "missing_clock_in_enabled"):
        return results
    severity = get_rule_value(rules, "missing_clock_in_enabled", "severity") or "High"
    for _, row in df.iterrows():
        if row.get("has_clock_out") and not row.get("has_clock_in"):
            base = _make_base(row)
            results.append(
                ExceptionRecord(
                    **base,
                    exception_type="Missing Clock In",
                    severity=severity,
                    raw_value=str(row.get("clock_in_raw", "") or ""),
                    rule_triggered="missing_clock_in_enabled",
                    suggested_action="Confirm actual start time before payroll.",
                )
            )
    return results


def check_missing_break(
    df: pd.DataFrame,
    rules: dict,
    employee_rules: list,
) -> list[ExceptionRecord]:
    """Flag rows where a break is required but none was recorded."""
    results = []
    if not is_rule_enabled(rules, "missing_break_enabled"):
        return results
    threshold = get_rule_value(rules, "break_required_after_hours") or 6.0
    severity = get_rule_value(rules, "missing_break_enabled", "severity") or "Medium"

    for _, row in df.iterrows():
        shift_hrs = row.get("calc_shift_hours")
        if shift_hrs is None or pd.isna(shift_hrs):
            continue
        override = get_employee_override(
            employee_rules, row.get("employee_name", ""), row.get("employee_id")
        )
        eff_threshold = (
            override.get("break_required_after_hours_override", threshold)
            if override
            else threshold
        )
        if float(shift_hrs) >= float(eff_threshold) and not row.get("has_break"):
            base = _make_base(row)
            results.append(
                ExceptionRecord(
                    **base,
                    exception_type="Missing Break",
                    severity=severity,
                    raw_value=f"Shift = {_fmt_hours(shift_hrs)} hrs, threshold = {eff_threshold} hrs",
                    rule_triggered="break_required_after_hours",
                    suggested_action=(
                        "Confirm whether break was taken and update BrightHR if needed."
                    ),
                )
            )
    return results


def check_short_break(
    df: pd.DataFrame,
    rules: dict,
    employee_rules: list,
) -> list[ExceptionRecord]:
    """Flag rows where the recorded break is below the minimum threshold."""
    results = []
    if not is_rule_enabled(rules, "short_break_enabled"):
        return results
    min_break = get_rule_value(rules, "min_break_minutes") or 20.0
    severity = get_rule_value(rules, "short_break_enabled", "severity") or "Low"

    for _, row in df.iterrows():
        bm = row.get("calc_break_minutes")
        if bm is None or pd.isna(bm) or float(bm) <= 0:
            continue
        override = get_employee_override(
            employee_rules, row.get("employee_name", ""), row.get("employee_id")
        )
        eff_min = (
            override.get("min_break_minutes_override", min_break)
            if override
            else min_break
        )
        if float(bm) < float(eff_min):
            base = _make_base(row)
            results.append(
                ExceptionRecord(
                    **base,
                    exception_type="Break Too Short",
                    severity=severity,
                    raw_value=f"{int(bm)} min (minimum {int(eff_min)} min)",
                    rule_triggered="min_break_minutes",
                    suggested_action="Confirm break duration.",
                )
            )
    return results


def check_long_break(
    df: pd.DataFrame,
    rules: dict,
    employee_rules: list,
) -> list[ExceptionRecord]:
    """Flag rows where the recorded break exceeds the maximum threshold."""
    results = []
    if not is_rule_enabled(rules, "long_break_enabled"):
        return results
    max_break = get_rule_value(rules, "max_break_minutes") or 60.0
    severity = get_rule_value(rules, "long_break_enabled", "severity") or "Low"

    for _, row in df.iterrows():
        bm = row.get("calc_break_minutes")
        if bm is None or pd.isna(bm) or float(bm) <= 0:
            continue
        override = get_employee_override(
            employee_rules, row.get("employee_name", ""), row.get("employee_id")
        )
        eff_max = (
            override.get("max_break_minutes_override", max_break)
            if override
            else max_break
        )
        if float(bm) > float(eff_max):
            base = _make_base(row)
            results.append(
                ExceptionRecord(
                    **base,
                    exception_type="Break Too Long",
                    severity=severity,
                    raw_value=f"{int(bm)} min (maximum {int(eff_max)} min)",
                    rule_triggered="max_break_minutes",
                    suggested_action=(
                        "Confirm whether the employee forgot to clock back in "
                        "or if the break was correct."
                    ),
                )
            )
    return results


def check_long_shift(
    df: pd.DataFrame,
    rules: dict,
    employee_rules: list,
) -> list[ExceptionRecord]:
    """Flag rows where the calculated shift exceeds the maximum hours."""
    results = []
    if not is_rule_enabled(rules, "long_shift_enabled"):
        return results
    max_hrs = get_rule_value(rules, "max_shift_hours_default") or 12.0
    severity = get_rule_value(rules, "long_shift_enabled", "severity") or "High"

    for _, row in df.iterrows():
        shift_hrs = row.get("calc_shift_hours")
        if shift_hrs is None or pd.isna(shift_hrs):
            continue
        override = get_employee_override(
            employee_rules, row.get("employee_name", ""), row.get("employee_id")
        )
        eff_max = (
            override.get("max_shift_hours_override", max_hrs)
            if override
            else max_hrs
        )
        if float(shift_hrs) > float(eff_max):
            base = _make_base(row)
            results.append(
                ExceptionRecord(
                    **base,
                    exception_type="Shift Too Long",
                    severity=severity,
                    raw_value=f"{_fmt_hours(shift_hrs)} hrs (maximum {eff_max} hrs)",
                    rule_triggered="max_shift_hours_default",
                    suggested_action=(
                        "Review for possible forgotten clock-out, overtime, "
                        "or schedule exception."
                    ),
                )
            )
    return results


def check_short_shift(
    df: pd.DataFrame,
    rules: dict,
    employee_rules: list,
) -> list[ExceptionRecord]:
    """Flag rows where the calculated shift is below the minimum hours."""
    results = []
    if not is_rule_enabled(rules, "short_shift_enabled"):
        return results
    min_hrs = get_rule_value(rules, "min_shift_hours_default") or 1.0
    severity = get_rule_value(rules, "short_shift_enabled", "severity") or "Low"

    for _, row in df.iterrows():
        shift_hrs = row.get("calc_shift_hours")
        if shift_hrs is None or pd.isna(shift_hrs):
            continue
        # Only check rows that have both clock in and out
        if not row.get("has_clock_in") or not row.get("has_clock_out"):
            continue
        override = get_employee_override(
            employee_rules, row.get("employee_name", ""), row.get("employee_id")
        )
        eff_min = (
            override.get("min_shift_hours_override", min_hrs)
            if override
            else min_hrs
        )
        if float(shift_hrs) < float(eff_min):
            base = _make_base(row)
            results.append(
                ExceptionRecord(
                    **base,
                    exception_type="Shift Too Short",
                    severity=severity,
                    raw_value=f"{_fmt_hours(shift_hrs)} hrs (minimum {eff_min} hrs)",
                    rule_triggered="min_shift_hours_default",
                    suggested_action=(
                        "Review for accidental clock-in or incomplete shift."
                    ),
                )
            )
    return results


def check_duplicate_shift(
    df: pd.DataFrame,
    rules: dict,
    employee_rules: list,
) -> list[ExceptionRecord]:
    """Flag records where an employee has duplicate/near-duplicate entries for the same date."""
    results = []
    if not is_rule_enabled(rules, "duplicate_shift_detection_enabled"):
        return results
    severity = (
        get_rule_value(rules, "duplicate_shift_detection_enabled", "severity") or "High"
    )

    # Group by employee_name + work_date + clock_in + clock_out
    group_cols = ["employee_name", "work_date", "clock_in", "clock_out"]
    # Only rows with a valid work_date
    valid = df[df["work_date"].notna()].copy()
    valid["_ci_str"] = valid["clock_in"].apply(_fmt_ts)
    valid["_co_str"] = valid["clock_out"].apply(_fmt_ts)
    dupes = valid[
        valid.duplicated(subset=["employee_name", "work_date", "_ci_str", "_co_str"], keep=False)
    ]

    reported: set = set()
    for _, row in dupes.iterrows():
        key = (row["employee_name"], str(row["work_date"]), row["_ci_str"], row["_co_str"])
        if key in reported:
            continue
        reported.add(key)
        base = _make_base(row)
        results.append(
            ExceptionRecord(
                **base,
                exception_type="Duplicate Shift",
                severity=severity,
                raw_value=(
                    f"Duplicate for {row['employee_name']} on {_fmt_date(row['work_date'])}"
                ),
                rule_triggered="duplicate_shift_detection_enabled",
                suggested_action=(
                    "Confirm whether duplicate entry should be removed "
                    "or corrected in BrightHR."
                ),
            )
        )
    return results


def check_overlapping_shift(
    df: pd.DataFrame,
    rules: dict,
    employee_rules: list,
) -> list[ExceptionRecord]:
    """Flag records where an employee has overlapping shifts on the same date."""
    results = []
    if not is_rule_enabled(rules, "overlap_detection_enabled"):
        return results
    severity = (
        get_rule_value(rules, "overlap_detection_enabled", "severity") or "High"
    )

    valid = df[
        df["work_date"].notna()
        & df["clock_in"].notna()
        & df["clock_out"].notna()
    ].copy()

    reported_pairs: set = set()

    for emp, emp_group in valid.groupby("employee_name"):
        for date, date_group in emp_group.groupby("work_date"):
            rows = date_group.sort_values("clock_in").reset_index(drop=True)
            for i in range(len(rows)):
                for j in range(i + 1, len(rows)):
                    r1 = rows.iloc[i]
                    r2 = rows.iloc[j]
                    # Overlap if r1.clock_out > r2.clock_in
                    if pd.Timestamp(r1["clock_out"]) > pd.Timestamp(r2["clock_in"]):
                        pair = (int(r1["source_row"]), int(r2["source_row"]))
                        if pair in reported_pairs:
                            continue
                        reported_pairs.add(pair)
                        base = _make_base(r1)
                        results.append(
                            ExceptionRecord(
                                **base,
                                exception_type="Overlapping Shift",
                                severity=severity,
                                raw_value=(
                                    f"Rows {r1['source_row']} and {r2['source_row']} overlap "
                                    f"for {emp} on {_fmt_date(date)}"
                                ),
                                rule_triggered="overlap_detection_enabled",
                                suggested_action=(
                                    "Confirm correct shift records before payroll."
                                ),
                            )
                        )
    return results


def check_weekend_entry(
    df: pd.DataFrame,
    rules: dict,
    employee_rules: list,
) -> list[ExceptionRecord]:
    """Flag entries on weekends when weekend work is not expected."""
    results = []
    if not is_rule_enabled(rules, "weekend_entry_enabled"):
        return results
    weekend_default = get_rule_value(rules, "weekend_work_allowed_default") or False
    severity = get_rule_value(rules, "weekend_entry_enabled", "severity") or "Medium"

    for _, row in df.iterrows():
        if not row.get("is_weekend"):
            continue
        override = get_employee_override(
            employee_rules, row.get("employee_name", ""), row.get("employee_id")
        )
        weekend_allowed = (
            override.get("weekend_work_allowed", weekend_default)
            if override
            else weekend_default
        )
        if not weekend_allowed:
            base = _make_base(row)
            results.append(
                ExceptionRecord(
                    **base,
                    exception_type="Weekend Entry",
                    severity=severity,
                    raw_value=row.get("day_of_week", ""),
                    rule_triggered="weekend_work_allowed_default",
                    suggested_action="Confirm whether weekend work was authorised.",
                )
            )
    return results


# ---------------------------------------------------------------------------
# Master runner
# ---------------------------------------------------------------------------

_ALL_RULES = [
    check_missing_clock_out,
    check_missing_clock_in,
    check_missing_break,
    check_short_break,
    check_long_break,
    check_long_shift,
    check_short_shift,
    check_duplicate_shift,
    check_overlapping_shift,
    check_weekend_entry,
]


def detect_all(
    df: pd.DataFrame,
    rules: dict,
    employee_rules: list | None = None,
) -> list[ExceptionRecord]:
    """Run every enabled exception rule against the normalised DataFrame.

    Args:
        df:             Normalised DataFrame from :func:`normalizer.normalize`.
        rules:          Parsed rules dict from :func:`config.load_exception_rules`.
        employee_rules: Optional list from :func:`config.load_employee_rules`.

    Returns:
        Combined list of :class:`ExceptionRecord` objects.
    """
    employee_rules = employee_rules or []
    all_exceptions: list[ExceptionRecord] = []
    for rule_fn in _ALL_RULES:
        found = rule_fn(df, rules, employee_rules)
        if found:
            logger.info("%s: %d exception(s) found.", rule_fn.__name__, len(found))
        all_exceptions.extend(found)
    logger.info("Total exceptions detected: %d", len(all_exceptions))
    return all_exceptions
