# Campus AI RAG 定制化高校AI问答助手

一个基于 **Python + FastAPI + Streamlit + MySQL + Milvus + LongCat/OpenAI 兼容大模型 API** 的高校AI问答助手。

项目汇总了高校学生手册、教务处文件、高校规章制度等知识文档，支持将本校知识库向量化后进行检索增强生成，最终由大模型生成回答。系统支持 **人工审核模式** 和 **违禁词快速审核模式**，适合作为校园智能客服、学工问答助手、教务问答助手的原型项目。

---

## 1. 项目功能

- 学生端在线提问
- Markdown格式 高校知识文档入库
- 定制化高校关键词库匹配
- 中文分词与本地向量生成
- Milvus 向量检索
- MySQL 保存问答记录、知识片段、审核状态
- 调用 LongCat-Flash-Lite 或其他 OpenAI API 兼容模型生成回答
- 支持人工审核后返回学生，支持关闭人工审核，改用违禁词表进行快速审核
- 支持查询历史问题的审核状态和最终答案

---

## 2. 技术栈

| 模块 | 技术 |
|---|---|
| 后端 API | FastAPI |
| 前端页面 | Streamlit |
| 数据库 | MySQL |
| 向量数据库 | Milvus |
| ORM | SQLModel / SQLAlchemy |
| 中文分词 | jieba |
| 配置管理 | python-dotenv / pydantic-settings |
| 大模型接口 | LongCat-Flash-Lite / OpenAI Compatible API |
| 向量化方案 | 本地 `local_hash` 向量化 |
| 审核机制 | 人工审核 / 违禁词快速审核 |
| 部署方式 | Python 直接运行 / Docker Compose |

---

## 3. 系统数据流程

整体流程如下：

```text
学生原始问题
    ↓
问题清洗与纠错
    ↓
本校关键词识别
    ↓
意图识别
    ↓
MySQL 关键词召回
    ↓
Milvus 向量召回
    ↓
合并知识上下文
    ↓
判断知识库相关性
    ↓
调用 LongCat/OpenAI 兼容大模型生成草稿
    ↓
安全规则与违禁词审核
    ↓
人工审核 或 自动快速通过
    ↓
返回学生最终答案
````

## 4. 项目结构

```text
campus-ai-python-rag/
├── app/
│   ├── api/                    # FastAPI 接口
│   ├── core/                   # 配置文件
│   ├── db/                     # MySQL 连接
│   ├── models/                 # 数据库模型
│   ├── schemas/                # 请求和响应结构
│   ├── services/               # 核心业务逻辑
│   ├── main.py                 # FastAPI 启动入口
│   └── ingest_markdown.py      # Markdown 入库入口
│
├── streamlit_app/
│   ├── Home.py                 # Streamlit 首页
│   └── pages/
│       ├── 1_Student_QA.py     # 学生问答页面
│       ├── 2_Admin_Review.py   # 人工审核页面
│       └── 3_Knowledge_Ingest.py # 知识库入库页面
│
├── data/
│   ├── campus_keywords.yml     # 本校关键词库
│   ├── typo_map.yml            # 错别字和别名映射
│   └── banned_words.txt        # 违禁词表
│
├── knowledge/                  # Markdown 知识文档目录
├── scripts/                    # 检查脚本和测试脚本
├── requirements.txt            # Python 依赖
├── docker-compose.app.yml      # Docker 启动文件
├── Dockerfile
├── .env.example                # 环境变量示例
└── README.md
```

---

## 5. 环境要求

推荐环境：

```text
Python 3.11+
MySQL 8
Milvus Standalone
Docker，可选
```

本项目默认使用：

```text
MySQL：保存结构化数据
Milvus：保存向量化后的知识片段
LongCat-Flash-Lite：负责最终回答生成
local_hash：本地生成知识向量，不依赖额外 embedding API
```

---

## 6. 安装依赖

python所需依赖已经归类到一处：

```bash
python -m pip install -r requirements.txt
```

---

## 7. 初始化 MySQL

如果你已经有自己的 MySQL 用户，也可以直接在 `.env` 中配置已有账号。

---

## 8. 配置环境变量

编辑 `.env`，示例配置：

```env
# MySQL
MYSQL_HOST=你的MySQL服务器IP
MYSQL_PORT=3306
MYSQL_USER=your_user
MYSQL_PASSWORD=your_pwd
MYSQL_DATABASE=your_ai_db
MYSQL_CHARSET=utf8mb4

# Milvus
MILVUS_URI= http://你的Milvus服务器IP:19530
MILVUS_TOKEN=
MILVUS_COLLECTION= your_collection
MILVUS_DIMENSION= 默认1024
MILVUS_METRIC= 默认COSINE

# OpenAI Compatible API
OPENAI_API_KEY=your_API_KEY
OPENAI_BASE_URL=your_url
OPENAI_CHAT_MODEL=your_model

# 本地向量化
EMBEDDING_PROVIDER=local_hash
OPENAI_EMBEDDING_MODEL=

