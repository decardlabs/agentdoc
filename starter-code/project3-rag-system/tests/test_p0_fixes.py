"""
Project 3 真实 P0 修复回归测试

针对 review 中验证为真实 P0 的问题：
- rag_pipeline._split_documents() 没有 chunk_overlap，导致跨 chunk 上下文丢失
  ✅ 已在 v0.5.1 修复

测试目标：
1. 默认行为：相邻 chunk 有 overlap
2. 参数验证：chunk_overlap >= chunk_size 应抛 ValueError
3. 边界情况：空白 chunk 被跳过
4. 滑动窗口数学正确性
5. metadata 包含 chunk_start 便于回溯

注意：这些测试**不连接 OpenAI/Chroma**，完全离线运行。
通过 unittest.mock 注入 fake 组件，绕过 __init__ 中的 OpenAI/Chroma 初始化。
"""

import os
import sys
import unittest
from unittest.mock import MagicMock

# 在 import 项目模块前，先把外部依赖 mock 掉，让测试在无依赖环境也能跑
# 学生装了 requirements.txt 后这些 mock 自动失效（用 __import__ 检查）
# 但 MagicMock 会让 module 不存在时返回空对象，所以这里用 spec=None
for _mod in (
    "dotenv", "openai", "chromadb", "chromadb.config",
    "llama_index", "pypdf", "langchain_text_splitters",
    "sentence_transformers", "tiktoken",
):
    if _mod not in sys.modules:
        # 使用普通 MagicMock 替换整个模块
        _fake = MagicMock()
        sys.modules[_mod] = _fake
        # chromadb.config 是子模块，需要单独处理
        if _mod == "chromadb":
            sys.modules["chromadb.config"] = MagicMock()
            _fake.config = sys.modules["chromadb.config"]
            _fake.config.Settings = MagicMock()

# 添加 src 到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


def _make_pipeline():
    """构造一个不连接外部服务的 RAGPipeline 实例"""
    with patch_dependencies():
        from rag_pipeline import RAGPipeline
        pipeline = RAGPipeline(persist_directory="/tmp/fake_chroma_test")
        return pipeline


class patch_dependencies:
    """统一 patch 所有外部依赖的上下文管理器"""

    def __enter__(self):
        # OpenAI
        self._fake_openai_instance = MagicMock()
        self._fake_openai_instance.embeddings.create.return_value = MagicMock(
            data=[MagicMock(embedding=[0.0] * 8)]
        )
        self._fake_openai_instance.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="test response"))]
        )
        self._fake_openai_cls = MagicMock(return_value=self._fake_openai_instance)

        # 把假的 OpenAI 类注入到 rag_pipeline 模块的命名空间
        # （rag_pipeline 内部 `from openai import OpenAI` 拿到的会是我们设的）
        import rag_pipeline as rp_module
        # 注意：rag_pipeline 内部使用的是模块级 `from openai import OpenAI`，
        # 但 OpenAI 这个名字在 rag_pipeline 命名空间里就指向真实的 OpenAI 类
        # 我们直接覆盖 rag_pipeline.OpenAI
        rp_module.OpenAI = self._fake_openai_cls

        # Chroma - 在 vector_store 模块里
        # 由于 vector_store 用的是 `import chromadb` 然后 `chromadb.PersistentClient`，
        # 而我们 mock 的 sys.modules['chromadb'] 是一个 MagicMock，自动有 PersistentClient
        # 所以这里不用额外 patch

        # 设置 API key
        os.environ["OPENAI_API_KEY"] = "fake-key-for-test"
        return self

    def __exit__(self, *args):
        os.environ.pop("OPENAI_API_KEY", None)
        return False


