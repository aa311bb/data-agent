import asyncio

from huggingface_hub import AsyncInferenceClient, InferenceClient
from langchain_huggingface import HuggingFaceEndpointEmbeddings
from app.conf.app_config import EmbeddingConfig, app_config


class EmbeddingClientManager:
    def __init__(self, config: EmbeddingConfig):
        self.client: HuggingFaceEndpointEmbeddings | None = None
        self.config = config

    def _get_url(self):
        return f"http://{self.config.host}:{self.config.port}"

    def init(self):
        url = self._get_url()
        embeddings = HuggingFaceEndpointEmbeddings.model_construct(
            model=url,
            repo_id=url,
            task="feature-extraction",
        )
        embeddings.client = InferenceClient(model=url)
        embeddings.async_client = AsyncInferenceClient(model=url)
        self.client = embeddings


embedding_client_manager = EmbeddingClientManager(app_config.embedding)

if __name__ == "__main__":
    embedding_client_manager.init()
    client = embedding_client_manager.client

    text = "What is deep learning"

    async def test():
        query_resul = await client.aembed_query(text)
        print(query_resul[:3])

    asyncio.run(test())
