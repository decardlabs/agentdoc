"""
LLM 客户端模块

本模块负责：
1. 封装 OpenAI API 调用
2. 支持流式输出
3. 错误处理和重试机制
4. Token 计数和成本控制

作者：智能体工程师培养计划
日期：2024
"""

import os
from openai import OpenAI, RateLimitError, APIError, APITimeoutError
from typing import List, Dict, Optional, Generator
import time
import logging
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LLMClient:
    """
    LLM 客户端类
    
    封装 OpenAI API 的调用，提供流式输出、错误处理等功能
    """
    
    def __init__(
        self,
        model: str = "gpt-4o-mini",
        temperature: float = 0.7,
        max_tokens: int = 2000
    ):
        """
        初始化 LLM 客户端
        
        Args:
            model: 模型名称，默认 gpt-4o-mini
            temperature: 温度参数，默认 0.7
            max_tokens: 最大输出 Token 数，默认 2000
        """
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        # 获取 API Key
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("未找到 OPENAI_API_KEY 环境变量，请在 .env 文件中配置")
        
        # 初始化 OpenAI 客户端
        self.client = OpenAI(api_key=api_key)
        
        logger.info(f"LLMClient 初始化完成: model={model}, temperature={temperature}")
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        stream: bool = True
    ) -> Generator[str, None, None]:
        """
        聊天接口（支持流式输出）
        
        Args:
            messages: 消息列表，格式 [{"role": "user", "content": "..."}]
            stream: 是否流式输出，默认 True
            
        Yields:
            生成的文本片段（流式）或完整文本（非流式）
            
        Raises:
            Exception: API 调用失败
        """
        try:
            logger.info(f"开始调用 LLM: model={self.model}, messages={len(messages)} 条")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                stream=stream
            )
            
            if stream:
                # 流式输出
                for chunk in response:
                    if chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
            else:
                # 非流式输出
                yield response.choices[0].message.content
                
        except RateLimitError:
            logger.error("API 限流，请稍后重试")
            raise Exception("API 限流，请稍后重试")
        except APITimeoutError:
            logger.error("API 超时，请检查网络连接")
            raise Exception("API 超时，请检查网络连接")
        except APIError as e:
            logger.error(f"API 错误: {str(e)}")
            raise Exception(f"API 调用失败: {str(e)}")
        except Exception as e:
            logger.error(f"未知错误: {str(e)}")
            raise
    
    def chat_with_retry(
        self,
        messages: List[Dict[str, str]],
        stream: bool = True,
        max_retries: int = 3
    ) -> Generator[str, None, None]:
        """
        带重试的聊天接口
        
        Args:
            messages: 消息列表
            stream: 是否流式输出
            max_retries: 最大重试次数
            
        Yields:
            生成的文本片段
        """
        for attempt in range(max_retries):
            try:
                yield from self.chat(messages, stream)
                return  # 成功则返回
            except Exception as e:
                if attempt == max_retries - 1:
                    # 最后一次重试失败
                    raise
                
                # 指数退避
                wait_time = 2 ** attempt
                logger.warning(f"第 {attempt + 1} 次重试，等待 {wait_time} 秒: {str(e)}")
                time.sleep(wait_time)
    
    def count_tokens(self, messages: List[Dict[str, str]]) -> int:
        """
        计算消息列表的 Token 数量
        
        Args:
            messages: 消息列表
            
        Returns:
            Token 数量
        """
        try:
            import tiktoken
            
            # 将 messages 转换为文本
            text = ""
            for msg in messages:
                text += f"{msg['role']}: {msg['content']}\n"
            
            encoding = tiktoken.encoding_for_model(self.model)
            return len(encoding.encode(text))
        except Exception as e:
            logger.warning(f"Token 计算失败: {str(e)}")
            return 0
    
    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        估算成本（美元）
        
        Args:
            input_tokens: 输入 Token 数
            output_tokens: 输出 Token 数
            
        Returns:
            估算成本（美元）
        """
        # gpt-4o-mini 价格：$0.15/M 输入, $0.6/M 输出
        price_per_1k_input = 0.00015
        price_per_1k_output = 0.0006
        
        cost = (input_tokens / 1000) * price_per_1k_input + \
               (output_tokens / 1000) * price_per_1k_output
        
        return cost


if __name__ == "__main__":
    # 测试代码
    try:
        client = LLMClient()
        
        # 测试非流式调用
        messages = [{"role": "user", "content": "你好，请介绍一下自己"}]
        print("测试非流式调用:")
        response = "".join(client.chat(messages, stream=False))
        print(response)
        
        # 测试流式调用
        print("\n测试流式调用:")
        messages = [{"role": "user", "content": "用一句话介绍 Python"}]
        for chunk in client.chat(messages, stream=True):
            print(chunk, end="", flush=True)
        
        print("\n\nLLMClient 模块测试完成！")
        
    except Exception as e:
        print(f"测试失败: {str(e)}")
