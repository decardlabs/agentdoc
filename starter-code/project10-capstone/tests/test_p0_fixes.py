"""
Project 10 (Capstone) 真实 P0 修复回归测试

针对 v0.3.0 中验证并修复的 P0 严重问题：
1. cs_agent.py (topic2): 不能用 `openai.api_key = ...` 全局变量
   （多线程下竞争条件），改用 `OpenAI(api_key=...)` 客户端实例
2. 各 topic 的 .env.example + docker-compose.yml:
   APP_PORT 默认值必须不同（8001 / 8002 / 8003 / 8004）
   避免同一台机器部署冲突

注意：这些测试**不调用真实 LLM / 部署 Docker**，完全离线运行。
"""

import os
import re
import sys
import unittest


PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")  # capstone/
TOPICS = ["topic1-github-review", "topic2-dingtalk-cs",
          "topic3-obsidian-agent", "topic4-marketing-agent"]
EXPECTED_PORTS = {
    "topic1-github-review": "8001",
    "topic2-dingtalk-cs": "8002",
    "topic3-obsidian-agent": "8003",
    "topic4-marketing-agent": "8004",
}


class TestPortsUnique(unittest.TestCase):
    """测试 4 个 topic 的 APP_PORT 互不冲突"""

    def test_each_topic_has_distinct_port(self):
        """每个 topic 的 .env.example APP_PORT 必须等于预期值"""
        for topic, expected in EXPECTED_PORTS.items():
            env_path = os.path.join(PROJECT_ROOT, topic, ".env.example")
            with open(env_path, "r", encoding="utf-8") as f:
                content = f.read()

            # 找 APP_PORT=xxxx
            match = re.search(r"^APP_PORT=(\d+)$", content, re.MULTILINE)
            self.assertIsNotNone(match,
                                 f"{topic}/.env.example 必须有 APP_PORT=xxxx 配置")
            actual = match.group(1)
            self.assertEqual(actual, expected,
                             f"{topic} 的 APP_PORT 应该是 {expected}（避免冲突），实际 {actual}")

    def test_docker_compose_uses_same_port(self):
        """docker-compose.yml 端口映射必须和 .env.example APP_PORT 一致"""
        for topic, expected in EXPECTED_PORTS.items():
            compose_path = os.path.join(PROJECT_ROOT, topic, "docker-compose.yml")
            with open(compose_path, "r", encoding="utf-8") as f:
                content = f.read()

            # 找 ports 配置中的 ${APP_PORT:-XXXX}
            match = re.search(r"\$\{APP_PORT:-(\d+)\}:8000", content)
            self.assertIsNotNone(match,
                                 f"{topic}/docker-compose.yml 缺少 ${{APP_PORT:-XXXX}}:8000")
            actual = match.group(1)
            self.assertEqual(actual, expected,
                             f"{topic} docker-compose.yml 默认端口应与 .env.example 一致")

    def test_no_topic_uses_default_8000(self):
        """4 个 topic 中没有任何一个使用默认 8000（避免与其他服务冲突）"""
        for topic in TOPICS:
            env_path = os.path.join(PROJECT_ROOT, topic, ".env.example")
            with open(env_path, "r", encoding="utf-8") as f:
                content = f.read()

            self.assertNotIn("APP_PORT=8000", content,
                             f"{topic} 不能用 APP_PORT=8000（与 Chroma/uvicorn 默认冲突）")


class TestNoOpenAIApiKeyRace(unittest.TestCase):
    """测试不再使用 openai.api_key 全局变量（多线程竞争条件）"""

    def test_cs_agent_uses_openai_client(self):
        """cs_agent.py 必须用 OpenAI 客户端实例"""
        cs_path = os.path.join(
            PROJECT_ROOT, "topic2-dingtalk-cs", "src", "agent", "cs_agent.py"
        )
        with open(cs_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 必须有 OpenAI client 模式
        self.assertIn("from openai import OpenAI", content,
                      "cs_agent.py 必须 from openai import OpenAI")
        self.assertIn("client = OpenAI(api_key=", content,
                      "cs_agent.py 必须用 client = OpenAI(api_key=...) 实例化客户端")

        # 不能有 openai.api_key 全局赋值
        self.assertNotIn("openai.api_key =", content,
                         "cs_agent.py 不能用 'openai.api_key = ...'（多线程竞争条件）")

    def test_no_openai_api_key_in_all_topics(self):
        """全部 4 个 topic 中都不能有 openai.api_key 全局赋值"""
        for topic in TOPICS:
            topic_dir = os.path.join(PROJECT_ROOT, topic)
            for root, _, files in os.walk(topic_dir):
                for fname in files:
                    if not fname.endswith(".py"):
                        continue
                    fpath = os.path.join(root, fname)
                    with open(fpath, "r", encoding="utf-8") as f:
                        content = f.read()
                    self.assertNotIn(
                        "openai.api_key =",
                        content,
                        f"{fpath} 中不能用 'openai.api_key ='（应改用 OpenAI(api_key=...) 客户端实例）"
                    )

    def test_all_topics_use_openai_client(self):
        """4 个 topic 中都用 OpenAI 客户端实例"""
        topic_counts = {}
        for topic in TOPICS:
            topic_dir = os.path.join(PROJECT_ROOT, topic)
            count = 0
            for root, _, files in os.walk(topic_dir):
                for fname in files:
                    if not fname.endswith(".py"):
                        continue
                    fpath = os.path.join(root, fname)
                    with open(fpath, "r", encoding="utf-8") as f:
                        content = f.read()
                    count += content.count("from openai import OpenAI")
            topic_counts[topic] = count
            # 至少有一个 from openai import OpenAI
            self.assertGreater(count, 0,
                               f"{topic} 中应至少有一处 'from openai import OpenAI'，实际 0")


class TestCustomerServiceAgent(unittest.TestCase):
    """测试 CustomerServiceAgent 基本行为（mock OpenAI）"""

    def test_intent_result_fallback_on_error(self):
        """_recognize_intent 在 LLM 失败时应返回 fallback IntentResult"""
        sys.path.insert(0, os.path.join(
            PROJECT_ROOT, "topic2-dingtalk-cs", "src"
        ))

        from unittest.mock import patch, MagicMock
        with patch.dict("os.environ", {"OPENAI_API_KEY": "fake"}):
            # 不真正 mock openai, 只静态检查 fallback 逻辑
            cs_path = os.path.join(
                PROJECT_ROOT, "topic2-dingtalk-cs", "src", "agent", "cs_agent.py"
            )
            with open(cs_path, "r", encoding="utf-8") as f:
                content = f.read()

            self.assertIn("intent=\"fallback\"", content,
                          "_recognize_intent 出错时应返回 IntentResult(intent='fallback')")
            self.assertIn("requires_tool=False", content,
                          "fallback 必须 requires_tool=False")


if __name__ == "__main__":
    unittest.main(verbosity=2)
