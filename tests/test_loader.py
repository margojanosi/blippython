"""Tests for the CSV loader module."""

import textwrap
from pathlib import Path

import pandas as pd
import pytest

from brighthr_time_review.loader import REQUIRED_COLUMNS, load_csv


@pytest.fixture()
def sample_csv(tmp_path: Path) -> Path:
    """Write a minimal valid CSV and return its path."""
    content = textwrap.dedent(
        """\
        First Name,Last Name,Job Title,Team(s),Blip Type,Clock In Date,Clock In Time,Clock In Location,Clock Out Date,Clock Out Time,Clock Out Location,Total Duration,Total Excluding Breaks,Notes,Payroll Number,SI Number,Employee Address
        Alex,Green,Advisor,Support,Clocked,2026-06-30,9:00,HQ,2026-06-30,17:30,HQ,8:30,8:00,Clean record,E100,SI100,1 Demo Street
        Bailey,Stone,Advisor,Support,Clocked,2026-06-30,9:00,HQ,,,,,,Missing clock out,E101,SI101,2 Demo Street
        """
    )
    p = tmp_path / "test_export.csv"
    p.write_text(content)
    return p


def test_load_csv_returns_dataframe(sample_csv: Path) -> None:
    df = load_csv(sample_csv)
    assert isinstance(df, pd.DataFrame)


def test_load_csv_row_count(sample_csv: Path) -> None:
    df = load_csv(sample_csv)
    assert len(df) == 2


def test_load_csv_source_row_column(sample_csv: Path) -> None:
    df = load_csv(sample_csv)
    assert "source_row" in df.columns
    assert list(df["source_row"]) == [1, 2]


def test_load_csv_internal_column_names(sample_csv: Path) -> None:
    df = load_csv(sample_csv)
    assert "first_name" in df.columns
    assert "clock_in_time_raw" in df.columns
    assert "clock_out_time_raw" in df.columns
    assert "clock_in_date_raw" in df.columns


def test_load_csv_file_not_found(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_csv(tmp_path / "nonexistent.csv")


def test_load_csv_missing_required_column(tmp_path: Path) -> None:
    """A CSV missing a required column should raise ValueError."""
    content = "Employee Name,Work Date\nAlice,2024-06-03\n"
    p = tmp_path / "bad.csv"
    p.write_text(content)
    with pytest.raises(ValueError, match="missing required columns"):
        load_csv(p)


def test_load_csv_strips_column_whitespace(tmp_path: Path) -> None:
    """Column names with leading/trailing spaces should still be parsed."""
    content = (
        " First Name , Last Name , Clock In Date , Clock In Time , Clock Out Date , Clock Out Time \n"
        "Alex,Green,2026-06-30,9:00,2026-06-30,17:30\n"
    )
    p = tmp_path / "spaced.csv"
    p.write_text(content)
    df = load_csv(p)
    assert "first_name" in df.columns


def test_load_csv_skips_leading_note_lines(tmp_path: Path) -> None:
    """CSV files with a leading 'Note:' line should still be parsed correctly."""
    content = textwrap.dedent(
        """\
        Note: Durations of shifts that overlap two days will be displayed within the start date of the shift
        First Name,Last Name,Job Title,Team(s),Blip Type,Clock In Date,Clock In Time,Clock In Location,Clock Out Date,Clock Out Time,Clock Out Location,Total Duration,Total Excluding Breaks,Notes,Payroll Number,SI Number,Employee Address
        Alex,Green,Advisor,Support,Clocked,2026-06-30,9:00,HQ,2026-06-30,17:30,HQ,8:30,8:00,,E100,SI100,1 Demo Street
        """
    )
    p = tmp_path / "note_header.csv"
    p.write_text(content)
    df = load_csv(p)
    assert len(df) == 1
    assert "first_name" in df.columns
    assert df.iloc[0]["first_name"] == "Alex"


def test_load_sample_csv_exists() -> None:
    """The bundled sample CSV must exist and be loadable."""
    sample = (
        Path(__file__).resolve().parents[1]
        / "data"
        / "input"
        / "sample_bright_hr_export.csv"
    )
    df = load_csv(sample)
    assert len(df) > 0
