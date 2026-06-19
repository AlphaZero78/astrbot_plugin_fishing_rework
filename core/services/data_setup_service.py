from ..repositories.abstract_repository import (
    AbstractItemTemplateRepository,
    AbstractGachaRepository,
    AbstractShopRepository,
)
from ..initial_data import (
    FISH_DATA,
    BAIT_DATA,
    ROD_DATA,
    ACCESSORY_DATA,
    TITLE_DATA,
    GACHA_POOL,
    GACHA_POOL_ITEM_DATA,
    ITEM_DATA,
    SHOP_DATA,
    SHOP_ITEM_DATA,
    SHOP_ITEM_COST_DATA,
    SHOP_ITEM_REWARD_DATA,
)
from ..domain.models import Item
from astrbot.api import logger


class DataSetupService:
    """负责在首次启动时初始化游戏基础数据。"""

    def __init__(
        self,
        item_template_repo: AbstractItemTemplateRepository,
        gacha_repo: AbstractGachaRepository,
        shop_repo: AbstractShopRepository,
    ):
        """
        初始化数据设置服务。

        Args:
            item_template_repo: 物品模板仓储的实例，用于与数据库交互。
            gacha_repo: 抽卡仓储的实例。
            shop_repo: 商店仓储的实例。
        """
        self.gacha_repo = gacha_repo
        self.item_template_repo = item_template_repo
        self.shop_repo = shop_repo

    def setup_initial_data(self):
        """
        检查核心数据表是否为空，如果为空则进行数据填充。
        这是一个幂等操作（idempotent），可以安全地多次调用而不会重复插入数据。
        """
        try:
            existing_fish = self.item_template_repo.get_all_fish()
            if existing_fish:
                logger.info("数据库核心数据已存在，跳过初始化。")
                return
        except Exception as e:
            # 如果表不存在等数据库错误，也需要继续执行创建和插入
            logger.error(f"检查数据时发生错误 (可能是表不存在，将继续初始化): {e}")

        logger.info("检测到数据库为空或核心数据不完整，正在初始化游戏数据...")

        # 填充鱼类数据
        for fish in FISH_DATA:
            self.item_template_repo.add_fish_template({
                "name": fish[0],
                "description": fish[1],
                "rarity": fish[2],
                "base_value": fish[3],
                "min_weight": fish[4],
                "max_weight": fish[5],
                "icon_url": fish[6]
            })

        # 填充鱼饵数据
        for bait in BAIT_DATA:
            self.item_template_repo.add_bait_template({
                "name": bait[0],
                "description": bait[1],
                "rarity": bait[2],
                "effect_description": bait[3],
                "duration_minutes": bait[4],
                "cost": bait[5],
                "required_rod_rarity": bait[6],
                "success_rate_modifier": bait[7],
                "rare_chance_modifier": bait[8],
                "garbage_reduction_modifier": bait[9],
                "value_modifier": bait[10],
                "quantity_modifier": bait[11],
                "is_consumable": bait[12],
            })

        # 填充鱼竿数据
        for rod in ROD_DATA:
            self.item_template_repo.add_rod_template({
                "name": rod[0],
                "description": rod[1],
                "rarity": rod[2],
                "source": rod[3],
                "purchase_cost": rod[4],
                "bonus_fish_quality_modifier": rod[5],
                "bonus_fish_quantity_modifier": rod[6],
                "bonus_rare_fish_chance": rod[7],
                "durability": rod[8],
                "icon_url": rod[9]
            })

        # 填充饰品数据
        for acc in ACCESSORY_DATA:
            self.item_template_repo.add_accessory_template({
                "name": acc[0],
                "description": acc[1],
                "rarity": acc[2],
                "slot_type": acc[3],
                "bonus_fish_quality_modifier": acc[4],
                "bonus_fish_quantity_modifier": acc[5],
                "bonus_rare_fish_chance": acc[6],
                "bonus_coin_modifier": acc[7],
                "fishing_cooldown_modifier": acc[8],
                "other_bonus_description": acc[9],
                "icon_url": acc[10]
            })


        for title in TITLE_DATA:
            if hasattr(self.item_template_repo, "add_title_template"):
                self.item_template_repo.add_title_template({
                    "title_id": title[0],
                    "name": title[1],
                    "description": title[2],
                    "display_format": title[3]
                })

        for pool in GACHA_POOL:
            self.gacha_repo.add_pool_template(
                {
                    "pool_id": pool[0],
                    "name": pool[1],
                    "description": pool[2],
                    "cost_coins": pool[3],
                    "cost_premium_currency": pool[4],
                    "is_limited_time": pool[5],
                    "open_until": pool[6],
                }
            )

        # 填充道具数据
        self.create_initial_items()

        # --- 填充抽卡池具体物品 ---
        self._ensure_gacha_pool_items_from_initial_data()

        # --- 填充初始商店 ---
        if not self.shop_repo.get_all_shops():
            logger.info("正在初始化商店...")
            for shop_data in SHOP_DATA:
                self.shop_repo.create_shop({
                    "shop_id": shop_data[0],
                    "name": shop_data[1],
                    "description": shop_data[2],
                    "shop_type": shop_data[3],
                    "is_active": shop_data[4],
                    "start_time": shop_data[5],
                    "end_time": shop_data[6],
                    "daily_start_time": shop_data[7],
                    "daily_end_time": shop_data[8],
                    "sort_order": shop_data[9],
                })
            
            self._ensure_shop_items_from_initial_data()
            logger.info("初始商店与商品填充完成。")

        logger.info("核心游戏数据初始化完成。")

    def sync_shops_from_initial_data(self):
        """
        手动从 initial_data.py 同步商店和基础商品到数据库。
        这是一个幂等操作，可以安全地多次调用。
        """
        logger.info("正在从 initial_data.py 同步商店...")
        
        # 先确保基础数据已初始化
        self.setup_initial_data()
        
        # --- 填充初始商店 ---
        all_shops = self.shop_repo.get_all_shops()
        existing_shops_by_id = {s["shop_id"]: s for s in all_shops}
        existing_shop_names = {s["name"] for s in all_shops}
        
        for shop_data in SHOP_DATA:
            shop_payload = {
                "name": shop_data[1],
                "description": shop_data[2],
                "shop_type": shop_data[3],
                "is_active": shop_data[4],
                "start_time": shop_data[5],
                "end_time": shop_data[6],
                "daily_start_time": shop_data[7],
                "daily_end_time": shop_data[8],
                "sort_order": shop_data[9],
            }
            if shop_data[0] in existing_shops_by_id:
                self.shop_repo.update_shop(shop_data[0], shop_payload)
            elif shop_data[1] not in existing_shop_names:
                self.shop_repo.create_shop({
                    "shop_id": shop_data[0],
                    **shop_payload,
                })
                logger.info(f"创建新商店: {shop_data[1]}")

        self._ensure_shop_items_from_initial_data()

        logger.info("商店数据同步完成。")

    def _ensure_gacha_pool_items_from_initial_data(self):
        """根据 initial_data.py 中的显式配置填充卡池物品。"""
        grouped_items = {}
        for pool_id, item_type, item_id, quantity, weight in GACHA_POOL_ITEM_DATA:
            grouped_items.setdefault(pool_id, []).append({
                "item_type": item_type,
                "item_id": item_id,
                "quantity": quantity,
                "weight": weight,
            })

        for pool_id, items in grouped_items.items():
            if self.gacha_repo.get_pool_items(pool_id):
                continue
            for item_data in items:
                self.gacha_repo.add_pool_item(pool_id, item_data)

    def _ensure_shop_items_from_initial_data(self):
        """根据 initial_data.py 中的显式配置填充商店商品、成本与奖励。"""
        if not SHOP_ITEM_DATA:
            self._ensure_shop1_default_items()
            return

        for item_data in SHOP_ITEM_DATA:
            (
                item_id,
                shop_id,
                name,
                description,
                category,
                stock_total,
                per_user_limit,
                per_user_daily_limit,
                is_active,
                start_time,
                end_time,
                sort_order,
            ) = item_data

            item_payload = {
                "item_id": item_id,
                "name": name,
                "description": description,
                "category": category,
                "stock_total": stock_total,
                "per_user_limit": per_user_limit,
                "per_user_daily_limit": per_user_daily_limit,
                "is_active": is_active,
                "start_time": start_time,
                "end_time": end_time,
                "sort_order": sort_order,
            }
            if self.shop_repo.get_shop_item_by_id(item_id):
                self.shop_repo.update_shop_item(item_id, item_payload)
            else:
                self.shop_repo.create_shop_item(shop_id, {
                    **item_payload,
                    "stock_sold": 0,
                })

        initial_item_ids = {item_data[0] for item_data in SHOP_ITEM_DATA}
        for item_id in initial_item_ids:
            for cost in self.shop_repo.get_item_costs(item_id):
                self.shop_repo.delete_item_cost(cost["cost_id"])
            for reward in self.shop_repo.get_item_rewards(item_id):
                self.shop_repo.delete_item_reward(reward["reward_id"])

        for item_id, cost_type, cost_amount, cost_item_id, cost_relation, group_id, quality_level in SHOP_ITEM_COST_DATA:
            self.shop_repo.add_item_cost(item_id, {
                "cost_type": cost_type,
                "cost_amount": cost_amount,
                "cost_item_id": cost_item_id,
                "cost_relation": cost_relation,
                "group_id": group_id,
                "quality_level": quality_level,
            })

        for item_id, reward_type, reward_item_id, reward_quantity, reward_refine_level, quality_level in SHOP_ITEM_REWARD_DATA:
            self.shop_repo.add_item_reward(item_id, {
                "reward_type": reward_type,
                "reward_item_id": reward_item_id,
                "reward_quantity": reward_quantity,
                "reward_refine_level": reward_refine_level,
                "quality_level": quality_level,
            })

    def _ensure_shop1_default_items(self):
        """确保商店1有默认商品（新设计：直接创建shop_items）"""
        logger.info("正在确保商店1有默认商品...")
        
        # 获取商店1的现有商品
        shop1_items = self.shop_repo.get_shop_items(1)
        existing_item_names = {item["name"] for item in shop1_items}

        # 添加所有3星以下的鱼竿到商店1
        rod_items = []
        for rod_data in ROD_DATA:
            if rod_data[2] <= 3 and rod_data[3] == "shop" and rod_data[4] and rod_data[4] > 0:  # rarity <= 3, source=shop, has cost
                rod_items.append(rod_data)
        
        for rod_data in rod_items:
            rod_name = rod_data[0]
            rod_id = ROD_DATA.index(rod_data) + 1
            
            # 检查是否已存在同名商品
            if rod_name in existing_item_names:
                logger.info(f"鱼竿商品已存在: {rod_name}")
                continue
            
            # 创建新商品
            rod_description = rod_data[1] if len(rod_data) > 1 else ""
            logger.info(f"创建鱼竿商品: {rod_name}, 描述: {rod_description}")
            
            # 创建商品
            item_data = {
                "name": rod_name,
                "description": rod_description,
                "category": "basic",
                "is_active": True,
                "sort_order": rod_data[2] * 10,  # 按稀有度排序
            }
            created_item = self.shop_repo.create_shop_item(1, item_data)
            item_id = created_item["item_id"]
            
            # 添加成本
            self.shop_repo.add_item_cost(item_id, {
                "cost_type": "coins",
                "cost_amount": rod_data[4],
                "cost_relation": "and",
            })
            
            # 添加奖励
            self.shop_repo.add_item_reward(item_id, {
                "reward_type": "rod",
                "reward_item_id": rod_id,
                "reward_quantity": 1,
                "reward_refine_level": 1,
            })
            
            logger.info(f"已上架鱼竿: {rod_name}")

        # 添加所有有成本的鱼饵到商店1
        bait_items = []
        for bait_data in BAIT_DATA:
            if bait_data[5] > 0:  # has cost > 0
                bait_items.append(bait_data)
        
        for bait_data in bait_items:
            bait_name = bait_data[0]
            bait_id = BAIT_DATA.index(bait_data) + 1
            
            # 检查是否已存在同名商品
            if bait_name in existing_item_names:
                logger.info(f"鱼饵商品已存在: {bait_name}")
                continue
            
            # 创建新商品
            bait_description = bait_data[1] if len(bait_data) > 1 else ""
            logger.info(f"创建鱼饵商品: {bait_name}, 描述: {bait_description}")
            
            # 创建商品
            item_data = {
                "name": bait_name,
                "description": bait_description,
                "category": "basic",
                "is_active": True,
                "sort_order": bait_data[2] * 10 + 100,  # 鱼饵排在鱼竿后面
            }
            created_item = self.shop_repo.create_shop_item(1, item_data)
            item_id = created_item["item_id"]
            
            # 添加成本
            self.shop_repo.add_item_cost(item_id, {
                "cost_type": "coins",
                "cost_amount": bait_data[5],
                "cost_relation": "and",
            })
            
            # 添加奖励
            self.shop_repo.add_item_reward(item_id, {
                "reward_type": "bait",
                "reward_item_id": bait_id,
                "reward_quantity": 1,
                "reward_refine_level": 1,
            })
            
            logger.info(f"已上架鱼饵: {bait_name}")

    def sync_all_initial_data(self):
        """
        手动从 initial_data.py 同步所有设计为可同步的数据（如道具、商店）。
        """
        logger.info("--- 开始同步所有初始设定 ---")
        self.create_initial_items()
        self.sync_shops_from_initial_data()
        logger.info("--- 所有初始设定同步完成 ---")

    def create_initial_items(self):
        """创建初始的道具"""
        existing_items = self.item_template_repo.get_all()
        existing_items_by_name = {item.name: item for item in existing_items}

        items_to_create = []
        for item_data in ITEM_DATA:
            item_template = Item(
                item_id=0,
                name=item_data[1],
                description=item_data[2],
                rarity=item_data[3],
                effect_description=item_data[4],
                cost=item_data[5],
                is_consumable=item_data[6],
                icon_url=item_data[7],
                effect_type=item_data[8],
                effect_payload=item_data[9],
            )

            existing = existing_items_by_name.get(item_template.name)
            if existing:
                item_template.item_id = existing.item_id
                self.item_template_repo.update(item_template)
            else:
                items_to_create.append(
                    item_template
                )

        if items_to_create:
            logger.info(f"发现 {len(items_to_create)} 个新的道具，正在添加到数据库...")
            for item in items_to_create:
                self.item_template_repo.add(item)
            logger.info("新道具添加完成。")
        else:
            logger.info("没有发现新的道具需要添加。")

