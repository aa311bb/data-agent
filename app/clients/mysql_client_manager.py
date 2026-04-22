import asyncio

from sqlalchemy import text

from app.conf.app_config import DBConfig, app_config
from sqlalchemy.ext.asyncio import (
    async_sessionmaker,
    create_async_engine,
    AsyncEngine,
)


class MySQLClientManager:
    def __init__(self, config: DBConfig):
        self.engine: AsyncEngine | None = None
        self.session_factory = None
        self.config = config

    def _get_url(self):
        return f"mysql+asyncmy://{self.config.user}:{self.config.password}@{self.config.host}:{self.config.port}/{self.config.database}?charset=utf8mb4"

    def init(self):
        self.engine = create_async_engine(
            self._get_url(), pool_size=10, pool_pre_ping=True
        )
        self.session_factory = async_sessionmaker(self.engine)

    async def close(self):
        await self.engine.dispose()


meta_mysql_client_manager = MySQLClientManager(app_config.db_meta)
dw_mysql_client_manager = MySQLClientManager(app_config.db_dw)


if __name__ == "__main__":
    dw_mysql_client_manager.init()
    # engine = dw_mysql_client_manager.engine

    async def test():
        # async with AsyncSession(
        #     engine, autoflush=True, expire_on_commit=False
        # ) as session:
        async with dw_mysql_client_manager.session_factory() as session:
            sql = "select * from fact_order limit 10"
            result = await session.execute(text(sql))

            # rows = result.fetchall()
            rows2 = result.mappings().fetchall()

            # print(rows)
            print(rows2[0]["order_id"])

    asyncio.run(test())