# 当前使用 chat/completions 格式返回数据
USE_RESPONSES_API=false

# 如果平台没有 moderation 接口，可以关闭
ENABLE_OPENAI_MODERATION=false
OPENAI_MODERATION_MODEL=omni-moderation-latest

# 审核模式，默认关闭人工审核
MANUAL_REVIEW_ENABLED=false
BANNED_WORDS_FILE=./data/banned_words.txt
QUICK_REVIEW_CHECK_QUESTION=false

# 知识库与检索配置
KNOWLEDGE_DIR=./knowledge
KEYWORD_FILE=./data/campus_keywords.yml
TYPO_FILE=./data/typo_map.yml
TOP_K=5
MIN_RELEVANCE_SCORE=0.55
CHUNK_MAX_CHARS=900
CHUNK_OVERLAP_CHARS=120

# 服务配置
API_HOST=0.0.0.0
API_PORT=8000
STREAMLIT_API_BASE=http://127.0.0.1:8000
ADMIN_TOKEN=change_this_admin_token
```

---

## 9. 配置本校关键词库

关键词库文件：

```text
data/campus_keywords.yml
```

建议根据本校学工手册、教务文件中的高频词进行补充。

---

## 10. 配置违禁词表

违禁词文件：

```text
data/banned_words.txt
```

---

## 11. 导入 Markdown 知识库

将本校学工手册、教务文件等 Markdown 文档放入：

```text
knowledge/
```

例如：

```text
knowledge/student_handbook.md
knowledge/teaching_affairs.md
```

执行入库命令：

```bash
python -m app.ingest_markdown --knowledge-dir ./knowledge --rebuild
```

该命令会：

```text
读取 Markdown
切分文本片段
提取关键词
生成本地向量
写入 Milvus
写入 MySQL
```

如果修改了知识库文件或关键词库，建议重新执行入库命令。

---

## 12. 启动项目

启动后端 API：

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

另开一个终端，启动前端页面：

```bash
streamlit run streamlit_app/Home.py --server.port 8501 --server.address 0.0.0.0
```

访问页面：

```text
http://服务器IP:8501
```

FastAPI 接口文档：

```text
http://服务器IP:8000/docs
```

健康检查：

```bash
curl http://127.0.0.1:8000/health
```

---

## 13. Docker 启动方式

如果使用 Docker 启动应用：

```bash
docker compose -f docker-compose.app.yml up -d --build
```

查看日志：

```bash
docker logs -f campus-api
docker logs -f campus-ui
```

重新创建容器：

```bash
docker compose -f docker-compose.app.yml up -d --force-recreate
```

---

## 14. 审核模式说明

### 人工审核模式

配置：

```env
MANUAL_REVIEW_ENABLED=true
```

流程：

```text
学生提问
→ 系统生成草稿
→ 状态变为 PENDING_REVIEW
→ 管理员审核
→ 审核通过后学生看到最终答案
```

### 快速审核模式

配置：

```env
MANUAL_REVIEW_ENABLED=false
```

流程：

```text
学生提问
→ 系统生成草稿
→ 违禁词与安全规则检查
→ 通过后直接 APPROVED
→ 学生立即看到答案
```

快速审核适合测试环境或低风险问答。正式环境建议对高风险问题保留人工审核，例如：

```text
考试资格
处分申诉
成绩认定
奖助学金资格
毕业审核
学籍异动
```

---

## 15. 常见问题

### 1. Streamlit 报 `No module named 'streamlit_app'`

请从项目根目录启动：

```bash
cd campus-ai-python-rag
python -m streamlit run streamlit_app/Home.py --server.port 8501 --server.address 0.0.0.0
```

不要进入 `streamlit_app/` 目录后再启动。

### 2. 修改 `.env` 后不生效

`.env` 是服务启动时读取的。修改后需要重启后端。

Python 方式：

```bash
Ctrl + C
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Docker 方式：

```bash
docker compose -f docker-compose.app.yml up -d --force-recreate
```

### 3. 部分问题没有调用大模型

系统会先判断知识库相关性。如果检索不到足够可靠的本校知识片段，可能不会调用大模型，而是返回兜底答案。

### 4. 回答出现非本校内容

建议：

```text
清理知识库中的外校资料
补充本校正式文档
提高 MIN_RELEVANCE_SCORE
对高风险问题开启人工审核
在 Prompt 中要求只依据本校知识库回答
```

---

## 16. 安全说明

本项目用于校园知识问答原型开发。系统回答应以本校正式文件、学工部门、教务部门的最新解释为准。

建议正式上线前增加：

```text
登录认证
管理员权限控制
接口限流
日志审计
知识库来源标记
答案引用来源
高风险问题人工审核
敏感信息脱敏
```

---

## 17. License

本项目仅用于学习、课程设计、毕业设计和校园智能问答原型验证。

可根据实际情况添加开源协议，例如 MIT License。
