from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState
from langgraph.runtime import Runtime
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app.agent.llm import llm
from app.prompt.prompt_loader import load_prompt
from app.core.log import logger

import yaml


async def generate_sql(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    writer = runtime.stream_writer
    writer({"type": "progress", "step": "生成SQL", "status": "running"})

    try:
        query = state["query"]
        table_infos = state["table_infos"]
        metric_infos = state["metric_infos"]
        date_info = state["date_info"]
        db_info = state["db_info"]

        # 借助LLM扩展关键词
        prompt = PromptTemplate(
            template=load_prompt("generate_sql"),
            input_variables=[
                "query",
                "metric_infos",
                "table_infos",
                "date_info",
                "db_info",
            ],
        )
        output_parser = StrOutputParser()

        chain = prompt | llm | output_parser

        result = await chain.ainvoke(
            {
                "query": query,
                "table_infos": yaml.dump(table_infos, allow_unicode=True, sort_keys=False),
                "metric_infos": yaml.dump(
                    metric_infos, allow_unicode=True, sort_keys=False
                ),
                "date_info": yaml.dump(date_info, allow_unicode=True, sort_keys=False),
                "db_info": yaml.dump(db_info, allow_unicode=True, sort_keys=False),
            }
        )

        logger.info(f"llm生成SQL：{result}")
        writer({"type": "progress", "step": "生成SQL", "status": "success"})
        return {"sql": result}
    except Exception as e:
        logger.error(f"生成SQL出错: {e}")
        writer({"type": "progress", "step": "生成SQL", "status": "error"})
        raise
