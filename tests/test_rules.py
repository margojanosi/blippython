"""Tests for the exception detection rules engine."""

from pathlib import Path

import pandas as pd
import pytest

from brighthr_time_review.config import load_exception_rules
from brighthr_time_review.loader import load_csv
from brighthr_time_review.normalizer import normalize
from brighthr_time_review.rules import (
    check_duplicate_shift,
    check_long_break,
    check_long_shift,
    check_missing_break,
    check_missing_clock_in,
    check_missing_clock_out,
    check_overlapping_shift,
    check_short_break,
    check_short_shift,
    check_weekend_entry,
    detect_all,
)

_RULES_PATH = (
    Path(__file__).resolve().parents[1] / "config" / "exception_rules.yml"
)


@pytest.fixture()
def rules() -> dict:
    return load_exception_rules(_RULES_PATH)


@pytest.fixture()
def sample_norm_df() -> pd.DataFrame:
    sample = (
        Path(__file__).resolve().parents[1]
        / "data"
        / "input"
        / "sample_bright_hr_export.csv"
    )
    return normalize(load_csv(sample))


def _make_norm_row(**overrides) -> pd.DataFrame:
    """Build a single-row normalised DataFrame for unit testing rules."""
    import pandas as pd
    base = {
        "source_row": 1,
        "employee_name": "Test Person",
        "employee_id": "EMP999",
        "work_date": pd.Timestamp("2024-06-03").date(),
        "day_of_week": "Monday",
        "is_weekend": False,
        "clock_in": pd.Timestamp("2024-06-03 09:00"),
        "clock_out": pd.Timestamp("2024-06-03 17:00"),
        "calc_break_minutes": 30.0,
        "calc_shift_hours": 8.0,
        "calc_paid_hours": 7.5,
        "has_clock_in": True,
        "has_clock_out": True,
        "has_break": True,
        "location": "Office",
        "notes": "",
        "normalization_warnings": "",
    }
    base.update(overrides)
    return pd.DataFrame([base])


# ---------------------------------------------------------------------------
# Individual rule tests
# ---------------------------------------------------------------------------

def test_missing_clock_out_detected(rules: dict) -> None:
    df = _make_norm_row(has_clock_out=False, clock_out=None, calc_shift_hours=None)
    result = check_missing_clock_out(df, rules, [])
    assert len(result) == 1
    assert result[0].exception_type == "Missing Clock Out"


def test_missing_clock_out_not_flagged_when_present(rules: dict) -> None:
    df = _make_norm_row()
    result = check_missing_clock_out(df, rules, [])
    assert len(result) == 0


def test_missing_clock_in_detected(rules: dict) -> None:
    df = _make_norm_row(has_clock_in=False, clock_in=None, calc_shift_hours=None)
    result = check_missing_clock_in(df, rules, [])
    assert len(result) == 1
    assert result[0].exception_type == "Missing Clock In"


def test_missing_clock_in_not_flagged_when_present(rules: dict) -> None:
    df = _make_norm_row()
    result = check_missing_clock_in(df, rules, [])
    assert len(result) == 0


def test_missing_break_detected(rules: dict) -> None:
    # Shift of 8 hours, no break
    df = _make_norm_row(calc_shift_hours=8.0, has_break=False, calc_break_minutes=None)
    result = check_missing_break(df, rules, [])
    assert len(result) == 1
    assert result[0].exception_type == "Missing Break"


def test_missing_break_not_flagged_short_shift(rules: dict) -> None:
    # Shift of 4 hours (under the 6-hr threshold) with no break
    df = _make_norm_row(calc_shift_hours=4.0, has_break=False, calc_break_minutes=None)
    result = check_missing_break(df, rules, [])
    assert len(result) == 0


def test_short_break_detected(rules: dict) -> None:
    df = _make_norm_row(calc_break_minutes=10.0)
    result = check_short_break(df, rules, [])
    assert len(result) == 1
    assert result[0].exception_type == "Break Too Short"


def test_short_break_not_flagged_at_minimum(rules: dict) -> None:
    df = _make_norm_row(calc_break_minutes=20.0)
    result = check_short_break(df, rules, [])
    assert len(result) == 0


