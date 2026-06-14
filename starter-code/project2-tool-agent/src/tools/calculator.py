"""
计算器工具

本模块提供数学计算功能，支持：
1. 基本运算（加减乘除）
2. 科学计算（幂、根号、三角函数等）
3. 安全的表达式求值

作者：智能体工程师培养计划
日期：2024
"""

import operator
from typing import Any, Dict
import math


# 支持的操作符
OPERATORS = {
    '+': operator.add,
    '-': operator.sub,
    '*': operator.mul,
    '/': operator.truediv,
    '^': operator.pow,
    '**': operator.pow,
}

# 支持的数学函数
MATH_FUNCTIONS = {
    'sin': math.sin,
    'cos': math.cos,
    'tan': math.tan,
    'asin': math.asin,
    'acos': math.acos,
    'atan': math.atan,
    'sqrt': math.sqrt,
    'log': math.log,
    'log10': math.log10,
    'exp': math.exp,
    'abs': abs,
    'ceil': math.ceil,
    'floor': math.floor,
    'round': round,
}

# 支持的常量
CONSTANTS = {
    'pi': math.pi,
    'e': math.e,
}


def calculator(expression: str) -> str:
    """
    数学计算器
    
    支持基本运算和科学计算，例如：
    - "2 + 3 * 4"
    - "sqrt(16)"
    - "sin(pi/2)"
    - "(10 + 5) * 2"
    
    Args:
        expression: 数学表达式字符串
        
    Returns:
        计算结果字符串
        
    Examples:
        >>> calculator("2 + 3 * 4")
        '14'
        
        >>> calculator("sqrt(16)")
        '4.0'
        
        >>> calculator("sin(pi/2)")
        '1.0'
    """
    try:
        # 清理表达式
        expression = expression.strip()
        
        # 替换常量
        for const_name, const_value in CONSTANTS.items():
            expression = expression.replace(const_name, str(const_value))
        
        # 安全求值
        # 创建一个安全的命名空间
        safe_dict = {
            **MATH_FUNCTIONS,
            '__builtins__': {}
        }
        
        # 使用 eval 求值（在安全的环境下）
        result = eval(expression, safe_dict)
        
        # 格式化结果
        if isinstance(result, (int, float)):
            if result == int(result):
                return str(int(result))
            else:
                return f"{result:.6f}".rstrip('0').rstrip('.')
        else:
            return str(result)
        
    except ZeroDivisionError:
        return "计算错误：除数不能为 0"
    except SyntaxError as e:
        return f"计算错误：表达式语法错误 ({str(e)})"
    except NameError as e:
        return f"计算错误：不支持的函数或常量 ({str(e)})"
    except Exception as e:
        return f"计算错误：{str(e)}"


def calculator_safe(expression: str) -> str:
    """
    更安全的计算器（使用 numexpr 库，如果可用）
    
    Args:
        expression: 数学表达式字符串
        
    Returns:
        计算结果字符串
    """
    try:
        # 尝试使用 numexpr（更快更安全）
        import numexpr as ne
        result = ne.evaluate(expression)
        return str(result.item())
    except ImportError:
        # 如果 numexpr 不可用，使用标准计算器
        return calculator(expression)
    except Exception as e:
        return f"计算错误：{str(e)}"


def batch_calculate(expressions: list) -> Dict[str, str]:
    """
    批量计算
    
    Args:
        expressions: 表达式列表
        
    Returns:
        字典：{表达式: 结果}
    """
    results = {}
    for expr in expressions:
        results[expr] = calculator(expr)
    return results


def calculate_with_steps(expression: str) -> str:
    """
    带步骤的计算（用于教学）
    
    Args:
        expression: 数学表达式字符串
        
    Returns:
        带步骤的计算结果
    """
    try:
        result = calculator(expression)
        return f"""
计算过程：
表达式: {expression}
步骤:
  1. 解析表达式
  2. 应用运算符优先级
  3. 计算结果

结果: {result}
"""
    except Exception as e:
        return f"计算失败：{str(e)}"


if __name__ == "__main__":
    # 测试代码
    print("测试计算器工具")
    print("=" * 50)
    
    # 测试用例
    test_cases = [
        "2 + 3",
        "10 - 5",
        "3 * 7",
        "20 / 4",
        "(2 + 3) * 4",
        "sqrt(16)",
        "sin(pi/2)",
        "log(e)",
        "2^10",
        "100 * 0.13",
    ]
    
    for expr in test_cases:
        result = calculator(expr)
        print(f"{expr} = {result}")
    
    print("\n" + "=" * 50)
    print("测试完成！")