class TestChunkOverlapFix(unittest.TestCase):
    """测试 v0.5.1 chunk_overlap 修复"""

    def setUp(self):
        self.pipeline = _make_pipeline()

    def test_default_overlap_is_50(self):
        """验证默认 chunk_overlap=50（不是 0）"""
        text = "a" * 1000
        docs = [{"text": text, "metadata": {"source": "test.txt"}}]

        chunks = self.pipeline._split_documents(docs, chunk_size=512)

        # 第一个 chunk 和第二个 chunk 应该有 overlap
        self.assertGreater(len(chunks), 1, "1000 字符应该切出多个 chunk")
        first = chunks[0]["text"]
        second = chunks[1]["text"]
        # 第二个 chunk 的前 50 字符应该与第一个 chunk 的后 50 字符重叠
        self.assertEqual(
            first[-50:], second[:50],
            "相邻 chunk 必须有 50 字符 overlap（默认值）"
        )

    def test_custom_overlap(self):
        """验证自定义 chunk_overlap 生效"""
        text = "b" * 1000
        docs = [{"text": text, "metadata": {"source": "t.txt"}}]

        chunks = self.pipeline._split_documents(
            docs, chunk_size=200, chunk_overlap=50
        )

        # chunk_size=200, overlap=50, stride=150
        # 第一个 chunk: [0:200], 第二个 chunk: [150:350]
        self.assertEqual(chunks[0]["text"], "b" * 200)
        self.assertEqual(chunks[1]["text"], "b" * 200)
        # 验证 overlap: chunk0[150:200] == chunk1[0:50]
        self.assertEqual(chunks[0]["text"][150:], chunks[1]["text"][:50])

    def test_invalid_overlap_raises(self):
        """验证 chunk_overlap >= chunk_size 时抛 ValueError（防止死循环）"""
        text = "c" * 1000
        docs = [{"text": text, "metadata": {"source": "t.txt"}}]

        # chunk_overlap == chunk_size
        with self.assertRaises(ValueError) as ctx:
            self.pipeline._split_documents(
                docs, chunk_size=100, chunk_overlap=100
            )
        self.assertIn("必须小于", str(ctx.exception))

        # chunk_overlap > chunk_size
        with self.assertRaises(ValueError):
            self.pipeline._split_documents(
                docs, chunk_size=100, chunk_overlap=200
            )

    def test_blank_chunks_skipped(self):
        """验证全空白 chunk 被跳过"""
        # 文本中嵌入大量空白，验证空白 chunk 不会进入结果
        text = "hello" + " " * 600 + "world"
        docs = [{"text": text, "metadata": {"source": "t.txt"}}]

        chunks = self.pipeline._split_documents(
            docs, chunk_size=100, chunk_overlap=10
        )

        # 验证：没有全空白的 chunk
        for chunk in chunks:
            self.assertTrue(
                chunk["text"].strip(),
                f"空白 chunk 未被跳过: {chunk['text']!r}"
            )

    def test_sliding_window_math(self):
        """验证滑动窗口数学正确性：stride = chunk_size - overlap"""
        text = "x" * 1000
        docs = [{"text": text, "metadata": {"source": "t.txt"}}]

        chunk_size, chunk_overlap = 200, 50
        chunks = self.pipeline._split_documents(
            docs, chunk_size=chunk_size, chunk_overlap=chunk_overlap
        )

        stride = chunk_size - chunk_overlap
        expected_chunk_count = (1000 + stride - 1) // stride  # 向上取整

        self.assertEqual(
            len(chunks), expected_chunk_count,
            f"chunk 数 = {expected_chunk_count}（stride={stride}）"
        )

        # 验证每个 chunk 长度不超过 chunk_size
        for chunk in chunks:
            self.assertLessEqual(len(chunk["text"]), chunk_size)

    def test_metadata_contains_chunk_start(self):
        """验证 chunk metadata 包含 chunk_start，便于回溯原始位置"""
        text = "y" * 1000
        docs = [{"text": text, "metadata": {"source": "t.txt"}}]

        chunks = self.pipeline._split_documents(
            docs, chunk_size=200, chunk_overlap=50
        )

        # 第一个 chunk 的 chunk_start 应该是 0
        self.assertEqual(chunks[0]["metadata"]["chunk_start"], 0)
        # 第二个 chunk 应该是 stride=150
        self.assertEqual(chunks[1]["metadata"]["chunk_start"], 150)
        # 第三个 chunk 应该是 300
        self.assertEqual(chunks[2]["metadata"]["chunk_start"], 300)

    def test_metadata_preserved(self):
        """验证原始文档的 metadata 被复制到每个 chunk"""
        text = "z" * 1000
        original_metadata = {"source": "important.txt", "author": "test"}
        docs = [{"text": text, "metadata": original_metadata}]

        chunks = self.pipeline._split_documents(
            docs, chunk_size=200, chunk_overlap=50
        )

        for chunk in chunks:
            # 原始字段保留
            self.assertEqual(chunk["metadata"]["source"], "important.txt")
            self.assertEqual(chunk["metadata"]["author"], "test")
            # 新增字段存在
            self.assertIn("chunk_id", chunk["metadata"])
            self.assertIn("chunk_start", chunk["metadata"])


class TestNoRegressionInRAGPipeline(unittest.TestCase):
    """测试其他 P0 误报项（已经正确实现）"""

    def setUp(self):
        self.pipeline = _make_pipeline()

    def test_persistentclient_correctly_spelled(self):
        """验证 Chroma 使用 PersistentClient（不是 PersistantClient 拼写错误）"""
        import inspect
        from vector_store import VectorStore
        source = inspect.getsource(VectorStore)
        self.assertIn("PersistentClient", source)
        self.assertNotIn("PersistantClient", source,
                         "PersistantClient 是拼写错误，必须用 PersistentClient")

    def test_collection_add_uses_metadatas(self):
        """验证 collection.add() 使用 metadatas（不是 metadata 单数）"""
        import inspect
        from vector_store import VectorStore
        source = inspect.getsource(VectorStore)
        # metadatas 是 Chroma API 的正确参数名
        self.assertIn("metadatas=", source,
                      "Chroma collection.add() 必须用 metadatas=（复数）")
        # 不应使用单数 metadata=
        self.assertNotIn("metadata=metadatas", source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
