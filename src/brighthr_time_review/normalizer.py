"""Data normalizer for BrightHR/Blip timesheet records.

Converts raw string columns from the loaded CSV into typed / calculated
fields used by the rules engine and the workbook builder.
"""

import logging
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

# Date / time parsing formats attempted in order.
# Add or reorder if your BrightHR export uses a different format.
_DATE_FORMATS = ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"]
_TIME_FORMATS = ["%H:%M:%S", "%H:%M", "%I:%M %p", "%I:%M%p"]

SECONDS_PER_MINUTE = 60.0  # seconds in one minute
MINUTES_PER_HOUR = 60.0    # minutes in one hour (kept for documentation clarity)
SECONDS_PER_HOUR = SECONDS_PER_MINUTE * MINUTES_PER_HOUR  # seconds in one hour


def _try_parse_date(value: str) -> pd.Timestamp | None:
    """Attempt to parse a date string using multiple formats."""
    if not value or not value.strip():
        return None
    for fmt in _DATE_FORMATS:
        try:
            return pd.Timestamp(pd.to_datetime(value.strip(), format=fmt))
        except (ValueError, TypeError):
            continue
    logger.debug("Could not parse date: %r", value)
    return None


def _try_parse_time(date: pd.Timestamp, time_str: str) -> pd.Timestamp | None:
    """Attempt to parse a time string and combine it with a date."""
    if not time_str or not time_str.strip():
        return None
    cleaned = time_str.strip()
    for fmt in _TIME_FORMATS:
        try:
            t = pd.to_datetime(cleaned, format=fmt)
            return date.replace(hour=t.hour, minute=t.minute, second=t.second)
        except (ValueError, TypeError):
            continue
    logger.debug("Could not parse time: %r", time_str)
    return None


def _parse_duration_minutes(value: str) -> float | None:
    """Parse a duration string in H:MM or HH:MM format into total minutes.

    Examples: "8:30" → 510.0, "1:00" → 60.0, "" → None.
    """
    if not value or not value.strip():
        return None
    cleaned = value.strip()
    try:
        parts = cleaned.split(":")
        if len(parts) == 2:
            hours = int(parts[0])
            minutes = int(parts[1])
            return float(hours * MINUTES_PER_HOUR + minutes)
    except (ValueError, TypeError):
        pass
    logger.debug("Could not parse duration: %r", value)
    return None


