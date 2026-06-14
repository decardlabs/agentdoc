"""
工具测试模块

本模块测试所有工具的功能：
1. 天气查询工具
2. 计算器工具
3. 日历工具

作者：智能体工程师培养计划
日期：2024
"""

import unittest
import sys
import os

# 添加 src 到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from tools.weather import get_weather, get_weather_simple
from tools.calculator import calculator, batch_calculate
from tools.calendar import get_today, add_event, list_events, get_current_time, _calendar_events


class TestWeatherTool(unittest.TestCase):
    """
    测试天气查询工具
    """
    
    def test_get_weather_valid_city(self):
        """
        测试查询有效城市的天气
        """
        # 注意：这个测试需要网络连接
        result = get_weather("深圳")
        
        # 断言：返回结果应该包含城市名
        self.assertIn("深圳", result)
        print(f"\n✅ 天气查询测试通过: {result[:50]}...")
    
    def test_get_weather_invalid_city(self):
        """
        测试查询无效城市的天气
        """
        result = get_weather("不存在的城市XXX")
        
        # 断言：应该返回错误信息
        self.assertIn("失败", result)
        print(f"\n✅ 无效城市天气查询测试通过")
    
    def test_get_weather_simple(self):
        """
        测试简化版天气查询
        """
        result = get_weather_simple("北京")
        
        # 断言：应该返回非空结果
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)
        print(f"\n✅ 简化版天气查询测试通过: {result}")


class TestCalculatorTool(unittest.TestCase):
    """
    测试计算器工具
    """
    
    def test_basic_calculation(self):
        """
        测试基本运算
        """
        test_cases = [
            ("2 + 3", "5"),
            ("10 - 5", "5"),
            ("3 * 7", "21"),
            ("20 / 4", "5"),
        ]
        
        for expr, expected in test_cases:
            result = calculator(expr)
            self.assertEqual(result, expected)
        
        print(f"\n✅ 基本运算测试通过")
    
    def test_parentheses(self):
        """
        测试括号运算
        """
        result = calculator("(2 + 3) * 4")
        self.assertEqual(result, "20")
        print(f"\n✅ 括号运算测试通过")
    
    def test_math_functions(self):
        """
        测试数学函数
        """
        test_cases = [
            ("sqrt(16)", "4"),
            ("sin(pi/2)", "1"),
        ]
        
        for expr, expected in test_cases:
            result = calculator(expr)
            self.assertTrue(abs(float(result) - float(expected)) < 0.0001)
        
        print(f"\n✅ 数学函数测试通过")
    
    def test_division_by_zero(self):
        """
        测试除零错误
        """
        result = calculator("1 / 0")
        self.assertIn("错误", result)
        print(f"\n✅ 除零错误测试通过")
    
    def test_invalid_expression(self):
        """
        测试无效表达式
        """
        result = calculator("2 + + 3")
        self.assertIn("错误", result)
        print(f"\n✅ 无效表达式测试通过")
    
    def test_batch_calculate(self):
        """
        测试批量计算
        """
        expressions = ["2 + 3", "10 - 5", "3 * 7"]
        results = batch_calculate(expressions)
        
        self.assertEqual(len(results), 3)
        self.assertEqual(results["2 + 3"], "5")
        print(f"\n✅ 批量计算测试通过")


class TestCalendarTool(unittest.TestCase):
    """
    测试日历工具
    """
    
    def setUp(self):
        """
        测试前准备：清除模拟数据库
        """
        global _calendar_events
        _calendar_events.clear()
    
    def test_get_today(self):
        """
        测试获取今天日期
        """
        result = get_today()
        
        # 断言：应该包含"今天"
        self.assertIn("今天", result)
        print(f"\n✅ 获取今天日期测试通过")
    
    def test_get_current_time(self):
        """
        测试获取当前时间
        """
        result = get_current_time()
        
        # 断言：应该包含":"
        self.assertIn(":", result)
        print(f"\n✅ 获取当前时间测试通过: {result}")
    
    def test_add_event(self):
        """
        测试添加日程
        """
        result = add_event("团队会议", "明天", "14:00", "讨论项目进展")
        
        # 断言：应该包含"已添加"
        self.assertIn("已添加", result)
        print(f"\n✅ 添加日程测试通过")
    
    def test_list_events(self):
        """
        测试查询日程
        """
        # 先添加几个日程
        add_event("会议1", "明天", "10:00")
        add_event("会议2", "后天", "14:00")
        
        # 查询
        result = list_events()
        
        # 断言：应该包含"日程"
        self.assertIn("日程", result)
        print(f"\n✅ 查询日程测试通过")
    
    def test_add_and_list_events(self):
        """
        测试添加后查询
        """
        # 添加日程
        add_event("测试会议", "明天", "10:00")
        
        # 查询
        result = list_events()
        
        # 断言：应该包含"测试会议"
        self.assertIn("测试会议", result)
        print(f"\n✅ 添加后查询测试通过")


class TestToolsIntegration(unittest.TestCase):
    """
    集成测试：测试工具之间的协作
    """
    
    def test_calculator_with_complex_expression(self):
        """
        测试复杂表达式
        """
        expressions = [
            "100 * 0.13",  # 计算税费
            "sqrt(2) * sqrt(2)",  # 应该等于 2
            "(10 + 20) * 30",  # 复杂运算
        ]
        
        for expr in expressions:
            result = calculator(expr)
            self.assertIsInstance(result, str)
            self.assertGreater(len(result), 0)
        
        print(f"\n✅ 复杂表达式测试通过")


def run_tests():
    """
    运行所有测试
    """
    print("=" * 50)
    print("开始运行工具测试")
    print("=" * 50)
    
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试用例
    suite.addTests(loader.loadTestsFromTestCase(TestWeatherTool))
    suite.addTests(loader.loadTestsFromTestCase(TestCalculatorTool))
    suite.addTests(loader.loadTestsFromTestCase(TestCalendarTool))
    suite.addTests(loader.loadTestsFromTestCase(TestToolsIntegration))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 输出总结
    print("\n" + "=" * 50)
    print("测试总结")
    print("=" * 50)
    print(f"运行测试: {result.testsRun}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")
    
    if result.failures:
        print("\n失败详情:")
        for test, failure in result.failures:
            print(f"  - {test}: {failure}")
    
    if result.errors:
        print("\n错误详情:")
        for test, error in result.errors:
            print(f"  - {test}: {error}")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    # 运行测试
    success = run_tests()
    
    # 退出码
    sys.exit(0 if success else 1)
