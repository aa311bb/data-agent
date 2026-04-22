# Data Agent

基于大语言模型的数据分析智能助手，支持自然语言查询数据仓库并自动生成 SQL。

## 架构概览

```
用户自然语言提问
       │
       ▼
  ┌─ LLM (Qwen) ──────────────────────┐
  │  解析意图，生成 SQL                │
  └────────────────────────────────────┘
       ▲                    ▲
       │                    │
  ┌────┴─────┐      ┌──────┴──────┐
  │  Qdrant  │      │ Elasticsearch│
  │ 字段向量  │      │ 维度值全文    │
  │ 检索     │      │ 检索         │
  └──────────┘      └─────────────┘
       ▲                    ▲
       │    Embedding       │
       │   (bge-large-zh)   │
       └────────┬───────────┘
                │
         ┌──────┴──────┐
         │ Meta MySQL  │
         │ 元数据存储   │
         └──────┬──────┘
                │
         ┌──────┴──────┐
         │  DW MySQL   │
         │ 数据仓库     │
         └─────────────┘
```

## 核心组件

| 组件 | 作用 |
|------|------|
| **Meta MySQL** | 存储表结构、字段信息、指标定义等元数据 |
| **DW MySQL** | 数据仓库，存放实际的业务数据 |
| **Embedding (TEI)** | 将文本转为向量，使用 BAAI/bge-large-zh-v1.5 模型 |
| **Qdrant** | 向量数据库，对字段名/描述/别名建立向量索引，实现语义匹配 |
| **Elasticsearch** | 全文检索引擎，对维度字段的取值建立索引，支持中文分词搜索 |
| **LLM (Qwen)** | 大语言模型，解析用户意图并生成 SQL |

## 项目结构

```
data-agent/
├── conf/                          # 配置文件
│   ├── app_config.yaml.example    # 应用配置模板
│   └── meta_config.yaml           # 元知识构建配置
├── app/
│   ├── clients/                   # 外部服务客户端管理
│   │   ├── mysql_client_manager.py
│   │   ├── embedding_client_manager.py
│   │   ├── qdrant_client_manager.py
│   │   └── es_client_manager.py
│   ├── conf/                      # 配置定义
│   │   ├── app_config.py
│   │   └── meta_config.py
│   ├── entities/                  # 数据实体
│   ├── models/                    # ORM 模型
│   ├── repositories/              # 数据访问层
│   │   ├── mysql/                 # MySQL (meta/dw)
│   │   ├── qdrant/                # Qdrant 向量库
│   │   └── es/                    # Elasticsearch
│   ├── services/                  # 业务逻辑
│   └── scripts/                   # 脚本
│       └── build_meta_knowledge.py
└── docker/                        # Docker 部署配置
```

## 快速开始

### 1. 环境准备

```bash
# Python >= 3.12
uv sync
```

### 2. 启动基础设施

```bash
cd docker
docker compose up -d
```

服务包含：MySQL、Qdrant、Elasticsearch (含 IK 分词插件)、HuggingFace TEI (Embedding)。

### 3. 配置

```bash
cp conf/app_config.yaml.example conf/app_config.yaml
# 编辑 conf/app_config.yaml，填入实际的数据库密码、API Key 等
```

### 4. 构建元知识库

将 DW 数据库中的表结构、字段信息同步到 Meta 数据库、Qdrant 向量索引和 ES 全文索引：

```bash
python -m app.scripts.build_meta_knowledge -c conf/meta_config.yaml
```

该脚本会：
1. 读取 `meta_config.yaml` 中定义的表和字段
2. 从 DW 数据库查询字段类型和取值样本
3. 将表/字段元数据写入 Meta MySQL
4. 对字段名、描述、别名生成向量并写入 Qdrant
5. 对 `sync: true` 的维度字段取值写入 Elasticsearch

## 技术栈

- **Web 框架**: FastAPI
- **ORM**: SQLAlchemy (async)
- **向量数据库**: Qdrant
- **搜索引擎**: Elasticsearch (ik_max_word 分词)
- **Embedding**: BAAI/bge-large-zh-v1.5 (via HuggingFace TEI)
- **LLM**: Qwen (via OpenAI-compatible API)
- **Agent 框架**: LangGraph
