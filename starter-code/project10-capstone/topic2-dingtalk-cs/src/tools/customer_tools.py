"""
客服工具集
提供订单查询、物流查询、知识库搜索等工具
"""

import os
import logging
import aiohttp
import json
from typing import Dict, List, Any, Optional
from datetime import datetime

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)


class CustomerTools:
    """客服工具集"""

    def __init__(self):
        self.api_base = os.getenv("BACKEND_API_BASE", "https://api.example.com")
        self.api_key = os.getenv("BACKEND_API_KEY", "")

    async def query_order(self, order_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        查询订单信息

        Args:
            order_id: 订单 ID
            user_id: 用户 ID (可选，用于验证权限)

        Returns:
            订单信息字典
        """
        logger.info(f"查询订单: order_id={order_id}")

        mock_orders = {
            "12345": {
                "order_id": "12345",
                "status": "已发货",
                "product_name": "无线蓝牙耳机",
                "quantity": 1,
                "amount": 199.00,
                "create_time": "2026-01-10 14:30:00",
                "shipping_id": "SF1234567890"
            },
            "67890": {
                "order_id": "67890",
                "status": "待付款",
                "product_name": "机械键盘",
                "quantity": 1,
                "amount": 399.00,
                "create_time": "2026-01-15 10:15:00",
                "shipping_id": None
            }
        }

        if order_id in mock_orders:
            return {
                "success": True,
                "order": mock_orders[order_id]
            }
        else:
            return {
                "success": False,
                "error": f"未找到订单 {order_id}",
                " suggestion": "请检查订单号是否正确，或联系人工客服查询"
            }

    async def cancel_order(self, order_id: str, reason: Optional[str] = None) -> Dict[str, Any]:
        """
        取消订单

        Args:
            order_id: 订单 ID
            reason: 取消原因

        Returns:
            取消结果
        """
        logger.info(f"取消订单: order_id={order_id}, reason={reason}")

        mock_orders = {
            "12345": {"status": "已发货", "cancelable": False},
            "67890": {"status": "待付款", "cancelable": True}
        }

        if order_id not in mock_orders:
            return {
                "success": False,
                "error": f"未找到订单 {order_id}"
            }

        order_info = mock_orders[order_id]

        if not order_info["cancelable"]:
            return {
                "success": False,
                "error": f"订单 {order_id} 状态为 '{order_info['status']}'，无法取消",
                "suggestion": "如需取消，请联系人工客服处理"
            }

        return {
            "success": True,
            "order_id": order_id,
            "status": "已取消",
            "refund_amount": 399.00,
            "refund_time": "1-3 个工作日"
        }

    async def query_shipping(self, order_id: str) -> Dict[str, Any]:
        """
        查询物流信息

        Args:
            order_id: 订单 ID

        Returns:
            物流信息字典
        """
        logger.info(f"查询物流: order_id={order_id}")

        mock_shipping = {
            "12345": {
                "shipping_id": "SF1234567890",
                "carrier": "顺丰速运",
                "status": "运输中",
                "events": [
                    {"time": "2026-01-13 09:00:00", "description": "快件已到达北京转运中心"},
                    {"time": "2026-01-12 18:30:00", "description": "快件已从深圳发出"},
                    {"time": "2026-01-11 15:00:00", "description": "商家已发货"}
                ]
            }
        }

        if order_id in mock_shipping:
            return {
                "success": True,
                "shipping": mock_shipping[order_id]
            }
        else:
            return {
                "success": False,
                "error": f"未找到订单 {order_id} 的物流信息",
                "suggestion": "订单可能尚未发货，请确认订单状态"
            }

    async def search_knowledge_base(self, query: str, category: Optional[str] = None) -> Dict[str, Any]:
        """
        搜索知识库

        Args:
            query: 搜索关键词
            category: 分类 (可选)

        Returns:
            搜索结果
        """
        logger.info(f"搜索知识库: query={query}, category={category}")

        mock_kb = [
            {
                "id": "kb001",
                "title": "如何申请退货",
                "category": "return_policy",
                "content": "您可以在订单详情页点击'申请退货'按钮，7天内无理由退货。退货审核通过后，请将商品寄回，我们收到商品后会在1-3个工作日内退款。"
            },
            {
                "id": "kb002",
                "title": "运费政策",
                "category": "shipping",
                "content": "全场满99元包邮（偏远地区除外）。偏远地区包括：新疆、西藏、内蒙古、青海、宁夏。"
            },
            {
                "id": "kb003",
                "title": "支付问题",
                "category": "payment",
                "content": "我们支持支付宝、微信支付、银行卡支付。如支付失败，请检查银行卡余额或联系银行。"
            }
        ]

        results = []
        for item in mock_kb:
            if query.lower() in item["title"].lower() or query.lower() in item["content"].lower():
                if category is None or item["category"] == category:
                    results.append(item)

        if results:
            return {
                "success": True,
                "results": results,
                "count": len(results)
            }
        else:
            return {
                "success": False,
                "error": f"未找到与 '{query}' 相关的知识库条目",
                "suggestion": "请尝试其他关键词，或联系人工客服"
            }

    async def create_ticket(self, user_id: str, issue_type: str, description: str) -> Dict[str, Any]:
        """
        创建工单

        Args:
            user_id: 用户 ID
            issue_type: 问题类型
            description: 问题描述

        Returns:
            创建结果
        """
        logger.info(f"创建工单: user_id={user_id}, type={issue_type}")

        ticket_id = f"TICKET-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        return {
            "success": True,
            "ticket_id": ticket_id,
            "user_id": user_id,
            "issue_type": issue_type,
            "description": description,
            "status": "open",
            "create_time": datetime.now().isoformat(),
            "estimated_response": "24 小时内"
        }

    async def transfer_to_human(self, user_id: str, reason: str) -> Dict[str, Any]:
        """
        转接人工客服

        Args:
            user_id: 用户 ID
            reason: 转接原因

        Returns:
            转接结果
        """
        logger.info(f"转接人工客服: user_id={user_id}, reason={reason}")

        return {
            "success": True,
            "user_id": user_id,
            "reason": reason,
            "queue_position": 3,
            "estimated_wait": "5 分钟",
            "message": "已为您转接人工客服，请稍候"
        }


class KnowledgeBase:
    """知识库管理"""

    def __init__(self, kb_file: Optional[str] = None):
        self.kb_file = kb_file or "data/knowledge_base.json"
        self.entries = self._load_entries()

    def _load_entries(self) -> List[Dict]:
        """加载知识库条目"""
        try:
            import os
            if not os.path.exists(self.kb_file):
                return []

            with open(self.kb_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载知识库失败: {str(e)}")
            return []

    def search(self, query: str, top_k: int = 3) -> List[Dict]:
        """
        搜索知识库

        Args:
            query: 查询字符串
            top_k: 返回 top-k 结果

        Returns:
            匹配的条目列表
        """
        results = []
        query_lower = query.lower()

        for entry in self.entries:
            score = 0
            title_lower = entry.get("title", "").lower()
            content_lower = entry.get("content", "").lower()

            if query_lower in title_lower:
                score += 2
            if query_lower in content_lower:
                score += 1

            if score > 0:
                results.append({
                    **entry,
                    "score": score
                })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def add_entry(self, title: str, content: str, category: str) -> Dict:
        """添加知识库条目"""
        entry = {
            "id": f"kb{len(self.entries) + 1:03d}",
            "title": title,
            "content": content,
            "category": category,
            "create_time": datetime.now().isoformat()
        }

        self.entries.append(entry)
        self._save_entries()

        return entry

    def _save_entries(self):
        """保存知识库条目"""
        try:
            import os
            os.makedirs(os.path.dirname(self.kb_file), exist_ok=True)
            with open(self.kb_file, 'w', encoding='utf-8') as f:
                json.dump(self.entries, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存知识库失败: {str(e)}")
