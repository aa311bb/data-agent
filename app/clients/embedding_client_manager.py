import asyncio

from langchain_community.embeddings import DashScopeEmbeddings
from app.conf.app_config import EmbeddingConfig, app_config


class EmbeddingClientManager:
    def __init__(self, config: EmbeddingConfig):
        self.client: DashScopeEmbeddings | None = None
        self.config = config

    def init(self):
        self.client = DashScopeEmbeddings(
            model=self.config.model,
            dashscope_api_key=self.config.dashscope_api_key,
        )


embedding_client_manager = EmbeddingClientManager(app_config.embedding)

if __name__ == "__main__":
    embedding_client_manager.init()
    client = embedding_client_manager.client

    text = "What is deep learning"

    async def test():
        query_result = await client.aembed_query(text)
        print(query_result[:3])

    asyncio.run(test())
