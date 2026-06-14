"""
PDF 加载器测试用例

本模块测试 PDFLoader 的各项功能：
1. 文本切分功能
2. Token 计数功能
3. 边界情况处理

注意：测试 PDF 加载需要实际的 PDF 文件，这里主要测试文本切分功能

作者：智能体工程师培养计划
日期：2024
"""

import unittest
import sys
import os

# 添加 src 到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from pdf_loader import PDFLoader, count_tokens


class TestPDFLoader(unittest.TestCase):
    """
    测试 PDFLoader 类
    """
    
    def setUp(self):
        """
        测试前准备
        """
        self.loader = PDFLoader(chunk_size=1000, chunk_overlap=200)
    
    def test_split_text_basic(self):
        """
        测试基本的文本切分功能
        """
        # 准备长文本
        long_text = "这是一个测试文本。" * 500  # 约 5000 字符
        
        # 切分
        chunks = self.loader.split_text(long_text)
        
        # 断言
        self.assertIsInstance(chunks, list)
        self.assertGreater(len(chunks), 1)  # 应该切分成多个 Chunks
        self.assertLessEqual(len(chunks[0]), self.loader.chunk_size)  # Chunk 大小不超过限制
        
        print(f"\n✅ 文本切分测试通过: {len(chunks)} 个 Chunks")
    
    def test_split_text_empty(self):
        """
        测试空文本切分
        """
        chunks = self.loader.split_text("")
        self.assertEqual(len(chunks), 0)
        print("\n✅ 空文本切分测试通过")
    
    def test_split_text_short(self):
        """
        测试短文本切分（不需要切分）
        """
        short_text = "短文本"
        chunks = self.loader.split_text(short_text)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0], short_text)
        print("\n✅ 短文本切分测试通过")
    
    def test_chunk_overlap(self):
        """
        测试 Chunk 重叠功能
        """
        # 准备长文本
        long_text = "测试文本" * 1000
        
        # 切分
        chunks = self.loader.split_text(long_text)
        
        # 检查重叠（简化检查：相邻 Chunks 应该有部分内容重复）
        if len(chunks) > 1:
            # 检查第一个 Chunk 的末尾是否在第二个 Chunk 的开头出现
            chunk1_end = chunks[0][-200:]  # 最后 200 字符
            chunk2_start = chunks[1][:200]  # 前 200 字符
            
            # 应该有重叠（至少 50 字符）
            overlap = False
            for i in range(50, len(chunk1_end)):
                if chunk1_end[-i:] in chunk2_start:
                    overlap = True
                    break
            
            self.assertTrue(overlap, "Chunk 之间应该有重叠")
            print(f"\n✅ Chunk 重叠测试通过")
    
    def test_count_tokens(self):
        """
        测试 Token 计数功能
        """
        text = "这是一个测试文本，用于测试 Token 计数功能。"
        tokens = count_tokens(text)
        
        self.assertIsInstance(tokens, int)
        self.assertGreater(tokens, 0)
        print(f"\n✅ Token 计数测试通过: {tokens} tokens")
    
    def test_count_tokens_empty(self):
        """
        测试空文本的 Token 计数
        """
        tokens = count_tokens("")
        self.assertEqual(tokens, 0)
        print("\n✅ 空文本 Token 计数测试通过")
    
    def test_load_multiple_pdfs_empty_list(self):
        """
        测试空文件列表
        """
        results = self.loader.load_multiple_pdfs([])
        self.assertEqual(len(results), 0)
        print("\n✅ 空文件列表测试通过")


class TestPDFLoaderEdgeCases(unittest.TestCase):
    """
    测试边界情况
    """
    
    def test_large_chunk_size(self):
        """
        测试大 Chunk Size
        """
        loader = PDFLoader(chunk_size=10000, chunk_overlap=200)
        text = "测试" * 100
        chunks = loader.split_text(text)
        
        self.assertEqual(len(chunks), 1)  # 不需要切分
        print("\n✅ 大 Chunk Size 测试通过")
    
    def test_small_chunk_size(self):
        """
        测试小 Chunk Size
        """
        loader = PDFLoader(chunk_size=10, chunk_overlap=2)
        text = "这是一个测试文本，用于测试小 Chunk Size 的情况。"
        chunks = loader.split_text(text)
        
        self.assertGreater(len(chunks), 1)  # 应该切分成多个 Chunks
        print(f"\n✅ 小 Chunk Size 测试通过: {len(chunks)} 个 Chunks")
    
    def test_zero_overlap(self):
        """
        测试零重叠
        """
        loader = PDFLoader(chunk_size=100, chunk_overlap=0)
        text = "测试文本" * 100
        chunks = loader.split_text(text)
        
        self.assertGreater(len(chunks), 1)
        print(f"\n✅ 零重叠测试通过: {len(chunks)} 个 Chunks")


def run_tests():
    """
    运行所有测试
    """
    print("=" * 50)
    print("开始运行 PDFLoader 测试")
    print("=" * 50)
    
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试用例
    suite.addTests(loader.loadTestsFromTestCase(TestPDFLoader))
    suite.addTests(loader.loadTestsFromTestCase(TestPDFLoaderEdgeCases))
    
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
