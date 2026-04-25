# Data Agent

基于 LLM 的自然语言转 SQL 查询代理。用户以自然语言提问，系统自动检索数据仓库元数据、生成 SQL、验证、执行并流式返回结果。

## 架构概览

```
用户自然语言查询
        |
        v
   POST /api/query (FastAPI, SSE 流式)
        |
        v
   [extract_keywords]  ← jieba 中文分词
        |
    +---+---+--- (并行召回)
    |   |   |
    v   v   v
 [recall_column] [recall_value] [recall_metric]
 (Qdrant 向量    (Elasticsearch   (Qdrant 向量
  检索)           全文检索)        检索)
    |   |   |
    +---+---+--- (合并)
        |
        v
   [merge_retrieved_info]
        |
    +---+---+ (并行过滤)
    |       |
    v       v
 [filter_table]  [filter_metric]
 (LLM 筛选       (LLM 筛选
  相关表/列)      相关指标)
    |       |
    +---+---+
        |
        v
   [add_extra_context]  ← 注入日期、数据库方言
        |
        v
   [generate_sql]  ← LLM 生成 SQL
        |
        v
   [validate_sql]   ← EXPLAIN 验证
      /       \
   (通过)    (失败)
     |         |
     v         v
 [run_sql]  [correct_sql] → [run_sql]
     |
     v
  SSE 流式返回结果
```

## 技术栈

| 组件 | 技术 | 用途 |
|---|---|---|
| Web 框架 | FastAPI + Uvicorn | API 服务, SSE 流式响应 |
| Agent 工作流 | LangGraph | 多步骤状态图, 并行节点, 条件路由 |
| LLM | Qwen (DashScope OpenAI 兼容) | 关键词扩展、过滤、SQL 生成/纠错 |
| Embedding | DashScope text-embedding-v4 | 列名/指标名语义向量化 |
| 向量数据库 | Qdrant | 列信息、指标信息语义检索 |
| 全文检索 | Elasticsearch + IK 分词 | 维度字段值全文检索 |
| 元数据存储 | MySQL | 表/列/指标元信息 |
| 数据仓库 | MySQL | 业务数据, SQL 执行 |
| 配置 | OmegaConf + YAML | 结构化配置管理 |

## 分层结构

```
app/
├── api/                  # API 层: 路由、Schema、依赖注入、生命周期
├── agent/                # Agent 层: LangGraph 图定义、状态、节点
│   └── nodes/            # 各图节点实现
├── services/             # 服务层: 查询编排、元知识构建
├── repositories/         # 数据访问层: MySQL/Qdrant/ES 仓库
├── clients/              # 连接管理: MySQL/Qdrant/ES/Embedding 客户端
├── models/               # SQLAlchemy ORM 模型
├── entities/             # 领域数据类
├── conf/                 # 配置 Schema 与加载
├── scripts/              # 脚本: 元知识构建入口
├── prompt/               # Prompt 模板加载器
└── core/                 # 日志等基础组件
conf/                     # 配置文件 (YAML)
prompts/                  # LLM Prompt 模板
docker/                   # Docker Compose 与初始化 SQL
```

## 快速开始

### 前置要求

- Python >= 3.12
- [uv](https://github.com/astral-sh/uv) 包管理器
- Docker & Docker Compose
- DashScope API Key

### 1. 安装依赖

```bash
uv sync
```

### 2. 启动基础设施

```bash
cd docker
docker compose up -d
```

启动以下服务:
- **MySQL 8.0** (端口 3306) — 元数据库 + 数据仓库
- **Elasticsearch 8.19** (端口 9200) — 全文检索, 预装 IK 分词插件
- **Kibana** (端口 5601) — ES 管理界面
- **Qdrant** (端口 6333/6334) — 向量数据库

### 3. 配置应用

```bash
cp conf/app_config.yaml.example conf/app_config.yaml
```

编辑 `conf/app_config.yaml`, 填入实际的数据库连接信息和 DashScope API Key。

### 4. 构建元知识库

```bash
python -m app.scripts.build_meta_knowledge -c conf/meta_config.yaml
```

此命令会:
- 读取 `conf/meta_config.yaml` 中的表/列/指标定义
- 从数据仓库拉取列类型和样本值
- 将元信息写入 Meta MySQL
- 生成列和指标的向量嵌入, 写入 Qdrant
- 将维度字段值索引到 Elasticsearch

### 5. 启动服务

```bash
uvicorn main:app --reload
```

### 6. 查询示例

```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "统计华北地区的销售总额"}'
```

返回 SSE 流, 包含进度事件和最终 SQL 查询结果。

## 配置说明

### app_config.yaml

| 配置项 | 说明 |
|---|---|
| `logging` | Loguru 日志配置 (文件/控制台) |
| `db_meta` | 元数据库 MySQL 连接 |
| `db_dw` | 数据仓库 MySQL 连接 |
| `qdrant` | Qdrant 向量数据库连接 |
| `embedding` | DashScope Embedding API 配置 |
| `es` | Elasticsearch 连接与索引配置 |
| `llm` | LLM 模型配置 (默认 Qwen via DashScope) |

### meta_config.yaml

定义数据仓库的星型 Schema 元数据:
- **tables**: 表名、角色 (fact/dim)、描述、列定义
- **columns**: 列名、角色 (primary_key/foreign_key/measure/dimension)、描述、别名
- **metrics**: 指标名、描述、关联列、别名、SQL 表达式

## Agent 工作流节点

| 节点 | 功能 |
|---|---|
| `extract_keywords` | jieba 中文关键词提取 |
| `recall_column` | LLM 扩展关键词 → 向量检索相关列 (Qdrant) |
| `recall_value` | LLM 扩展关键词 → 全文检索维度值 (Elasticsearch) |
| `recall_metric` | LLM 扩展关键词 → 向量检索相关指标 (Qdrant) |
| `merge_retrieved_info` | 合并召回结果, 组装结构化表/指标信息 |
| `filter_table` | LLM 过滤无关表和列 |
| `filter_metric` | LLM 过滤无关指标 |
| `add_extra_context` | 注入当前日期、星期、季度及数据库方言信息 |
| `generate_sql` | LLM 根据上下文生成 SQL |
| `validate_sql` | EXPLAIN 验证 SQL 合法性 |
| `correct_sql` | 验证失败时 LLM 纠错 SQL |
| `run_sql` | 执行 SQL 并流式返回结果 |

## License

MIT
