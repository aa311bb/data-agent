import asyncio

from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState
from langgraph.runtime import Runtime


async def add_extra_context(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    runtime.stream_writer("正在添加额外的上下文信息...")
    # writer("正在添加额外的上下文信息...")
    await asyncio.sleep(0.5)  # 模拟添加上下文的时间
