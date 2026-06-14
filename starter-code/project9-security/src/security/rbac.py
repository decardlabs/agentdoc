"""
角色权限控制（RBAC）- 智能体工程师培养计划 项目 9
基于角色的访问控制，防止越权操作
"""

from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass, field
import logging
import os
import re

# ===========================================================
# 日志配置
# ===========================================================
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ===========================================================
# 枚举定义
# ===========================================================
class Role(Enum):
    """用户角色"""
    GUEST = "guest"         # 只读，不能调用工具
    USER = "user"           # 可调用安全工具
    POWER_USER = "power"    # 可调用大部分工具，危险操作需确认
    ADMIN = "admin"         # 全部权限，但删除/写入需二次确认
    SYSTEM = "system"       # 无限制（仅内部使用）

class ToolRisk(Enum):
    """工具风险等级"""
    SAFE = "safe"           # 纯读取，无副作用
    LOW = "low"             # 有限副作用（写入日志）
    MEDIUM = "medium"       # 修改数据
    HIGH = "high"           # 删除/执行命令
    CRITICAL = "critical"   # 系统级操作

# ===========================================================
# 数据模型
# ===========================================================
@dataclass
class ToolPolicy:
    """工具策略定义"""
    name: str
    risk: ToolRisk
    allowed_roles: List[Role]
    require_confirmation: bool = False
    require_audit: bool = False
    parameter_rules: Dict[str, Any] = field(default_factory=dict)

@dataclass
class AccessCheckResult:
    """权限检查结果"""
    allowed: bool
    reason: str
    require_human_approval: bool = False
    require_audit: bool = False
    risk_level: Optional[str] = None

