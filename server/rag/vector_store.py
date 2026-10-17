"""Milvus向量数据库封装"""
from typing import List, Optional
from pymilvus import MilvusClient, DataType
from core.config import settings
from rag.embeddings import get_embeddings


class VectorStore:
    """Milvus向量存储管理器"""

    def __init__(self):
        self.client = MilvusClient(
            uri=settings.milvus_uri,
            token=settings.milvus_token or None,
        )
        self.collection_name = settings.milvus_collection
        self.embeddings = get_embeddings()
        self._ensure_collection()

    def _ensure_collection(self):
        """集合不存在时按当前 embedding 维度创建"""
        if self.client.has_collection(self.collection_name):
            return
        schema = MilvusClient.create_schema(auto_id=False, enable_dynamic_field=True)
        schema.add_field("id", DataType.VARCHAR, is_primary_key=True, max_length=64)
        schema.add_field("vector", DataType.FLOAT_VECTOR, dim=settings.embedding_dimensions)
        index_params = self.client.prepare_index_params()
        index_params.add_index(
            field_name="vector",
            index_type="AUTOINDEX",
            metric_type="COSINE",
        )
        self.client.create_collection(
            collection_name=self.collection_name,
            schema=schema,
            index_params=index_params,
        )

    def add_documents(self, texts: List[str], metadatas: List[dict], ids: List[str]):
        """
        添加文档向量（分批嵌入）
        :param texts: 文本列表
        :param metadatas: 元数据列表
        :param ids: 向量ID列表
        """
        batch_size = settings.embedding_batch_size
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            batch_metas = metadatas[i:i + batch_size]
            batch_ids = ids[i:i + batch_size]
            vectors = self.embeddings.embed_documents(batch_texts)
            rows = []
            for j in range(len(batch_texts)):
                row = {
                    "id": str(batch_ids[j]),
                    "vector": vectors[j],
                    "content": batch_texts[j],
                }
                for k, v in batch_metas[j].items():
                    if k != "content":
                        row[k] = v
                rows.append(row)
            self.client.insert(collection_name=self.collection_name, data=rows)

    def search(self, query: str, top_k: int = None) -> List[dict]:
        """
        向量相似度检索
        :param query: 查询文本
        :param top_k: 返回数量
        :return: 检索结果列表，元素含 content / metadata / distance
        """
        top_k = top_k or settings.retrieval_top_k
        query_vector = self.embeddings.embed_query(query)
        results = self.client.search(
            collection_name=self.collection_name,
            data=[query_vector],
            limit=top_k,
            output_fields=["content"],
            search_params={"metric_type": "COSINE"},
        )
        items = []
        if results:
            for hit in results[0]:
                entity = hit.get("entity", {}) or {}
                content = entity.pop("content", "")
                items.append({
                    "content": content,
                    "metadata": entity,
                    "distance": hit.get("distance", 0),
                })
        return items

    def delete_by_file_id(self, file_id: int):
        """删除指定文件的所有向量"""
        try:
            self.client.delete(
                collection_name=self.collection_name,
                filter=f"file_id == {int(file_id)}",
            )
        except Exception:
            pass


# 全局单例
_vector_store: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """获取向量存储单例"""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
