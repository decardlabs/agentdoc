"""
Customer Service Agent - 客服 Agent 核心逻辑
使用 LLM 理解用户意图，调用工具完成客服任务
"""

import os
import logging
from typing import Dict, List, Any, Optional
from pydantic import BaseModel
from datetime import datetime
import json

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)


class IntentResult(BaseModel):
    """意图识别结果"""
    intent: str
    confidence: float
    entities: Dict[str, Any]
    requires_tool: bool
    tool_name: Optional[str] = None
    tool_args: Optional[Dict] = None


class AgentResponse(BaseModel):
    """Agent 响应"""
    reply: str
    intent: str
    confidence: float
    tool_used: Optional[str] = None
    data: Optional[Dict] = None


class ConversationHistory:
    """会话历史管理"""

    def __init__(self, max_turns: int = 10):
        self.max_turns = max_turns
        self.history: Dict[str, List[Dict]] = {}

    def add_message(self, session_id: str, role: str, content: str):
        """添加消息到历史"""
        if session_id not in self.history:
            self.history[session_id] = []

        self.history[session_id].append({
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat()
        })

        if len(self.history[session_id]) > self.max_turns * 2:
            self.history[session_id] = self.history[session_id][-self.max_turns * 2:]

    def get_history(self, session_id: str) -> List[Dict]:
        """获取会话历史"""
        return self.history.get(session_id, [])

    def clear(self, session_id: str):
        """清除会话历史"""
        if session_id in self.history:
            del self.history[session_id]