# ===========================================================
# 工具访问控制
# ===========================================================
class ToolAccessControl:
    """基于角色的工具访问控制
    
    功能：
    - 定义工具策略（风险等级、允许角色、参数规则）
    - 检查工具调用权限
    - 验证工具参数
    - 记录审计日志
    """
    
    def __init__(self):
        """初始化工具访问控制"""
        # === 工具策略定义 ===
        self.tool_policies: Dict[str, ToolPolicy] = {
            "search_web": ToolPolicy(
                name="search_web",
                risk=ToolRisk.SAFE,
                allowed_roles=[Role.GUEST, Role.USER, Role.POWER_USER, Role.ADMIN],
                parameter_rules={"query": {"max_length": 500}}
            ),
            "read_url": ToolPolicy(
                name="read_url",
                risk=ToolRisk.LOW,
                allowed_roles=[Role.USER, Role.POWER_USER, Role.ADMIN],
                parameter_rules={
                    "url": {
                        "max_length": 2048,
                        "allowed_schemes": ["https", "http"],
                        "blocked_domains": ["127.0.0.1", "localhost", "0.0.0.0", "192.168.", "10.", "172.16."]
                    }
                }
            ),
            "read_file": ToolPolicy(
                name="read_file",
                risk=ToolRisk.LOW,
                allowed_roles=[Role.USER, Role.POWER_USER, Role.ADMIN],
                parameter_rules={
                    "path": {
                        "blocked_prefixes": ["/etc/", "/proc/", "/sys/", "C:\\Windows\\", "/root/"],
                        "blocked_patterns": [r"\.\./", r"\.\.\\", r"\.env$", r"\.pem$", r"id_rsa"]
                    }
                }
            ),
            "write_file": ToolPolicy(
                name="write_file",
                risk=ToolRisk.MEDIUM,
                allowed_roles=[Role.POWER_USER, Role.ADMIN],
                require_confirmation=True,
                parameter_rules={
                    "path": {"max_length": 1024},
                    "content": {"max_length": 100000}
                }
            ),
            "execute_command": ToolPolicy(
                name="execute_command",
                risk=ToolRisk.HIGH,
                allowed_roles=[Role.ADMIN],
                require_confirmation=True,
                require_audit=True,
                parameter_rules={
                    "command": {
                        "max_length": 1000,
                        "blocked_commands": [
                            "rm -rf", "dd if=", "mkfs", "format",
                            ":(){ :|:& };:",  # fork bomb
                            "chmod 777", "wget", "curl",
                        ]
                    }
                }
            ),
            "send_email": ToolPolicy(
                name="send_email",
                risk=ToolRisk.MEDIUM,
                allowed_roles=[Role.POWER_USER, Role.ADMIN],
                require_confirmation=True,
                parameter_rules={
                    "to": {"max_length": 254},
                    "subject": {"max_length": 200},
                    "body": {"max_length": 50000}
                }
            ),
            "delete_file": ToolPolicy(
                name="delete_file",
                risk=ToolRisk.HIGH,
                allowed_roles=[Role.ADMIN],
                require_confirmation=True,
                require_audit=True,
            ),
            "query_database": ToolPolicy(
                name="query_database",
                risk=ToolRisk.LOW,
                allowed_roles=[Role.POWER_USER, Role.ADMIN],
                parameter_rules={
                    "sql": {
                        "max_length": 4000,
                        "allow_only_read": True,  # 只允许 SELECT
                        "blocked_keywords": [
                            "DROP", "DELETE", "UPDATE", "INSERT",
                            "ALTER", "CREATE", "TRUNCATE", "EXEC"
                        ]
                    }
                }
            ),
            "transfer_money": ToolPolicy(
                name="transfer_money",
                risk=ToolRisk.CRITICAL,
                allowed_roles=[Role.ADMIN],
                require_confirmation=True,
                require_audit=True,
                parameter_rules={
                    "amount": {"max_value": 100000, "min_value": 0.01}
                }
            ),
        }
        
        # 全局阻止列表
        self.global_blocked_tools = {
            "format_disk", "rm_rf", "shutdown_system",
            "drop_database", "sudo", "reboot",
        }
    
    def check_access(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        user_role: Role
    ) -> AccessCheckResult:
        """检查工具调用权限
        
        Args:
            tool_name: 工具名称
            arguments: 工具参数
            user_role: 用户角色
            
        Returns:
            AccessCheckResult: 权限检查结果
        """
        # 0. 全局阻止列表
        if tool_name in self.global_blocked_tools:
            return AccessCheckResult(
                allowed=False,
                reason=f"工具 '{tool_name}' 已被全局禁用",
                require_human_approval=False
            )
        
        # 1. 工具是否在策略中
        if tool_name not in self.tool_policies:
            return AccessCheckResult(
                allowed=False,
                reason=f"工具 '{tool_name}' 不在允许列表中",
                require_human_approval=False
            )
        
        policy = self.tool_policies[tool_name]
        
        # 2. 角色权限检查
        if user_role not in policy.allowed_roles:
            return AccessCheckResult(
                allowed=False,
                reason=f"角色 '{user_role.value}' 无权使用工具 '{tool_name}'。需要: {[r.value for r in policy.allowed_roles]}",
                require_human_approval=False
            )
        
        # 3. 参数校验
        param_errors = self._validate_parameters(tool_name, arguments, policy.parameter_rules)
        if param_errors:
            return AccessCheckResult(
                allowed=False,
                reason=f"参数校验失败: {param_errors}",
                require_human_approval=False
            )
        
        # 4. 是否需要确认
        result = AccessCheckResult(
            allowed=True,
            reason="通过",
            require_human_approval=policy.require_confirmation,
            require_audit=policy.require_audit,
            risk_level=policy.risk.value,
        )
        return result
    
    def _validate_parameters(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        rules: Dict[str, Any]
    ) -> List[str]:
        """参数校验
        
        Args:
            tool_name: 工具名称
            arguments: 工具参数
            rules: 参数规则
            
        Returns:
            错误信息列表
        """
        errors = []
        
        for param_name, param_rules in rules.items():
            if param_name not in arguments:
                if param_rules.get("required", True):
                    errors.append(f"缺少必需参数 '{param_name}'")
                continue
            
            value = arguments[param_name]
            
            # 字符串参数
            if isinstance(value, str):
                max_len = param_rules.get("max_length")
                if max_len and len(value) > max_len:
                    errors.append(f"'{param_name}' 长度 {len(value)} 超过限制 {max_len}")
                
                blocked_prefixes = param_rules.get("blocked_prefixes", [])
                for prefix in blocked_prefixes:
                    if value.startswith(prefix):
                        errors.append(f"'{param_name}' 路径被阻止: {prefix}...")
                
                blocked_patterns = param_rules.get("blocked_patterns", [])
                for pattern in blocked_patterns:
                    if re.search(pattern, value):
                        errors.append(f"'{param_name}' 包含禁止模式: {pattern}")
                
                allowed_schemes = param_rules.get("allowed_schemes", [])
                if allowed_schemes and "://" in value:
                    scheme = value.split("://")[0]
                    if scheme not in allowed_schemes:
                        errors.append(f"'{param_name}' 不支持的 Scheme: {scheme}")
                
                blocked_domains = param_rules.get("blocked_domains", [])
                for domain in blocked_domains:
                    if domain in value:
                        errors.append(f"'{param_name}' 目标域名被阻止: {domain}")
                
                blocked_keywords = param_rules.get("blocked_keywords", [])
                value_upper = value.upper()
                for kw in blocked_keywords:
                    if kw.upper() in value_upper:
                        errors.append(f"'{param_name}' 包含禁止关键词: {kw}")
                
                allow_only_read = param_rules.get("allow_only_read", False)
                if allow_only_read:
                    first_word = value_upper.strip().split()[0] if value.strip() else ""
                    if first_word not in ("SELECT", "SHOW", "DESCRIBE", "EXPLAIN", "WITH"):
                        errors.append(f"'{param_name}' 只允许读操作(SELECT)，但收到: {first_word}")
                
                blocked_commands = param_rules.get("blocked_commands", [])
                for cmd in blocked_commands:
                    if cmd in value:
                        errors.append(f"'{param_name}' 包含禁止命令: {cmd}")
            
            # 数值参数
            if isinstance(value, (int, float)):
                max_val = param_rules.get("max_value")
                min_val = param_rules.get("min_value")
                if max_val is not None and value > max_val:
                    errors.append(f"'{param_name}' 值 {value} 超过上限 {max_val}")
                if min_val is not None and value < min_val:
                    errors.append(f"'{param_name}' 值 {value} 低于下限 {min_val}")
        
        return errors
    
    def add_tool_policy(self, policy: ToolPolicy):
        """添加工具策略
        
        Args:
            policy: 工具策略
        """
        self.tool_policies[policy.name] = policy
        logger.info(f"已添加工具策略: {policy.name}")
    
    def remove_tool_policy(self, tool_name: str):
        """移除工具策略
        
        Args:
            tool_name: 工具名称
        """
        if tool_name in self.tool_policies:
            del self.tool_policies[tool_name]
            logger.info(f"已移除工具策略: {tool_name}")
    
    def get_tool_policy(self, tool_name: str) -> Optional[ToolPolicy]:
        """获取工具策略
        
        Args:
            tool_name: 工具名称
            
        Returns:
            工具策略，如果不存在则返回 None
        """
        return self.tool_policies.get(tool_name)
    
    def list_tools_by_role(self, role: Role) -> List[str]:
        """列出角色允许的工具
        
        Args:
            role: 用户角色
            
        Returns:
            工具名称列表
        """
        return [name for name, policy in self.tool_policies.items() if role in policy.allowed_roles]


