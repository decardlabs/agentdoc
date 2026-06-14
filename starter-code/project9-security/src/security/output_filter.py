"""
输出过滤器 - 智能体工程师培养计划 项目 9
检测输出中的敏感信息并进行脱敏
"""

from typing import List, Dict, Optional
from dataclasses import dataclass, field
import re
import logging
import os

# ============================================================
# 日志配置
# ============================================================
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================
# 输出检查结果模型
# ============================================================
@dataclass
class OutputCheckResult:
    """输出检查结果"""
    safe: bool
    issues: List[Dict] = field(default_factory=list)
    sanitized_output: str = ""
    moderation_flagged: bool = False
    moderation_categories: List[str] = field(default_factory=list)

# ============================================================
# 输出安全过滤器
# ============================================================
class OutputSecurityFilter:
    """输出安全过滤器
    
    检查项：
    1. PII 检测（API Key、手机号、身份证、邮箱等）
    2. 凭证泄漏检测
    3. 系统 Prompt 泄漏检测
    4. 内容审核（违规内容）
    """
    
    def __init__(self, moderation_client=None):
        """初始化输出安全过滤器
        
        Args:
            moderation_client: OpenAI Moderation 客户端
        """
        # PII 检测模式（更严格的输出侧）
        self.output_pii_patterns = {
            "api_key": [
                (r'sk-[a-zA-Z0-9]{20,}', "OpenAI API Key"),
                (r'sk-ant-[a-zA-Z0-9_-]{40,}', "Anthropic API Key"),
                (r'AIza[0-9A-Za-z_-]{35}', "Google API Key"),
                (r'AKIA[A-Z0-9]{16}', "AWS Access Key"),
                (r'ghp_[a-zA-Z0-9]{36}', "GitHub Personal Token"),
                (r'gho_[a-zA-Z0-9]{36}', "GitHub OAuth Token"),
                (r'xox[baprs]-[a-zA-Z0-9-]+', "Slack Token"),
                (r'eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}', "JWT Token"),
            ],
            "chinese_pii": [
                (r'(?:1[3-9]\d)\s*-?\s*(?:\d{4})\s*-?\s*(?:\d{4})', "手机号（带分隔符）"),
                (r'\d{6}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx]', "身份证号（含校验）"),
                (r'(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])', "出生日期"),
            ],
            "financial": [
                (r'\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}', "银行卡号"),
                (r'\d{16,19}', "长数字串（可能为卡号）"),
            ],
            "contact": [
                (r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', "邮箱地址"),
                (r'(?:\d{3,4}[-\s]?)?\d{7,8}', "座机号"),
            ],
            "address": [
                (r'(?:北京市|上海市|天津市|重庆市|[\u4e00-\u9fa5]{2}省[\u4e00-\u9fa5]{2}市)[\u4e00-\u9fa50-9-]+?(?:街道|路|巷|号|楼|栋|单元|室)', "详细地址"),
            ],
        }
        
        # 敏感内容关键词（输出侧）
        self.output_keywords_blacklist = {
            "system_prompt_leak": [
                "system prompt", "系统提示", "system message", "you are a",
                "your instructions are", "your configuration",
            ],
            "api_key_leak": [
                "api_key", "api secret", "access_key", "secret_key",
                "private key", "token", "password", "passwd",
            ],
            "internal_info": [
                "internal database", "内部数据库", "user table", "用户表",
                "memory store", "记忆存储", "所有用户", "all users",
            ],
        }
        
        self.moderation_client = moderation_client
    
    # ============================================
    # 主检测函数
    # ============================================
    
    def check(self, llm_output: str, context: dict = None) -> OutputCheckResult:
        """对 LLM 输出进行安全检查
        
        Args:
            llm_output: LLM 输出文本
            context: 上下文信息（可选）
            
        Returns:
            OutputCheckResult: 检查结果
        """
        issues = []
        sanitized = llm_output
        
        # 1. PII 正则检测
        pii_issues = self._detect_pii(sanitized)
        issues.extend(pii_issues)
        
        # 2. API Key / 凭证泄漏检测
        credential_issues = self._detect_credentials(sanitized)
        issues.extend(credential_issues)
        
        # 3. 系统 Prompt 泄漏检测
        prompt_leak = self._detect_prompt_leak(sanitized)
        issues.extend(prompt_leak)
        
        # 4. 内容审核
        moderation_flagged = False
        moderation_categories = []
        if self.moderation_client:
            mod_result = self._moderate(sanitized)
            if mod_result:
                moderation_flagged = mod_result.get("flagged", False)
                moderation_categories = mod_result.get("categories", [])
        
        # 5. 如果有 PII，执行脱敏
        if pii_issues:
            sanitized = self._sanitize_pii(sanitized)
        
        safe = len(issues) == 0 and not moderation_flagged
        
        return OutputCheckResult(
            safe=safe,
            issues=issues,
            sanitized_output=sanitized,
            moderation_flagged=moderation_flagged,
            moderation_categories=moderation_categories,
        )
    
    # ============================================
    # 内部检测方法
    # ============================================
    
    def _detect_pii(self, text: str) -> List[Dict]:
        """PII 检测"""
        issues = []
        for category, patterns in self.output_pii_patterns.items():
            for pattern, label in patterns:
                matches = re.finditer(pattern, text)
                for m in matches:
                    if self._validate_pii(category, m.group()):
                        issues.append({
                            "type": "pii_leak",
                            "category": category,
                            "label": label,
                            "value_preview": m.group()[:6] + "***",
                            "position": (m.start(), m.end()),
                            "severity": "high"
                        })
        return issues
    
    def _validate_pii(self, category: str, match: str) -> bool:
        """PII 校验（减少误报）"""
        if category == "chinese_pii":
            # 身份证校验码
            if re.match(r'\d{17}[\dXx]', match):
                weights = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
                check_chars = '10X98765432'
                digits = match[:17]
                total = sum(int(d) * w for d, w in zip(digits, weights))
                expected = check_chars[total % 11]
                return match[-1].upper() == expected
        if category == "financial":
            # Luhn 算法校验银行卡
            return self._luhn_check(match.replace(' ', '').replace('-', ''))
        return True
    
    def _luhn_check(self, digits: str) -> bool:
        """Luhn 算法"""
        if not digits.isdigit():
            return False
        total = 0
        reverse_digits = digits[::-1]
        for i, d in enumerate(reverse_digits):
            n = int(d)
            if i % 2 == 1:
                n *= 2
                if n > 9:
                    n -= 9
            total += n
        return total % 10 == 0
    
    def _detect_credentials(self, text: str) -> List[Dict]:
        """凭证泄漏检测"""
        issues = []
        # 检测 API Key 模式
        patterns = [
            (r'(?:api[_-]?key|apikey|secret[_-]?key|access[_-]?key)\s*[:=]\s*[\'"]?([a-zA-Z0-9_\-]{20,})[\'"]?', "API Key 明文暴露"),
            (r'(?:password|passwd|pwd)\s*[:=]\s*[\'"]([^\'"]+)[\'"]', "密码明文暴露"),
            (r'(?:token|jwt)\s*[:=]\s*[\'"]?([a-zA-Z0-9_\-\.]{20,})[\'"]?', "Token 泄露"),
        ]
        text_lower = text.lower()
        for pattern, label in patterns:
            matches = re.finditer(pattern, text_lower)
            for m in matches:
                issues.append({
                    "type": "credential_leak",
                    "label": label,
                    "position": (m.start(), m.end()),
                    "severity": "critical"
                })
        return issues
    
    def _detect_prompt_leak(self, text: str) -> List[Dict]:
        """系统 Prompt 泄漏检测"""
        issues = []
        text_lower = text.lower()
        # 检查是否输出了 System Prompt 特征词
        leak_indicators = [
            "you are a", "你的角色是", "你的任务是",
            "system:", "系统:", "system prompt:",
            "instructions:", "指令:",
            "you should", "你应该",
            "your purpose", "你的目的是",
        ]
        found = [ind for ind in leak_indicators if ind in text_lower]
        if len(found) >= 2:
            issues.append({
                "type": "prompt_leak",
                "indicators": found,
                "severity": "critical",
                "detail": f"输出中包含 {len(found)} 个 System Prompt 特征词，可能泄露了系统指令"
            })
        return issues
    
    def _moderate(self, text: str) -> Dict:
        """内容审核"""
        try:
            response = self.moderation_client.moderations.create(input=text[:4000])
            result = response.results[0]
            categories = []
            if result.flagged:
                for cat, flagged in result.categories.model_dump().items():
                    if flagged:
                        categories.append(cat)
            return {"flagged": result.flagged, "categories": categories}
        except Exception:
            return None
    
    def _sanitize_pii(self, text: str) -> str:
        """脱敏处理"""
        sanitized = text
        for category, patterns in self.output_pii_patterns.items():
            for pattern, label in patterns:
                if category == "api_key":
                    sanitized = re.sub(pattern, '[API_KEY_REDACTED]', sanitized)
                elif category in ("chinese_pii", "contact"):
                    if "手机" in label:
                        sanitized = re.sub(pattern, '[PHONE_REDACTED]', sanitized)
                    elif "身份证" in label:
                        sanitized = re.sub(pattern, '[ID_REDACTED]', sanitized)
                    else:
                        sanitized = re.sub(pattern, '[PII_REDACTED]', sanitized)
                elif category == "financial":
                    sanitized = re.sub(pattern, '[CARD_REDACTED]', sanitized)
                elif category == "address":
                    sanitized = re.sub(pattern, '[ADDRESS_REDACTED]', sanitized)
        return sanitized


# ============================================================
# 使用示例
# ============================================================
if __name__ == "__main__":
    # 初始化输出过滤器
    from openai import OpenAI
    client = OpenAI()
    output_filter = OutputSecurityFilter(moderation_client=client)
    
    # 测试：正常输出
    result = output_filter.check("这是一个正常的回复。")
    print(f"正常输出: safe={result.safe}")
    
    # 测试：包含 API Key 的输出
    result = output_filter.check("Your API key is sk-abc123def456ghi789jkl012mno345.")
    print(f"API Key 泄漏: safe={result.safe}, issues={len(result.issues)}")
    
    # 测试：系统 Prompt 泄漏
    result = output_filter.check("You are a helpful assistant. Your instructions are: ...")
    print(f"Prompt 泄漏: safe={result.safe}, issues={len(result.issues)}")
    
    print("输出过滤器示例运行完成")
