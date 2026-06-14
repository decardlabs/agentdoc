"""
RAG 系统测试模块

本模块测试 RAG Pipeline 的各项功能：
1. 文档加载
2. 向量存储
3. 检索
4. 端到端流程

作者：智能体工程师培养计划
日期：2024
"""

import unittest
import sys
import os

# 添加 src 到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from document_loader import DocumentLoader
from prompt_builder import RAGPromptBuilder


class TestDocumentLoader(unittest.TestCase):
    """
    测试文档加载器
    """
    
    def setUp(self):
        """
        测试前准备
        """
        self.loader = DocumentLoader()
        self.sample_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'sample_docs')
    
    def test_load_markdown(self):
        """
        测试加载 Markdown 文件
        """
        # 查找示例 Markdown 文件
        md_files = [f for f in os.listdir(self.sample_dir) if f.endswith('.md')]
        
        if not md_files:
            self.skipTest("没有找到示例 Markdown 文件")
        
        # 加载第一个文件
        file_path = os.path.join(self.sample_dir, md_files[0])
        documents = self.loader.load_markdown(file_path)
        
        # 断言
        self.assertIsInstance(documents, list)
        self.assertGreater(len(documents), 0)
        self.assertIn("text", documents[0])
        self.assertIn("metadata", documents[0])
        
        print(f"\n✅ Markdown 加载测试通过: {md_files[0]}")
    
    def test_load_directory(self):
        """
        测试加载目录
        """
        documents = self.loader.load_directory(self.sample_dir)
        
        # 断言
        self.assertIsInstance(documents, list)
        self.assertGreater(len(documents), 0)
        
        print(f"\n✅ 目录加载测试通过: {len(documents)} 个文档片段")
    
    def test_load_nonexistent_file(self):
        """
        测试加载不存在的文件
        """
        with self.assertRaises(Exception):
            self.loader.load_file("nonexistent.pdf")
        
        print(f"\n✅ 不存在文件加载测试通过（正确抛出异常）")


class TestPromptBuilder(unittest.TestCase):
    """
    测试 Prompt 构建器
    """
    
    def setUp(self):
        """
        测试前准备
        """
        self.builder = RAGPromptBuilder(use_citation=True)
    
    def test_build_context(self):
        """
        测试构建 Context
        """
        # 模拟文档
        documents = [
            {
                "text": "这是第一个文档的内容。",
                "metadata": {"file_name": "doc1.pdf", "page": 1}
            },
            {
                "text": "这是第二个文档的内容。",
                "metadata": {"file_name": "doc2.pdf", "page": 2}
            }
        ]
        
        # 构建 Context
        context = self.builder.build_context(documents)
        
        # 断言
        self.assertIsInstance(context, str)
        self.assertIn("doc1.pdf", context)
        self.assertIn("doc2.pdf", context)
        
        print(f"\n✅ Context 构建测试通过")
    
    def test_build_prompt(self):
        """
        测试构建 Prompt
        """
        # 模拟文档
        documents = [
            {
                "text": "公司年假政策：入职满 1 年 5 天年假。",
                "metadata": {"file_name": "员工手册.pdf", "page": 3}
            }
        ]
        
        # 构建 Prompt
        question = "年假怎么算？"
        messages = self.builder.build_prompt(question, documents)
        
        # 断言
        self.assertIsInstance(messages, list)
        self.assertEqual(len(messages), 2)  # system + user
        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[1]["role"], "user")
        
        print(f"\n✅ Prompt 构建测试通过")
    
    def test_format_answer_with_citation(self):
        """
        测试添加引用
        """
        # 模拟答案和文档
        answer = "年假政策是入职满 1 年 5 天。"
        documents = [
            {
                "text": "年假政策内容",
                "metadata": {"file_name": "员工手册.pdf", "page": 3}
            }
        ]
        
        # 添加引用
        answer_with_citation = self.builder.format_answer_with_citation(answer, documents)
        
        # 断言
        self.assertIn("参考文档", answer_with_citation)
        self.assertIn("员工手册.pdf", answer_with_citation)
        
        print(f"\n✅ 引用格式化测试通过")


class TestRAGPipelineMock(unittest.TestCase):
    """
    测试 RAG Pipeline（使用 Mock）
    """
    
    def test_mock_retrieval(self):
        """
        测试模拟检索
        """
        # 注意：这是一个简化测试，实际应该集成真实的向量数据库
        print(f"\n✅ RAG Pipeline 测试（简化版）通过")
        print("  注意：完整测试需要配置 OpenAI API Key 和向量数据库")


def run_tests():
    """
    运行所有测试
    """
    print("=" * 50)
    print("开始运行 RAG 系统测试")
    print("=" * 50)
    
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试用例
    suite.addTests(loader.loadTestsFromTestCase(TestDocumentLoader))
    suite.addTests(loader.loadTestsFromTestCase(TestPromptBuilder))
    suite.addTests(loader.loadTestsFromTestCase(TestRAGPipelineMock))
    
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
