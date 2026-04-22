from pathlib import Path
import uuid

from langchain_huggingface import HuggingFaceEndpointEmbeddings
from omegaconf import OmegaConf

from app.conf.meta_config import MetaConfig
from app.entities.column_info import ColumnInfo
from app.entities.table_info import TableInfo
from app.entities.value_info import ValueInfo
from app.repositories.es.value_es_repository import ValueESRepository
from app.repositories.mysql.dw.dw_mysql_repository import DWMySQLRepository
from app.repositories.mysql.meta.meta_mysql_repository import MetaMySQLRepository
from app.repositories.qdrant.column_qdrant_repository import ColumnQdrantRepository


class MetaKnowledgeService:
    def __init__(
        self,
        meta_mysql_repository: MetaMySQLRepository,
        dw_mysql_repository: DWMySQLRepository,
        column_qdrant_repository: ColumnQdrantRepository,
        embedding_client: HuggingFaceEndpointEmbeddings,
        value_es_repository: ValueESRepository,
    ):
        self.meta_mysql_repository: MetaMySQLRepository = meta_mysql_repository
        self.dw_mysql_repository: DWMySQLRepository = dw_mysql_repository
        self.column_qdrant_repository: ColumnQdrantRepository = column_qdrant_repository
        self.embedding_client: HuggingFaceEndpointEmbeddings = embedding_client
        self.value_es_repository: ValueESRepository = value_es_repository

    # 2.1 保存表信息到meta数据库
    async def _save_tables_to_meta_db(
        self, meta_config: MetaConfig
    ) -> list[ColumnInfo]:
        table_infos: list[TableInfo] = []
        column_infos: list[ColumnInfo] = []

        for table in meta_config.tables:
            table_info = TableInfo(
                id=table.name,
                name=table.name,
                role=table.role,
                description=table.description,
            )
            table_infos.append(table_info)

            # 查询字段类型
            column_types = await self.dw_mysql_repository.get_column_types(table.name)

            for column in table.columns:
                # 查询字段取值示例
                column_values = await self.dw_mysql_repository.get_column_values(
                    table.name, column.name
                )

                column_info = ColumnInfo(
                    id=f"{table.name}.{column.name}",
                    name=column.name,
                    type=column_types[column.name],
                    role=column.role,
                    examples=column_values,
                    description=column.description,
                    alias=column.alias,
                    table_id=table.name,
                )

                column_infos.append(column_info)

        async with self.meta_mysql_repository.session.begin():
            self.meta_mysql_repository.save_table_infos(table_infos)
            self.meta_mysql_repository.save_column_infos(column_infos)

        return column_infos

    # 2.2对字段信息建立向量索引
    async def _save_column_info_to_qdrant(self, column_infos: list[ColumnInfo]):

        await self.column_qdrant_repository.ensure_collection()

        # 构造待保存的数据
        points: list[dict] = []
        for column_info in column_infos:
            points.append(
                {
                    "id": uuid.uuid4(),
                    "embedding_text": column_info.name,
                    "payload": column_info,
                }
            )
            points.append(
                {
                    "id": uuid.uuid4(),
                    "embedding_text": column_info.description,
                    "payload": column_info,
                }
            )
            for alia in column_info.alias:
                points.append(
                    {
                        "id": uuid.uuid4(),
                        "embedding_text": alia,
                        "payload": column_info,
                    }
                )

        # 向量化
        embedding_texts = [point["embedding_text"] for point in points]
        embedding_batch_size = 10
        embeddings: list[list[float]] = []
        for i in range(0, len(embedding_texts), embedding_batch_size):
            batch_embedding_texts = embedding_texts[i : i + embedding_batch_size]
            batch_embeddings = await self.embedding_client.aembed_documents(
                batch_embedding_texts
            )
            embeddings.extend(batch_embeddings)

        # id列表
        ids = [point["id"] for point in points]

        # payload列表
        payloads = [point["payload"] for point in points]

        # 保存数据到qdrant
        await self.column_qdrant_repository.upsert(ids, embeddings, payloads)

    # 2.3对指定的维度字段取值建立全文索引
    async def _save_value_info_to_es(
        self, meta_config: MetaConfig, column_infos: list[ColumnInfo]
    ):
        await self.value_es_repository.ensure_index()

        # 构造ValueInfo列表
        value_infos: list[ValueInfo] = []
        for table in meta_config.tables:
            for column in table.columns:
                if column.sync:
                    # 查询这个列的所有取值
                    current_column_values = (
                        await self.dw_mysql_repository.get_column_values(
                            table.name, column.name, 100000
                        )
                    )
                    current_values_infos = [
                        ValueInfo(
                            id=f"{table.name}.{column.name}.{current_column_value}",
                            value=current_column_value,
                            column_id=f"{table.name}.{column.name}",
                        )
                        for current_column_value in current_column_values
                    ]
                    value_infos.extend(current_values_infos)

        # 批量保存到Elasticsearch
        await self.value_es_repository.index(value_infos)

    async def build(self, config_path: Path):
        # 1.读取配置文件
        context = OmegaConf.load(config_path)
        schema = OmegaConf.structured(MetaConfig)
        meta_config: MetaConfig = OmegaConf.to_object(OmegaConf.merge(schema, context))

        # 2.根据配置文件同步指定的表信息和指标信息
        if meta_config.tables:
            # 2.1 保存表信息到meta数据库
            column_infos = await self._save_tables_to_meta_db(meta_config)

            # 2.2对字段信息建立向量索引
            await self._save_column_info_to_qdrant(column_infos)

            # 2.3对指定的维度字段取值建立全文索引
            await self._save_value_info_to_es(meta_config)

        # 3根据配置文件同步指定的指标信息
        if meta_config.metrics:
            # 3.1 将指标信息保存meta数据库中

            # 3.2对指标信息建立向量索引

            pass
