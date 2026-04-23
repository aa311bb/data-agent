from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState
from langgraph.runtime import Runtime
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from app.prompt.prompt_loader import load_prompt
from app.core.log import logger
from app.agent.llm import llm
from app.entities.metric_info import MetricInfo


async def recall_metric(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    writer = runtime.stream_writer
    writer({"type": "progress", "step": "召回指标", "status": "running"})

    keywords = state["keywords"]
    query = state["query"]

    metric_qdrant_repository = runtime.context["metric_qdrant_repository"]
    embedding_client = runtime.context["embedding_client"]

    # 借助LLM扩展关键词
    prompt = PromptTemplate(
        template=load_prompt("extend_keywords_for_metric_recall"),
        input_variables=["query"],
    )
    output_parser = JsonOutputParser()

    chain = prompt | llm | output_parser

    result = await chain.ainvoke({"query": query})
    logger.info(f"llm指标信息扩展关键词：{result}")

    keywords = set(keywords + result)

    # 从Qdrant中检索字段信息
    metric_info_map: dict[str, MetricInfo] = {}
    for keyword in keywords:
        # 对keyword进行embedding
        embedding = await embedding_client.aembed_query(keyword)
        current_metric_infos: list[MetricInfo] = await metric_qdrant_repository.search(
            embedding,
        )
        for metric_info in current_metric_infos:
            if metric_info.id not in metric_info_map:
                metric_info_map[metric_info.id] = metric_info

    retrieved_metric_infos: list[MetricInfo] = list(metric_info_map.values())

    logger.info(f"检索到指标信息：{list(metric_info_map)}")
    return {
        "retrieved_metric_infos": retrieved_metric_infos,
    }
