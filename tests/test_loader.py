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
        Employee Name,Employee ID,Work Date,Clock In,Clock Out,Break Start,Break End,Break Minutes,Location,Notes
        Alice Green,EMP101,2024-06-03,08:00,16:30,12:00,12:30,30,Head Office,Clean record
        Bob White,EMP102,2024-06-03,09:00,,,,0,Head Office,Missing clock-out
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
    assert "employee_name" in df.columns
    assert "clock_in_raw" in df.columns
    assert "clock_out_raw" in df.columns
    assert "work_date_raw" in df.columns


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
        " Employee Name , Employee ID , Work Date , Clock In , Clock Out \n"
        "Alice,EMP1,2024-06-03,08:00,16:00\n"
    )
    p = tmp_path / "spaced.csv"
    p.write_text(content)
    df = load_csv(p)
    assert "employee_name" in df.columns


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
