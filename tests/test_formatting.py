from astrbot_plugin_fishing.core.formatting import (
    format_coins,
    format_number,
    format_percent,
)


def test_format_number_removes_float_noise_and_trailing_zeroes():
    assert format_number(1.10002432) == "1.1"
    assert format_number(0.02500608) == "0.025"
    assert format_number(12.0) == "12"
    assert format_number(-0.0) == "0"


def test_format_percent_uses_fractional_input():
    assert format_percent(0.05001216) == "5"
    assert format_percent(0.02500608) == "2.5"


def test_format_coins_adds_grouping():
    assert format_coins(12345) == "12,345"
    assert format_coins("9000") == "9,000"
