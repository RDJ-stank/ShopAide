"""向量存储模块 — 基于 ChromaDB + BAAI/bge-small-zh-v1.5 中文 Embedding"""

import os
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

# ChromaDB 持久化目录（相对于项目根目录）
DEFAULT_PERSIST_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "chroma_db")
DEFAULT_PERSIST_DIR = os.path.abspath(DEFAULT_PERSIST_DIR)

# 中文优化 Embedding 模型，首次运行自动下载（约 100MB）
_MODEL_NAME = "BAAI/bge-small-zh-v1.5"


def get_embedding_model() -> HuggingFaceEmbeddings:
    """返回中文 Embedding 模型实例。

    模型选型说明：
    - BAAI/bge-small-zh-v1.5 在中文检索 benchmark 上表现优异
    - 体积小（~100MB），本地 CPU 推理即可，无 API 成本
    """
    return HuggingFaceEmbeddings(
        model_name=_MODEL_NAME,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )


def build_vector_store(texts: list[str], persist_dir: str | None = None) -> Chroma:
    """从文本列表构建/重建 ChromaDB 向量库。

    Args:
        texts: 政策文本列表（每条为一个检索单元）
        persist_dir: 持久化目录，默认 ./chroma_db/

    Returns:
        已持久化的 Chroma 向量库实例
    """
    persist_dir = persist_dir or DEFAULT_PERSIST_DIR
    embeddings = get_embedding_model()

    vector_store = Chroma.from_texts(
        texts=texts,
        embedding=embeddings,
        persist_directory=persist_dir,
    )
    return vector_store


def get_retriever(persist_dir: str | None = None) -> object:
    """返回配置好的 ChromaDB retriever。

    如果持久化目录已有向量数据，直接加载；否则从 policies 构建。

    Args:
        persist_dir: 持久化目录，默认 ./chroma_db/

    Returns:
        LangChain Retriever 实例（可作为 Tool 注册给 Agent）
    """
    persist_dir = persist_dir or DEFAULT_PERSIST_DIR
    embeddings = get_embedding_model()

    # 从磁盘加载已有向量库（不重新计算 embedding）
    vector_store = Chroma(
        persist_directory=persist_dir,
        embedding_function=embeddings,
    )

    return vector_store.as_retriever(search_kwargs={"k": 3})
