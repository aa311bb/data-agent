from datetime import date

from app.agent.context import DataAgentContext
from app.agent.state import DBInfoState, DataAgentState, DateInfoState
from langgraph.runtime import Runtime
from app.core.log import logger


async def add_extra_context(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    writer = runtime.stream_writer
    writer({"type": "progress", "step": "添加额外上下文信息", "status": "running"})

    try:
        dw_mysql_repository = runtime.context["dw_mysql_repository"]

        # 当前的时间信息
        today = date.today()
        # 日期
        date_str = today.strftime("%Y-%m-%d")
        # 星期
        weekday = today.strftime("%A")
        # 季度
        quarter = f"Q{(today.month - 1) // 3 + 1}"

        date_info = DateInfoState(date=date_str, weekday=weekday, quarter=quarter)

        # 数据仓库环境信息
        db = await dw_mysql_repository.get_db_info()
        db_info = DBInfoState(**db)

        logger.info(f"额外上下文信息：数据库信息-{db_info} 日期信息-{date_info}")
        writer({"type": "progress", "step": "添加额外上下文信息", "status": "success"})
        return {
            "date_info": date_info,
            "db_info": db_info,
        }
    except Exception as e:
        logger.error(f"添加额外上下文信息出错: {e}")
        writer({"type": "progress", "step": "添加额外上下文信息", "status": "error"})
        raise
