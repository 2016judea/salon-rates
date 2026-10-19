"""python3 -m pytest tests/  (no network: everything here is pure parsing)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))
import benchmark  # noqa: E402
import load  # noqa: E402
import ownsite  # noqa: E402


@pytest.mark.parametrize("text, nums", [
    ("$45+", [45.0]), ("45-60", [45.0, 60.0]), ("$1,200", [1200.0]), ("$45 - $60", [45.0, 60.0]),
    ("Free", []), ("", []), (None, []),
    # a comma with no digit is not a number: this used to raise ValueError
    ("Varies, call", []), (",", []), ("$ , 45", [45.0]),
])
def test_money_reads_digits_only(text, nums):
    assert load.money(text) == nums


@pytest.mark.parametrize("text, typ, out", [
    ("$45.00+", "S", ("from", 45.0, None)), ("$45.00", "X", ("fixed", 45.0, 45.0)),
    ("$45 - $60", "X", ("range", 45.0, 60.0)), ("Free", "F", ("free", 0, 0)),
    ("Varies", "V", ("consult", None, None)), ("-", "D", ("consult", None, None)),
])
def test_booksy_price(text, typ, out):
    assert load.booksy_price(text, typ, None) == out


@pytest.mark.parametrize("text, out", [
    ("$65+", ("from", 65.0, None)), ("$80-$95", ("range", 80.0, 95.0)), ("starting at $45", ("from", 45.0, None)),
    ("45", ("fixed", 45.0, 45.0)), ("call", ("consult", None, None)), ("", ("consult", None, None)),
])
def test_ownsite_parse_price(text, out):
    assert ownsite.parse_price(text) == out


def test_typo_drop_needs_three_shops():
    """The 5x rule reads a price against the median of its group. With two shops the
    median is their midpoint, so [$40, $2000] dropped the REAL price and kept the typo."""
    two = {("v1", "box_braids", "", "unknown"): ((0, 40.0), 40.0), ("v2", "box_braids", "", "unknown"): ((0, 2000.0), 2000.0)}
    assert benchmark.drop_typos(dict(two)) == []
    three = {**two, ("v3", "box_braids", "", "unknown"): ((0, 45.0), 45.0)}
    assert benchmark.drop_typos(three) == [("v2", "box_braids", "", "unknown")]
    assert ("v2", "box_braids", "", "unknown") not in three
