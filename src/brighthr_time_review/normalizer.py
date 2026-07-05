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

MINUTES_PER_HOUR = 60.0


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


def _safe_float(value: str) -> float | None:
    """Convert a string to float, returning None on failure."""
    try:
        return float(str(value).strip())
    except (ValueError, TypeError):
        return None


def normalize(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize a raw BrightHR DataFrame into typed / calculated fields.

    The input DataFrame must have been produced by :func:`loader.load_csv`.

    Calculated fields added:
    * ``work_date``          – parsed work date (date only)
    * ``day_of_week``        – Monday, Tuesday, …
    * ``is_weekend``         – True if Saturday or Sunday
    * ``clock_in``           – parsed clock-in timestamp
    * ``clock_out``          – parsed clock-out timestamp
    * ``break_start``        – parsed break-start timestamp
    * ``break_end``          – parsed break-end timestamp
    * ``calc_break_minutes`` – break duration in minutes (from times or raw value)
    * ``calc_shift_hours``   – total elapsed hours (clock-in → clock-out)
    * ``calc_paid_hours``    – shift hours minus break hours
    * ``has_clock_in``       – bool
    * ``has_clock_out``      – bool
    * ``has_break``          – bool
    * ``normalization_warnings`` – pipe-separated string of any parse warnings

    Args:
        df: Raw DataFrame from loader.load_csv().

    Returns:
        New DataFrame with normalised / calculated columns.
    """
    records: list[dict[str, Any]] = []

    for _, row in df.iterrows():
        warnings: list[str] = []

        # ---- Work date ----
        work_date_raw = row.get("work_date_raw", "")
        work_date_ts = _try_parse_date(work_date_raw)
        if work_date_ts is None and work_date_raw:
            warnings.append(f"Could not parse Work Date: {work_date_raw!r}")

        work_date = work_date_ts.date() if work_date_ts else None
        day_of_week = work_date_ts.strftime("%A") if work_date_ts else ""
        is_weekend = (
            work_date_ts.dayofweek >= 5 if work_date_ts is not None else False
        )

        # ---- Clock in / out ----
        clock_in: pd.Timestamp | None = None
        clock_out: pd.Timestamp | None = None

        if work_date_ts is not None:
            ci_raw = row.get("clock_in_raw", "")
            clock_in = _try_parse_time(work_date_ts, ci_raw)
            if not clock_in and ci_raw:
                warnings.append(f"Could not parse Clock In: {ci_raw!r}")

            co_raw = row.get("clock_out_raw", "")
            clock_out = _try_parse_time(work_date_ts, co_raw)
            if not clock_out and co_raw:
                warnings.append(f"Could not parse Clock Out: {co_raw!r}")

        # ---- Break times ----
        break_start: pd.Timestamp | None = None
        break_end: pd.Timestamp | None = None

        if work_date_ts is not None:
            bs_raw = row.get("break_start_raw", "")
            break_start = _try_parse_time(work_date_ts, bs_raw)
            if not break_start and bs_raw:
                warnings.append(f"Could not parse Break Start: {bs_raw!r}")

            be_raw = row.get("break_end_raw", "")
            break_end = _try_parse_time(work_date_ts, be_raw)
            if not break_end and be_raw:
                warnings.append(f"Could not parse Break End: {be_raw!r}")

        # ---- Calculated break minutes ----
        calc_break_minutes: float | None = None
        if break_start is not None and break_end is not None:
            calc_break_minutes = (
                break_end - break_start
            ).total_seconds() / MINUTES_PER_HOUR
            if calc_break_minutes < 0:
                warnings.append("Break End is before Break Start.")
                calc_break_minutes = None
        else:
            # Fall back to the raw break-minutes column if provided
            raw_bm = row.get("break_minutes_raw", "")
            parsed_bm = _safe_float(raw_bm)
            if parsed_bm is not None:
                calc_break_minutes = parsed_bm

        # ---- Calculated shift / paid hours ----
        calc_shift_hours: float | None = None
        calc_paid_hours: float | None = None

        if clock_in is not None and clock_out is not None:
            calc_shift_hours = (
                clock_out - clock_in
            ).total_seconds() / (MINUTES_PER_HOUR * MINUTES_PER_HOUR)
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
                "employee_name": row.get("employee_name", ""),
                "employee_id": row.get("employee_id", ""),
                "work_date": work_date,
                "day_of_week": day_of_week,
                "is_weekend": is_weekend,
                "clock_in": clock_in,
                "clock_out": clock_out,
                "break_start": break_start,
                "break_end": break_end,
                "calc_break_minutes": calc_break_minutes,
                "calc_shift_hours": calc_shift_hours,
                "calc_paid_hours": calc_paid_hours,
                "has_clock_in": has_clock_in,
                "has_clock_out": has_clock_out,
                "has_break": has_break,
                "location": row.get("location", ""),
                "notes": row.get("notes", ""),
                "normalization_warnings": " | ".join(warnings) if warnings else "",
            }
        )

    result = pd.DataFrame(records)
    logger.info("Normalised %d records.", len(result))
    return result