def test_long_break_detected(rules: dict) -> None:
    df = _make_norm_row(calc_break_minutes=90.0)
    result = check_long_break(df, rules, [])
    assert len(result) == 1
    assert result[0].exception_type == "Break Too Long"


def test_long_break_not_flagged_at_maximum(rules: dict) -> None:
    df = _make_norm_row(calc_break_minutes=60.0)
    result = check_long_break(df, rules, [])
    assert len(result) == 0


def test_long_shift_detected(rules: dict) -> None:
    df = _make_norm_row(calc_shift_hours=14.0)
    result = check_long_shift(df, rules, [])
    assert len(result) == 1
    assert result[0].exception_type == "Shift Too Long"


def test_long_shift_not_flagged_under_max(rules: dict) -> None:
    df = _make_norm_row(calc_shift_hours=10.0)
    result = check_long_shift(df, rules, [])
    assert len(result) == 0


def test_short_shift_detected(rules: dict) -> None:
    df = _make_norm_row(calc_shift_hours=0.3)
    result = check_short_shift(df, rules, [])
    assert len(result) == 1
    assert result[0].exception_type == "Shift Too Short"


def test_short_shift_not_flagged_above_minimum(rules: dict) -> None:
    df = _make_norm_row(calc_shift_hours=2.0)
    result = check_short_shift(df, rules, [])
    assert len(result) == 0


def test_duplicate_shift_detected(rules: dict) -> None:
    import pandas as pd
    rows = [
        {
            "source_row": 1, "employee_name": "Iris Orange", "employee_id": "EMP109",
            "work_date": pd.Timestamp("2024-06-06").date(),
            "day_of_week": "Thursday", "is_weekend": False,
            "clock_in": pd.Timestamp("2024-06-06 08:00"),
            "clock_out": pd.Timestamp("2024-06-06 12:00"),
            "calc_break_minutes": 0.0, "calc_shift_hours": 4.0,
            "calc_paid_hours": 4.0, "has_clock_in": True, "has_clock_out": True,
            "has_break": False, "location": "HO", "notes": "dupe1",
            "normalization_warnings": "",
        },
        {
            "source_row": 2, "employee_name": "Iris Orange", "employee_id": "EMP109",
            "work_date": pd.Timestamp("2024-06-06").date(),
            "day_of_week": "Thursday", "is_weekend": False,
            "clock_in": pd.Timestamp("2024-06-06 08:00"),
            "clock_out": pd.Timestamp("2024-06-06 12:00"),
            "calc_break_minutes": 0.0, "calc_shift_hours": 4.0,
            "calc_paid_hours": 4.0, "has_clock_in": True, "has_clock_out": True,
            "has_break": False, "location": "HO", "notes": "dupe2",
            "normalization_warnings": "",
        },
    ]
    df = pd.DataFrame(rows)
    result = check_duplicate_shift(df, rules, [])
    assert len(result) >= 1
    assert result[0].exception_type == "Duplicate Shift"


def test_overlapping_shift_detected(rules: dict) -> None:
    import pandas as pd
    rows = [
        {
            "source_row": 1, "employee_name": "Jack Purple", "employee_id": "EMP110",
            "work_date": pd.Timestamp("2024-06-06").date(),
            "day_of_week": "Thursday", "is_weekend": False,
            "clock_in": pd.Timestamp("2024-06-06 08:00"),
            "clock_out": pd.Timestamp("2024-06-06 13:00"),
            "calc_break_minutes": 0.0, "calc_shift_hours": 5.0,
            "calc_paid_hours": 5.0, "has_clock_in": True, "has_clock_out": True,
            "has_break": False, "location": "HO", "notes": "",
            "normalization_warnings": "",
        },
        {
            "source_row": 2, "employee_name": "Jack Purple", "employee_id": "EMP110",
            "work_date": pd.Timestamp("2024-06-06").date(),
            "day_of_week": "Thursday", "is_weekend": False,
            "clock_in": pd.Timestamp("2024-06-06 12:00"),
            "clock_out": pd.Timestamp("2024-06-06 17:00"),
            "calc_break_minutes": 0.0, "calc_shift_hours": 5.0,
            "calc_paid_hours": 5.0, "has_clock_in": True, "has_clock_out": True,
            "has_break": False, "location": "HO", "notes": "",
            "normalization_warnings": "",
        },
    ]
    df = pd.DataFrame(rows)
    result = check_overlapping_shift(df, rules, [])
    assert len(result) >= 1
    assert result[0].exception_type == "Overlapping Shift"