class CustomerServiceAgent:
    """智能客服 Agent"""

    def __init__(self):
        self.llm_model = os.getenv("LLM_MODEL", "gpt-4o-mini")
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.history_manager = ConversationHistory()
        self.knowledge_base = self._load_knowledge_base()

    async def handle_message(
        self,
        user_id: str,
        message: str,
        session_id: str
    ) -> Dict[str, Any]:
        """
        处理用户消息

        Args:
            user_id: 用户 ID
            message: 用户消息
            session_id: 会话 ID

        Returns:
            响应字典
        """
        logger.info(f"处理消息: user={user_id}, session={session_id}, msg={message[:50]}...")

        self.history_manager.add_message(session_id, "user", message)

        intent_result = await self._recognize_intent(message, session_id)

        if intent_result.requires_tool and intent_result.tool_name:
            tool_result = await self._execute_tool(
                tool_name=intent_result.tool_name,
                tool_args=intent_result.tool_args or {}
            )

            reply = await self._generate_reply_with_tool_result(
                message=message,
                intent=intent_result.intent,
                tool_result=tool_result,
                session_id=session_id
            )
        else:
            reply = await self._generate_direct_reply(message, session_id)

        self.history_manager.add_message(session_id, "assistant", reply)

        return {
            "reply": reply,
            "session_id": session_id,
            "intent": intent_result.intent,
            "confidence": intent_result.confidence,
            "tool_used": intent_result.tool_name if intent_result.requires_tool else None
        }

    async def _recognize_intent(self, message: str, session_id: str) -> IntentResult:
        """识别用户意图"""
        history = self.history_manager.get_history(session_id)

        prompt = f"""你是智能客服的意图识别模块。请分析用户消息的意图。

## 上下文
最近的对话历史：
{self._format_history(history[-5:]) if history else "（无历史）"}

## 用户当前消息
{message}

## 可选意图
- query_order: 查询订单
- cancel_order: 取消订单
- return_refund: 退货退款
- query_shipping: 查询物流
- product_inquiry: 商品咨询
- complaint: 投诉建议
- greeting: 问候
- fallback: 无法理解

## 可选工具
- query_order: 查询订单信息
- cancel_order: 取消订单
- query_shipping: 查询物流信息
- search_kb: 搜索知识库

请以 JSON 格式输出：
```json
{{
  "intent": "意图名称",
  "confidence": 0.95,
  "entities": {{"order_id": "12345"}},
  "requires_tool": true,
  "tool_name": "query_order",
  "tool_args": {{"order_id": "12345"}}
}}
```

只输出 JSON，不要有其他内容。
"""

        try:
            import openai
            openai.api_key = self.openai_api_key

            response = openai.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {"role": "system", "content": "你是意图识别专家。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500,
                response_format={"type": "json_object"}
            )

            content = response.choices[0].message.content
            result = json.loads(content)

            return IntentResult(
                intent=result.get("intent", "fallback"),
                confidence=result.get("confidence", 0.5),
                entities=result.get("entities", {}),
                requires_tool=result.get("requires_tool", False),
                tool_name=result.get("tool_name"),
                tool_args=result.get("tool_args")
            )

        except Exception as e:
            logger.error(f"意图识别失败: {str(e)}")
            return IntentResult(
                intent="fallback",
                confidence=0.3,
                entities={},
                requires_tool=False
            )

    async def _execute_tool(self, tool_name: str, tool_args: Dict) -> Dict:
        """执行工具"""
        from src.tools.customer_tools import CustomerTools

        tools = CustomerTools()

        if tool_name == "query_order":
            return await tools.query_order(**tool_args)
        elif tool_name == "cancel_order":
            return await tools.cancel_order(**tool_args)
        elif tool_name == "query_shipping":
            return await tools.query_shipping(**tool_args)
        elif tool_name == "search_kb":
            return await tools.search_knowledge_base(**tool_args)
        else:
            logger.warning(f"未知工具: {tool_name}")
            return {"error": f"未知工具: {tool_name}"}

    async def _generate_reply_with_tool_result(
        self,
        message: str,
        intent: str,
        tool_result: Dict,
        session_id: str
    ) -> str:
        """根据工具执行结果生成回复"""
        history = self.history_manager.get_history(session_id)

        prompt = f"""你是智能客服助手。请根据工具执行结果为用户生成友好的回复。

## 用户消息
{message}

## 意图
{intent}

## 工具执行结果
{json.dumps(tool_result, ensure_ascii=False, indent=2)}

## 对话历史
{self._format_history(history[-5:]) if history else "（无历史）"}

请生成专业、友好、简洁的回复。不要提及"工具"或"API"，直接以客服口吻回答。
"""

        try:
            import openai
            openai.api_key = self.openai_api_key

            response = openai.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {"role": "system", "content": "你是专业、友好的智能客服助手。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"生成回复失败: {str(e)}")
            return "很抱歉，系统暂时无法处理您的请求，请稍后再试或联系人工客服。"

    async def _generate_direct_reply(self, message: str, session_id: str) -> str:
        """直接生成回复（无需调用工具）"""
        history = self.history_manager.get_history(session_id)

        prompt = f"""你是智能客服助手。请回复用户消息。

## 对话历史
{self._format_history(history[-5:]) if history else "（无历史）"}

## 用户消息
{message}

请生成专业、友好、简洁的回复。
"""

        try:
            import openai
            openai.api_key = self.openai_api_key

            response = openai.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {"role": "system", "content": "你是专业、友好的智能客服助手。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"生成回复失败: {str(e)}")
            return "很抱歉，系统暂时无法处理您的请求，请稍后再试或联系人工客服。"

    def get_session_history(self, session_id: str) -> List[Dict]:
        """获取会话历史"""
        return self.history_manager.get_history(session_id)

    def clear_session(self, session_id: str):
        """清除会话历史"""
        self.history_manager.clear(session_id)

    def _format_history(self, history: List[Dict]) -> str:
        """格式化历史记录"""
        formatted = []
        for msg in history:
            role = "用户" if msg["role"] == "user" else "客服"
            formatted.append(f"{role}: {msg['content']}")
        return "\n".join(formatted) if formatted else "（无）"

    def _load_knowledge_base(self) -> Dict:
        """加载知识库"""
        return {
            "company_name": "示例科技",
            "support_phone": "400-123-4567",
            "support_hours": "9:00-18:00",
            "return_policy": "7天无理由退货，30天质量问题换货",
            "shipping_policy": "全场满99元包邮，偏远地区除外"
        }