# ===========================================================
# 安全 Agent 包装器
# ===========================================================
class SecureAgentWrapper:
    """安全 Agent 包装器 —— 将安全检查嵌入每次调用
    
    功能：
    - 输入安全检查
    - 工具权限检查
    - 输出安全检查
    - 审计日志记录
    """
    
    def __init__(self, agent, input_filter, output_filter, access_control):
        """初始化安全 Agent 包装器
        
        Args:
            agent: Agent 实例
            input_filter: 输入过滤器
            output_filter: 输出过滤器
            access_control: 工具访问控制
        """
        self.agent = agent
        self.input_filter = input_filter
        self.output_filter = output_filter
        self.access_control = access_control
        self.audit_log = []
    
    def chat(self, user_input: str, user_id: str, user_role: Role) -> Dict:
        """安全包装的 chat 方法
        
        Args:
            user_input: 用户输入
            user_id: 用户 ID
            user_role: 用户角色
            
        Returns:
            包含响应和状态的字典
        """
        # Step 1: 输入安全检查
        check = self.input_filter.check(user_input, user_id)
        if check.blocked:
            self._log("input_blocked", user_id, check)
            return {
                "success": False,
                "error": check.reason,
                "risk_score": check.risk_score
            }
        
        # Step 2: 使用脱敏后的输入
        sanitized = check.sanitized_input
        
        # Step 3: 调用 Agent（带工具权限检查）
        response = self.agent.chat(
            sanitized,
            tool_access_checker=lambda tool, args: self.access_control.check_access(tool, args, user_role)
        )
        
        # Step 4: 输出安全检查
        output_check = self.output_filter.check(response)
        if not output_check.safe:
            self._log("output_issue", user_id, output_check)
            return {
                "success": False if output_check.moderation_flagged else True,
                "response": output_check.sanitized_output,
                "warnings": [i["detail"] for i in output_check.issues]
            }
        
        # Step 5: 审计日志
        self._log("success", user_id, {"risk_score": check.risk_score})
        return {
            "success": True,
            "response": output_check.sanitized_output
        }
    
    def _log(self, event: str, user_id: str, details: Any):
        """记录审计日志
        
        Args:
            event: 事件类型
            user_id: 用户 ID
            details: 详细信息
        """
        import time
        self.audit_log.append({
            "timestamp": int(time.time()),
            "event": event,
            "user_id": user_id,
            "details": str(details)[:500]
        })
        logger.info(f"审计日志: {event}, 用户: {user_id}")


# ===========================================================
# 使用示例
# ===========================================================
if __name__ == "__main__":
    # 初始化工具访问控制
    access_control = ToolAccessControl()
    
    # 检查权限
    result = access_control.check_access(
        tool_name="search_web",
        arguments={"query": "Python 教程"},
        user_role=Role.USER
    )
    print(f"权限检查: allowed={result.allowed}, reason={result.reason}")
    
    # 列出角色允许的工具
    tools = access_control.list_tools_by_role(Role.USER)
    print(f"USER 角色允许的工具: {tools}")
    
    print("RBAC 示例运行完成")
