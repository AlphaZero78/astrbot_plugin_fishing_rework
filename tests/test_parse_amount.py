import pytest
from decimal import Decimal
from astrbot_plugin_fishing.utils import (
    calculate_percentage_reward,
    parse_amount,
    parse_percentage_rate,
)


def test_parse_plain_number():
    assert parse_amount("1000") == 1000
    assert parse_amount("1,000,000") == 1000000


def test_parse_arabic_with_unit():
    assert parse_amount("1万") == 10000
    assert parse_amount("1千万") == 10000000
    assert parse_amount("13百万") == 13000000


def test_parse_chinese_numbers():
    assert parse_amount("一") == 1
    assert parse_amount("十") == 10
    assert parse_amount("一百二十三") == 123
    assert parse_amount("一千三百万") == 13000000
    assert parse_amount("两万") == 20000


def test_invalid():
    with pytest.raises(ValueError):
        parse_amount("")
    with pytest.raises(ValueError):
        parse_amount("abc")


def test_percentage_reward_rounds_down():
    assert parse_percentage_rate("10%") == Decimal("0.1")
    assert parse_percentage_rate("2.5％") == Decimal("0.025")
    assert calculate_percentage_reward(12_345, "2.5%") == 308
    assert calculate_percentage_reward(9, "10%") == 0


@pytest.mark.parametrize("value", ["0%", "-1%", "abc%", "10"])
def test_invalid_percentage(value):
    with pytest.raises(ValueError):
        parse_percentage_rate(value)
