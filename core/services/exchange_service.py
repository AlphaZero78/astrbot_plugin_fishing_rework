from typing import Dict, Any, List

from astrbot.api import logger

from .exchange_price_service import ExchangePriceService
from .exchange_inventory_service import ExchangeInventoryService
from .exchange_account_service import ExchangeAccountService
from ..repositories.abstract_repository import AbstractExchangeRepository, AbstractUserRepository, AbstractLogRepository


class ExchangeService:
    """交易所主服务 - 协调其他服务"""
    
    def __init__(self, user_repo: AbstractUserRepository, exchange_repo: AbstractExchangeRepository, 
                 config: Dict[str, Any], log_repo: AbstractLogRepository, market_service=None):
        self.user_repo = user_repo
        self.exchange_repo = exchange_repo
        self.log_repo = log_repo
        self.config = config
        
        # 初始化子服务
        self.price_service = ExchangePriceService(exchange_repo, config)
        self.inventory_service = ExchangeInventoryService(user_repo, exchange_repo, config, log_repo, market_service)
        self.account_service = ExchangeAccountService(user_repo)
        
        # 商品定义（用于兼容性）
        self.commodities = self.price_service.commodities

    def apply_config(self, config: Dict[str, Any]) -> None:
        self.config = config
        self.price_service.apply_config(config)
        self.inventory_service.apply_config(config)

    # 价格管理相关方法
    def get_market_status(self) -> Dict[str, Any]:
        """获取市场状态"""
        return self.price_service.get_market_status()

    def get_price_history(self, days: int = 7) -> Dict[str, Any]:
        """获取价格历史"""
        return self.price_service.get_price_history(days)

    def manual_update_prices(self) -> Dict[str, Any]:
        """手动更新价格（管理员）"""
        return self.price_service.manual_update_prices()

    def reset_prices_to_initial(self) -> Dict[str, Any]:
        """重置价格到初始值（管理员）"""
        return self.price_service.reset_prices_to_initial()

    def update_daily_prices(self):
        """更新每日价格"""
        return self.price_service.update_daily_prices()

    def start_daily_price_update_task(self):
        """启动每日价格更新任务"""
        return self.price_service.start_daily_price_update_task()

    def stop_daily_price_update_task(self):
        """停止每日价格更新任务"""
        return self.price_service.stop_daily_price_update_task()

    # 账户管理相关方法
    def open_exchange_account(self, user_id: str) -> Dict[str, Any]:
        """开通交易所账户"""
        return self.account_service.open_exchange_account(user_id)

    def check_exchange_account(self, user_id: str) -> Dict[str, Any]:
        """检查交易所账户状态"""
        return self.account_service.check_exchange_account(user_id)

    def get_capacity_status(self, user_id: str) -> Dict[str, Any]:
        user = self.user_repo.get_by_id(user_id)
        if not user:
            return {"success": False, "message": "用户不存在"}
        if not user.exchange_account_status:
            return {
                "success": False,
                "message": "请先使用「交易所 开户」开通账户",
            }
        current_quantity = (
            self.inventory_service._get_user_total_commodity_quantity(user_id)
        )
        capacity = max(
            1,
            getattr(
                user,
                "exchange_capacity",
                self.config.get("exchange", {}).get("capacity", 1000),
            ),
        )
        next_upgrade = next(
            (
                item
                for item in self.config.get("exchange", {}).get(
                    "capacity_upgrades", []
                )
                if item.get("from") == capacity
            ),
            None,
        )
        return {
            "success": True,
            "current_quantity": current_quantity,
            "capacity": capacity,
            "next_upgrade": next_upgrade,
        }

    def upgrade_capacity(self, user_id: str) -> Dict[str, Any]:
        status = self.get_capacity_status(user_id)
        if not status.get("success"):
            return status
        next_upgrade = status.get("next_upgrade")
        if not next_upgrade:
            return {
                "success": False,
                "message": "交易所容量已达到最大，无法再升级",
            }
        user = self.user_repo.get_by_id(user_id)
        cost = int(next_upgrade["cost"])
        if user.coins < cost:
            return {
                "success": False,
                "message": f"金币不足，升级需要 {cost:,} 金币",
            }
        user.coins -= cost
        user.exchange_capacity = int(next_upgrade["to"])
        self.user_repo.update(user)
        return {
            "success": True,
            "old_capacity": status["capacity"],
            "new_capacity": user.exchange_capacity,
            "cost": cost,
        }

    # 库存管理相关方法
    def get_user_commodities(self, user_id: str) -> List:
        """获取用户的大宗商品库存"""
        return self.inventory_service.get_user_commodities(user_id)

    def get_user_inventory(self, user_id: str) -> Dict[str, Any]:
        """获取用户库存信息"""
        return self.inventory_service.get_user_inventory(user_id)

    def purchase_commodity(self, user_id: str, commodity_id: str, quantity: int, current_price: int) -> Dict[str, Any]:
        """购买大宗商品"""
        return self.inventory_service.purchase_commodity(user_id, commodity_id, quantity, current_price)

    def sell_commodity(self, user_id: str, commodity_id: str, quantity: int, current_price: int) -> Dict[str, Any]:
        """卖出大宗商品"""
        return self.inventory_service.sell_commodity(user_id, commodity_id, quantity, current_price)

    def sell_commodity_by_instance(self, user_id: str, instance_id: int, quantity: int, current_price: int) -> Dict[str, Any]:
        """通过实例ID卖出大宗商品"""
        return self.inventory_service.sell_commodity_by_instance(user_id, instance_id, quantity, current_price)

    def clear_all_inventory(self, user_id: str) -> Dict[str, Any]:
        """清空用户所有大宗商品库存"""
        return self.inventory_service.clear_all_inventory(user_id)

    def clear_commodity_inventory(self, user_id: str, commodity_id: str) -> Dict[str, Any]:
        """清空指定商品库存"""
        return self.inventory_service.clear_commodity_inventory(user_id, commodity_id)

    def get_user_commodity_stats(self) -> Dict[str, Any]:
        """获取用户大宗商品统计"""
        return self.inventory_service.get_user_commodity_stats()

    def _calculate_profit_loss_analysis(self, user_commodities: List[Any], current_prices: Dict[str, int]) -> Dict[str, Any]:
        """计算持仓盈亏分析"""
        return self.inventory_service.calculate_holdings_profit_loss(user_commodities, current_prices)
