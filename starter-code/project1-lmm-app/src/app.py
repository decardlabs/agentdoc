"""
Streamlit 应用主文件

本模块是 LLM 文档问答 Web 应用的主入口，提供：
1. 文件上传界面
2. 问答交互界面
3. 流式输出展示
4. Token 计数和成本显示

作者：智能体工程师培养计划
日期：2024
"""

import streamlit as st
import tempfile
import os
from typing import List, Dict, Optional

# 导入自定义模块
from pdf_loader import PDFLoader
from lmm_client import LLMClient
from prompt_templates import PromptBuilder

# 配置页面
st.set_page_config(
    page_title="LLM 文档问答助手",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 标题
st.title("📚 LLM 文档问答助手")
st.markdown("---")

# 侧边栏：配置区
with st.sidebar:
    st.header("⚙️ 配置")
    
    # API Key 配置
    api_key = st.text_input("OpenAI API Key", type="password", help="在 https://platform.openai.com 获取")
    if api_key:
        os.environ["OPENAI_API_KEY"] = api_key
    
    # 模型选择
    model = st.selectbox("选择模型", ["gpt-4o-mini", "gpt-4o"], help="gpt-4o-mini 性价比高，gpt-4o 质量更好")
    
    # 高级选项
    with st.expander("高级选项"):
        temperature = st.slider("温度 (Temperature)", 0.0, 1.0, 0.7, help="越高越随机，越低越确定")
        max_tokens = st.number_input("最大输出 Token", 100, 4000, 2000, help="控制回答长度")
        use_fewshot = st.checkbox("启用 Few-shot 示例", help="提升回答质量，但增加 Token 消耗")
    
    st.markdown("---")
    st.markdown("### 📊 统计")
    if "total_tokens" in st.session_state:
        st.metric("总 Token 消耗", st.session_state.total_tokens)
    if "total_cost" in st.session_state:
        st.metric("总成本 (USD)", f"${st.session_state.total_cost:.4f}")

# 初始化 Session State
if "messages" not in st.session_state:
    st.session_state.messages = []
if "doc_chunks" not in st.session_state:
    st.session_state.doc_chunks = None
if "doc_name" not in st.session_state:
    st.session_state.doc_name = None
if "total_tokens" not in st.session_state:
    st.session_state.total_tokens = 0
if "total_cost" not in st.session_state:
    st.session_state.total_cost = 0.0

# 主界面：分为两列
col1, col2 = st.columns([1, 2])

# 左侧：文档上传区
with col1:
    st.header("📄 文档上传")
    
    uploaded_file = st.file_uploader(
        "选择 PDF 文件",
        type=["pdf"],
        help="支持 PDF 格式，建议不超过 100 页"
    )
    
    if uploaded_file is not None:
        # 保存到临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_file_path = tmp_file.name
        
        # 加载和切分 PDF
        with st.spinner("正在加载文档..."):
            try:
                loader = PDFLoader()
                chunks = loader.load_and_split(tmp_file_path)
                
                # 保存到 Session State
                st.session_state.doc_chunks = chunks
                st.session_state.doc_name = uploaded_file.name
                
                # 清理临时文件
                os.unlink(tmp_file_path)
                
                st.success(f"✅ 文档加载成功！")
                st.info(f"文件名: {uploaded_file.name}\n页数: 约 {len(chunks)} 个片段")
                
                # 显示文档预览
                with st.expander("文档预览"):
                    st.text(chunks[0][:500] + "..." if len(chunks[0]) > 500 else chunks[0])
                
            except Exception as e:
                st.error(f"❌ 文档加载失败: {str(e)}")
    
    # 文档管理
    if st.session_state.doc_name:
        st.markdown("---")
        st.markdown(f"**当前文档**: {st.session_state.doc_name}")
        if st.button("🗑️ 清除文档"):
            st.session_state.doc_chunks = None
            st.session_state.doc_name = None
            st.session_state.messages = []
            st.rerun()

# 右侧：问答区
with col2:
    st.header("💬 问答区")
    
    # 检查文档是否加载
    if not st.session_state.doc_chunks:
        st.info("👈 请先上传文档")
    else:
        # 显示聊天历史
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        
        # 用户输入
        if prompt := st.chat_input("请输入你的问题..."):
            # 添加用户消息到历史
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            # 显示用户消息
            with st.chat_message("user"):
                st.markdown(prompt)
            
            # 生成回答
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                full_response = ""
                
                # 构造 Prompt
                try:
                    # 合并所有 Chunks（简化版，项目 3 会改进为向量检索）
                    doc_content = "\n\n".join(st.session_state.doc_chunks)
                    
                    # 构建 messages
                    prompt_builder = PromptBuilder(use_fewshot=use_fewshot)
                    messages = prompt_builder.build_messages(
                        doc_content,
                        prompt,
                        st.session_state.messages[:-1]  # 不包括当前问题
                    )
                    
                    # 调用 LLM
                    client = LLMClient(model=model, temperature=temperature, max_tokens=max_tokens)
                    
                    # 流式输出
                    for chunk in client.chat(messages, stream=True):
                        full_response += chunk
                        message_placeholder.markdown(full_response + "▌")
                    
                    message_placeholder.markdown(full_response)
                    
                    # 更新统计
                    input_tokens = client.count_tokens(messages)
                    output_tokens = client.count_tokens([{"role": "assistant", "content": full_response}])
                    st.session_state.total_tokens += input_tokens + output_tokens
                    st.session_state.total_cost += client.estimate_cost(input_tokens, output_tokens)
                    
                    # 显示 Token 消耗
                    with st.expander("📊 Token 消耗"):
                        st.write(f"输入 Token: {input_tokens}")
                        st.write(f"输出 Token: {output_tokens}")
                        st.write(f"本次成本: ${client.estimate_cost(input_tokens, output_tokens):.4f}")
                    
                except Exception as e:
                    st.error(f"❌ 生成回答失败: {str(e)}")
                    full_response = "抱歉，生成回答时出现错误。"
                
                # 添加助手回复到历史
                st.session_state.messages.append({"role": "assistant", "content": full_response})

# 底部：说明
st.markdown("---")
st.markdown("""
### 使用说明
1. 在左侧上传 PDF 文档
2. 在右侧输入问题
3. 系统会基于文档内容回答

### 注意事项
- 文档过长时，可能只使用部分内容（防止 Prompt 过长）
- 建议在侧边栏配置自己的 API Key
- 回答质量取决于文档质量和问题描述

### 关于
- 项目: 智能体工程师培养计划 - Phase 1
- 功能: LLM 文档问答 Web 应用
""")
