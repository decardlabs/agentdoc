"""
Project 8 (Monitoring) 真实 P0 修复回归测试

针对 v0.3.0 中验证并修复的 P0 严重问题：
1. grafana/provisioning/datasources.yml: `datassources` -> `datasources`（拼写错误）
2. requirements.txt: `sqlite3` 不是有效 pip 包名，改为注释

注意：这些测试**不启动 Grafana / Prometheus**，完全离线运行。
"""

import os
import re
import sys
import unittest


class TestDatasourceSpelling(unittest.TestCase):
    """测试 datasources.yml 拼写正确"""

    def test_datasource_key_correct(self):
        """datasources.yml 顶层键必须为 'datasources'（不能多一个 s）"""
        ds_path = os.path.join(
            os.path.dirname(__file__),
            "..", "grafana", "provisioning", "datasources.yml"
        )
        with open(ds_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 不能有 'datassources'（双 s 错误）
        self.assertNotIn("datassources", content,
                         "Grafana datasources.yml 不能有 'datassources'（拼写错误，正确是 'datasources'）")

        # 必须有 'datasources:'（注意冒号）
        self.assertIn("datasources:", content,
                      "datasources.yml 顶层必须有 'datasources:' 键")

    def test_yaml_loads(self):
        """datasources.yml 必须是合法 YAML（datasources 节点存在）"""
        ds_path = os.path.join(
            os.path.dirname(__file__),
            "..", "grafana", "provisioning", "datasources.yml"
        )
        with open(ds_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 用 PyYAML 解析（如果可用），否则静态分析
        try:
            import yaml
            data = yaml.safe_load(content)
            # 顶层必须有 datasources 键
            self.assertIn("datasources", data,
                          "YAML 解析后顶层必须有 'datasources' 键")
            self.assertIsInstance(data["datasources"], list,
                                  "'datasources' 必须是 list")
        except ImportError:
            # 没装 pyyaml，至少确保 'datasources:' 字符串在
            self.assertIn("datasources:", content,
                          "datasources.yml 顶层必须有 'datasources:' 键")

    def test_prometheus_datasource_present(self):
        """至少要有一个 Prometheus 数据源配置"""
        ds_path = os.path.join(
            os.path.dirname(__file__),
            "..", "grafana", "provisioning", "datasources.yml"
        )
        with open(ds_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 必须有 Prometheus 数据源
        self.assertIn("name: Prometheus", content,
                      "datasources.yml 必须有 Prometheus 数据源")
        self.assertIn("type: prometheus", content,
                      "Prometheus 数据源必须有 type: prometheus")


class TestRequirementsNoSQLite3(unittest.TestCase):
    """测试 requirements.txt 不含 sqlite3 这个无效 pip 包名"""

    def test_no_sqlite3_in_requirements(self):
        """requirements.txt 不能有 'sqlite3' 作为包名（内置模块不是 pip 包）"""
        req_path = os.path.join(
            os.path.dirname(__file__), "..", "requirements.txt"
        )
        with open(req_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        for line in lines:
            stripped = line.strip()
            # 跳过空行和注释
            if not stripped or stripped.startswith("#"):
                continue
            # 检查是否是裸 sqlite3（不是以 # 开头的注释行）
            self.assertFalse(
                stripped.startswith("sqlite3"),
                f"requirements.txt 不能有裸 'sqlite3' 包（内置模块，pip install 会失败）: {stripped}"
            )

    def test_sqlite3_only_as_comment(self):
        """'sqlite3' 字符串只能以注释形式出现"""
        req_path = os.path.join(
            os.path.dirname(__file__), "..", "requirements.txt"
        )
        with open(req_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 找所有非注释行包含 sqlite3 的
        for line in content.split("\n"):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if "sqlite3" in stripped:
                self.fail(f"requirements.txt 非注释行不能含 'sqlite3': {stripped}")


class TestOtherRequiredPackages(unittest.TestCase):
    """测试关键依赖都在 requirements.txt 中"""

    def test_prometheus_client_present(self):
        """prometheus-client 必须存在"""
        req_path = os.path.join(
            os.path.dirname(__file__), "..", "requirements.txt"
        )
        with open(req_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("prometheus-client", content,
                      "requirements.txt 必须包含 prometheus-client")

    def test_fastapi_present(self):
        """fastapi 必须存在"""
        req_path = os.path.join(
            os.path.dirname(__file__), "..", "requirements.txt"
        )
        with open(req_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("fastapi", content,
                      "requirements.txt 必须包含 fastapi")


if __name__ == "__main__":
    unittest.main(verbosity=2)