def test_weekend_entry_detected(rules: dict) -> None:
    df = _make_norm_row(
        work_date=pd.Timestamp("2024-06-08").date(),
        day_of_week="Saturday",
        is_weekend=True,
    )
    result = check_weekend_entry(df, rules, [])
    assert len(result) == 1
    assert result[0].exception_type == "Weekend Entry"


def test_weekend_entry_not_flagged_on_weekday(rules: dict) -> None:
    df = _make_norm_row(is_weekend=False)
    result = check_weekend_entry(df, rules, [])
    assert len(result) == 0


def test_clean_record_produces_no_exceptions(rules: dict) -> None:
    df = _make_norm_row()
    all_exc = detect_all(df, rules, [])
    # A clean 8-hr Monday shift with a 30-min break should only potentially
    # trigger missing_break (it has a break) – nothing else
    for exc in all_exc:
        assert exc.exception_type not in (
            "Missing Clock In",
            "Missing Clock Out",
            "Duplicate Shift",
            "Overlapping Shift",
            "Weekend Entry",
            "Shift Too Long",
            "Shift Too Short",
        ), f"Unexpected exception: {exc.exception_type}"


# ---------------------------------------------------------------------------
# Integration test against sample CSV
# ---------------------------------------------------------------------------

def test_detect_all_from_sample_csv(sample_norm_df: pd.DataFrame, rules: dict) -> None:
    exceptions = detect_all(sample_norm_df, rules, [])
    # Sample CSV is designed to trigger many exceptions
    assert len(exceptions) > 0


def test_sample_csv_has_missing_clock_out(sample_norm_df: pd.DataFrame, rules: dict) -> None:
    exceptions = detect_all(sample_norm_df, rules, [])
    types = [e.exception_type for e in exceptions]
    assert "Missing Clock Out" in types


def test_sample_csv_has_missing_clock_in(sample_norm_df: pd.DataFrame, rules: dict) -> None:
    exceptions = detect_all(sample_norm_df, rules, [])
    types = [e.exception_type for e in exceptions]
    assert "Missing Clock In" in types


def test_sample_csv_has_missing_break(sample_norm_df: pd.DataFrame, rules: dict) -> None:
    exceptions = detect_all(sample_norm_df, rules, [])
    types = [e.exception_type for e in exceptions]
    assert "Missing Break" in types


def test_sample_csv_has_short_break(sample_norm_df: pd.DataFrame, rules: dict) -> None:
    exceptions = detect_all(sample_norm_df, rules, [])
    types = [e.exception_type for e in exceptions]
    assert "Break Too Short" in types


def test_sample_csv_has_long_break(sample_norm_df: pd.DataFrame, rules: dict) -> None:
    exceptions = detect_all(sample_norm_df, rules, [])
    types = [e.exception_type for e in exceptions]
    assert "Break Too Long" in types


def test_sample_csv_has_long_shift(sample_norm_df: pd.DataFrame, rules: dict) -> None:
    exceptions = detect_all(sample_norm_df, rules, [])
    types = [e.exception_type for e in exceptions]
    assert "Shift Too Long" in types


def test_sample_csv_has_short_shift(sample_norm_df: pd.DataFrame, rules: dict) -> None:
    exceptions = detect_all(sample_norm_df, rules, [])
    types = [e.exception_type for e in exceptions]
    assert "Shift Too Short" in types


def test_sample_csv_has_duplicate_shift(sample_norm_df: pd.DataFrame, rules: dict) -> None:
    exceptions = detect_all(sample_norm_df, rules, [])
    types = [e.exception_type for e in exceptions]
    assert "Duplicate Shift" in types


def test_sample_csv_has_overlapping_shift(sample_norm_df: pd.DataFrame, rules: dict) -> None:
    exceptions = detect_all(sample_norm_df, rules, [])
    types = [e.exception_type for e in exceptions]
    assert "Overlapping Shift" in types


def test_sample_csv_has_weekend_entry(sample_norm_df: pd.DataFrame, rules: dict) -> None:
    exceptions = detect_all(sample_norm_df, rules, [])
    types = [e.exception_type for e in exceptions]
    assert "Weekend Entry" in types
