"""Unit tests for autocv.render.formatting."""

from __future__ import annotations

from datetime import date

import pytest

from autocv.render.formatting import format_date, format_month


class TestFormatMonth:
    """format_month: display formatting for CVML YYYY-MM values."""

    def test_formats_year_month(self) -> None:
        assert format_month("2024-01") == "Jan 2024"

    def test_formats_present_literal(self) -> None:
        assert format_month("present") == "Present"

    def test_rejects_malformed_value(self) -> None:
        with pytest.raises(ValueError, match="does not match format"):
            format_month("not-a-date")


class TestFormatDate:
    """format_date: display formatting for ISO dates."""

    def test_formats_date(self) -> None:
        assert format_date(date(2001, 11, 2)) == "02 Nov 2001"
