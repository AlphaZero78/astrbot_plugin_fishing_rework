from astrbot_plugin_fishing.draw.economy import (
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