def normalize(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize a raw BrightHR DataFrame into typed / calculated fields.

    The input DataFrame must have been produced by :func:`loader.load_csv`.

    Calculated fields added:
    * ``employee_name``          – first name + last name combined
    * ``work_date``              – parsed work date (Clock In date, or Clock Out date as fallback)
    * ``day_of_week``            – Monday, Tuesday, …
    * ``is_weekend``             – True if Saturday or Sunday
    * ``clock_in``               – parsed clock-in timestamp
    * ``clock_out``              – parsed clock-out timestamp
    * ``calc_break_minutes``     – break duration derived from Total Duration − Total Excluding Breaks
    * ``calc_shift_hours``       – total elapsed hours (clock-in → clock-out)
    * ``calc_paid_hours``        – shift hours minus break hours
    * ``has_clock_in``           – bool
    * ``has_clock_out``          – bool
    * ``has_break``              – bool
    * ``normalization_warnings`` – pipe-separated string of any parse warnings

    Args:
        df: Raw DataFrame from loader.load_csv().

    Returns:
        New DataFrame with normalised / calculated columns.
    """
    records: list[dict[str, Any]] = []

    for _, row in df.iterrows():
        warnings: list[str] = []

        # ---- Employee name ----
        first_name = str(row.get("first_name", "") or "").strip()
        last_name = str(row.get("last_name", "") or "").strip()
        employee_name = f"{first_name} {last_name}".strip()

        # ---- Clock In date ----
        ci_date_raw = row.get("clock_in_date_raw", "")
        ci_date_ts = _try_parse_date(ci_date_raw)
        if ci_date_ts is None and ci_date_raw:
            warnings.append(f"Could not parse Clock In Date: {ci_date_raw!r}")

        # ---- Clock Out date ----
        co_date_raw = row.get("clock_out_date_raw", "")
        co_date_ts = _try_parse_date(co_date_raw)
        if co_date_ts is None and co_date_raw:
            warnings.append(f"Could not parse Clock Out Date: {co_date_raw!r}")

        # ---- Work date (prefer Clock In date; fall back to Clock Out date) ----
        work_date_ts = ci_date_ts or co_date_ts
        work_date = work_date_ts.date() if work_date_ts else None
        day_of_week = work_date_ts.strftime("%A") if work_date_ts else ""
        is_weekend = (
            work_date_ts.dayofweek >= 5 if work_date_ts is not None else False
        )

        # ---- Clock In ----
        clock_in: pd.Timestamp | None = None
        if ci_date_ts is not None:
            ci_time_raw = row.get("clock_in_time_raw", "")
            clock_in = _try_parse_time(ci_date_ts, ci_time_raw)
            if not clock_in and ci_time_raw:
                warnings.append(f"Could not parse Clock In Time: {ci_time_raw!r}")

        # ---- Clock Out ----
        clock_out: pd.Timestamp | None = None
        if co_date_ts is not None:
            co_time_raw = row.get("clock_out_time_raw", "")
            clock_out = _try_parse_time(co_date_ts, co_time_raw)
            if not clock_out and co_time_raw:
                warnings.append(f"Could not parse Clock Out Time: {co_time_raw!r}")

        # ---- Break minutes (Total Duration − Total Excluding Breaks) ----
        calc_break_minutes: float | None = None
        dur_raw = row.get("total_duration_raw", "")
        excl_raw = row.get("total_excl_breaks_raw", "")
        dur_minutes = _parse_duration_minutes(dur_raw)
        excl_minutes = _parse_duration_minutes(excl_raw)

        if dur_minutes is not None and excl_minutes is not None:
            calc_break_minutes = dur_minutes - excl_minutes
            if calc_break_minutes < 0:
                warnings.append("Total Excluding Breaks exceeds Total Duration.")
                calc_break_minutes = None
        elif dur_raw and dur_minutes is None:
            warnings.append(f"Could not parse Total Duration: {dur_raw!r}")
        elif excl_raw and excl_minutes is None:
            warnings.append(f"Could not parse Total Excluding Breaks: {excl_raw!r}")

        # ---- Calculated shift / paid hours ----
        calc_shift_hours: float | None = None
        calc_paid_hours: float | None = None

        if clock_in is not None and clock_out is not None:
            calc_shift_hours = (
                clock_out - clock_in
            ).total_seconds() / SECONDS_PER_HOUR
            if calc_shift_hours < 0:
                warnings.append("Clock Out is before Clock In.")
                calc_shift_hours = None

        if calc_shift_hours is not None:
            break_hrs = (calc_break_minutes or 0.0) / MINUTES_PER_HOUR
            calc_paid_hours = max(calc_shift_hours - break_hrs, 0.0)

        # ---- Boolean presence flags ----
        has_clock_in = clock_in is not None
        has_clock_out = clock_out is not None
        has_break = (
            calc_break_minutes is not None and calc_break_minutes > 0
        )

        records.append(
            {
                "source_row": row.get("source_row"),
                "employee_name": employee_name,
                "employee_id": row.get("employee_id", ""),
                "work_date": work_date,
                "day_of_week": day_of_week,
                "is_weekend": is_weekend,
                "clock_in": clock_in,
                "clock_out": clock_out,
                "calc_break_minutes": calc_break_minutes,
                "calc_shift_hours": calc_shift_hours,
                "calc_paid_hours": calc_paid_hours,
                "has_clock_in": has_clock_in,
                "has_clock_out": has_clock_out,
                "has_break": has_break,
                "location": row.get("clock_in_location", ""),
                "notes": row.get("notes", ""),
                "normalization_warnings": " | ".join(warnings) if warnings else "",
            }
        )

    result = pd.DataFrame(records)
    logger.info("Normalised %d records.", len(result))
    return result
