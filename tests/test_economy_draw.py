from astrbot_plugin_fishing.draw.economy import (
    _smooth_curve,
    draw_economy_panel,
    save_economy_image,
)


def test_economy_panel_draws_and_saves(tmp_path):
    image = draw_economy_panel(
        "玩家市场",
        "当前展示 2 条挂单",
        [
            {
                "title": "鱼竿",
                "rows": [
                    {
                        "primary": "练习鱼竿 x1  ID R1234",
                        "secondary": "适合新手使用的鱼竿",
                        "meta": "1,200 金币 · 测试卖家",
                    }
                ],
            },
            {
                "title": "鱼类",
                "rows": [
                    {
                        "primary": "鲤鱼 x3  ID F5678",
                        "meta": "360 金币 · 匿名卖家",
                    }
                ],
            },
        ],
        "购买：购买 市场ID",
    )

    assert image.mode == "RGB"
    assert image.width == 1000
    assert image.height >= 280

    path = save_economy_image(image, "test_market", str(tmp_path))
    assert path.endswith(".png")
    assert (tmp_path / "temp_images").is_dir()


def test_economy_panel_draws_price_chart_on_right():
    image = draw_economy_panel(
        "大宗商品交易所",
        "2026-06-20 · neutral · stable · 平衡",
        [
            {
                "title": "实时行情",
                "rows": [
                    {
                        "primary": "鱼干 5,798 金币",
                        "secondary": "经过晾晒处理的鱼类，保质期较长",
                        "meta": "下跌 9.7%",
                    },
                    {
                        "primary": "鱼油 7,148 金币",
                        "secondary": "从鱼类中提取的油脂，用途广泛",
                        "meta": "下跌 2.6%",
                    },
                    {
                        "primary": "鱼卵 10,794 金币",
                        "secondary": "珍贵的鱼类卵子，营养价值极高",
                        "meta": "下跌 7.9%",
                    },
                ],
                "chart": {
                    "title": "价格趋势（最近 7 天）",
                    "labels": ["06-14", "06-16", "06-18", "06-20"],
                    "series": [
                        {
                            "name": "鱼干",
                            "values": [6400, 6200, 6100, 5798],
                            "color": (0, 123, 255),
                        },
                        {
                            "name": "鱼卵",
                            "values": [11800, 12100, 11600, 10794],
                            "color": (255, 176, 0),
                        },
                        {
                            "name": "鱼油",
                            "values": [7000, 7600, 7300, 7148],
                            "color": (40, 167, 69),
                        },
                    ],
                },
            }
        ],
    )

    chart_region = image.crop((500, 150, 950, 410))
    colors = chart_region.getcolors(maxcolors=1_000_000)
    assert colors is not None
    assert len(colors) > 20


def test_price_curve_adds_smooth_intermediate_points():
    points = [(0, 20), (20, 5), (40, 25), (60, 10)]
    curve = _smooth_curve(points)

    assert curve[0] == (0.0, 20.0)
    assert curve[-1] == (60.0, 10.0)
    assert len(curve) > len(points) * 10
