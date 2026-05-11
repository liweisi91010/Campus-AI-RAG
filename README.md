# 校园知识问答系统：Python + MySQL8 + Milvus + Markdown RAG

这个项目适合你的现状：

- VM1 已经 Docker 部署 MySQL8：保存学生问题、审核记录、Markdown 切片元数据。
- VM2 已经安装 Milvus Standalone：保存学工手册/教务文档向量。
- 大模型 API 支持 OpenAI API 规范：用于 embedding、草稿生成、可选安全审核。
- 后端和 AI 处理尽量全 Python：使用 FastAPI + Streamlit。
- 人工审核可以开关：开启时所有回答进入人工审核；关闭时用本地违禁词表做快速审核，通过后直接返回学生。

## 1. 这个压缩包应该在哪里运行？

它不是必须放在 Milvus 那台机器上。它是一个 Python 应用，可以运行在：

1. 你的电脑本机；
2. VM1；
3. VM3；
4. 任意一台能访问 VM1 MySQL、VM2 Milvus、大模型 API 的 Linux 机器。

最简单的部署方式：

```text
VM1：MySQL8 已有
VM2：Milvus Standalone 已有
VM1 或 VM3：运行本项目的 FastAPI + Streamlit
```

只要 `.env` 里面这几个地址能连通即可：

```env
MYSQL_HOST=VM1的IP
MILVUS_URI=http://VM2的IP:19530
OPENAI_BASE_URL=你的OpenAI兼容API地址/v1
OPENAI_API_KEY=你的API Key
```

## 2. Python 版本

推荐使用：

```text
Python 3.11.x
```

原因：项目 Dockerfile 使用的是：

```dockerfile
FROM python:3.11-slim
```

本地运行时，Python 3.10/3.11 通常都可以，但建议直接统一到 3.11，减少依赖兼容问题。

检查版本：

```bash
python3 --version
```

如果系统默认 `python` 指向 Python 3，可以用 `python`；否则建议命令里使用 `python3`。

## 3. 直接依赖列表

项目依赖写在 `requirements.txt`：

```text
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
sqlmodel>=0.0.22
SQLAlchemy>=2.0.35
PyMySQL>=1.1.1
cryptography>=42.0.0
pydantic-settings>=2.6.0
python-dotenv>=1.0.1
openai>=2.0.0
pymilvus==2.6.12
jieba>=0.42.1
PyYAML>=6.0.2
streamlit>=1.41.0
requests>=2.32.3
python-multipart>=0.0.12
```

作用说明：

| 依赖 | 用途 |
|---|---|
| fastapi | 后端 API 框架 |
| uvicorn[standard] | 启动 FastAPI 服务 |
| sqlmodel | Python ORM，定义 MySQL 表结构 |
| SQLAlchemy | 底层数据库访问能力 |
| PyMySQL | Python 连接 MySQL8 |
| cryptography | MySQL8 某些认证方式会用到 |
| pydantic-settings | 从 `.env` 读取配置 |
| python-dotenv | `.env` 支持 |
| openai | 调 OpenAI 或 OpenAI-compatible API |
| pymilvus | 连接 Milvus Standalone |
| jieba | 中文分词，用于关键词处理 |
| PyYAML | 读取高校关键词库 YAML |
| streamlit | Python 前端页面 |
| requests | Streamlit 调后端接口 |
| python-multipart | Markdown 文件上传 |

## 4. 本机 / 虚拟机 Python 方式运行

解压项目：

```bash
unzip campus-ai-python-rag.zip
cd campus-ai-python-rag
```

创建虚拟环境：

```bash
python3 -m venv .venv
source .venv/bin/activate
```

升级 pip 并安装依赖：

```bash
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
```

如果你的服务器访问 PyPI 慢，可以临时用国内镜像：

```bash
python -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

## 5. VM1 MySQL8 准备

进入 VM1 的 MySQL 容器：

```bash
docker exec -it mysql8 mysql -uroot -p
```

执行：

```sql
CREATE DATABASE IF NOT EXISTS campus_ai DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'campus_ai'@'%' IDENTIFIED BY 'campus_ai_pwd';
GRANT ALL PRIVILEGES ON campus_ai.* TO 'campus_ai'@'%';
FLUSH PRIVILEGES;
```

如果你已经有 MySQL 用户，也可以不用新建，只要在 `.env` 里写你的真实账号密码。

如果项目运行在另一个虚拟机，请确认 VM1 防火墙和 Docker 端口映射允许访问 3306。

## 6. 在哪里添加你的大模型 API Key？

在项目根目录复制配置文件：

```bash
cp .env.example .env
```

然后编辑 `.env`：

```bash
nano .env
```

找到这一段：

```env
OPENAI_API_KEY=replace_me
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_CHAT_MODEL=gpt-5.5
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_MODERATION_MODEL=omni-moderation-latest
```

改成你的服务商给你的值，例如：

```env
OPENAI_API_KEY=sk-你的真实Key
OPENAI_BASE_URL=https://你的服务商域名/v1
OPENAI_CHAT_MODEL=你的聊天模型名
OPENAI_EMBEDDING_MODEL=你的embedding模型名
OPENAI_MODERATION_MODEL=omni-moderation-latest
```

如果你的服务商只支持 `/v1/chat/completions`，不支持 OpenAI 的 `/v1/responses`：

```env
USE_RESPONSES_API=false
```

如果你的服务商不支持 moderation 接口：

```env
ENABLE_OPENAI_MODERATION=false
```

注意：

- API Key 不要写进 Python 代码。
- API Key 只放 `.env` 或服务器环境变量。
- `.gitignore` 已经忽略 `.env`。
- 本地 Python 运行时，`app/core/config.py` 会自动读取项目根目录的 `.env`。
- Docker 运行时，`docker-compose.app.yml` 会通过 `env_file: .env` 读取配置。

也可以不用 `.env`，直接用系统环境变量：

```bash
export OPENAI_API_KEY="sk-你的真实Key"
export OPENAI_BASE_URL="https://你的服务商域名/v1"
export OPENAI_CHAT_MODEL="你的聊天模型名"
export OPENAI_EMBEDDING_MODEL="你的embedding模型名"
```

系统环境变量优先级高于 `.env`。

## 7. 配置 MySQL、Milvus 和 API

`.env` 最少需要改这些：

```env
MYSQL_HOST=VM1的IP
MYSQL_PORT=3306
MYSQL_USER=campus_ai
MYSQL_PASSWORD=campus_ai_pwd
MYSQL_DATABASE=campus_ai

MILVUS_URI=http://VM2的IP:19530
MILVUS_COLLECTION=campus_student_handbook
MILVUS_DIMENSION=1536

OPENAI_API_KEY=你的API_KEY
OPENAI_BASE_URL=https://你的OpenAI兼容服务商/v1
OPENAI_CHAT_MODEL=你的聊天模型名
OPENAI_EMBEDDING_MODEL=你的embedding模型名
```

如果你的 embedding 模型不是 1536 维，必须同步修改：

```env
MILVUS_DIMENSION=你的embedding维度
```

如果 collection 已经用旧维度创建过，改维度后要重建 collection。

## 8. 人工审核开关与违禁词快速审核

默认开启人工审核：

```env
MANUAL_REVIEW_ENABLED=true
```

流程是：

```text
学生提问 → RAG 检索 → 大模型生成草稿 → 安全审核 → PENDING_REVIEW → 老师审核 → 返回学生
```

如果你想关闭人工审核，改成：

```env
MANUAL_REVIEW_ENABLED=false
```

关闭后流程变成：

```text
学生提问
→ RAG 检索
→ 大模型生成草稿
→ 模型输入/输出安全审核
→ 校园本地规则审核
→ data/banned_words.txt 违禁词快速审核
→ 通过：状态 APPROVED，直接返回学生
→ 不通过：状态 REJECTED，不返回答案
```

违禁词表位置：

```text
data/banned_words.txt
```

格式：

```text
# 注释会被忽略
系统提示词
API Key
身份证号：
regex:sk-[A-Za-z0-9_-]{20,}
```

规则：

- 普通行：答案里只要包含这个片段，就拦截。
- `regex:` 开头：按正则表达式匹配。
- 建议放高精度违禁片段，不要放太宽泛的词。

例如，不建议直接写：

```text
作弊
```

因为模型正常回答“考试作弊会被处理，请遵守校规”也会被拦截。更适合写高风险片段，例如：

```text
代写论文联系方式
代考联系方式
```

默认只检查“模型最终答复”。如果你也想让学生原始问题走同一份违禁词表，设置：

```env
QUICK_REVIEW_CHECK_QUESTION=true
```

修改 `.env` 后需要重启 FastAPI；只修改 `data/banned_words.txt` 时，下一次请求会重新读取，一般不用重启。

## 9. 检查连接

```bash
python scripts/check_connections.py
```

成功时会看到类似：

```text
MySQL OK: 1
Milvus OK: http://VM2的IP:19530 collection: campus_student_handbook
Manual review enabled: True
Banned words file: data/banned_words.txt
```

测试违禁词表：

```bash
python scripts/test_banned_words.py
```

## 10. Markdown 文档入库

把你的学工手册、教务文档 `.md` 文件放进：

```text
knowledge/
```

执行：

```bash
python -m app.ingest_markdown --knowledge-dir ./knowledge --rebuild
```

这个命令会：

```text
读取 Markdown
→ 按标题和段落切片
→ 从 data/campus_keywords.yml 提取高校关键词和意图
→ 调用 embedding API
→ 把向量写入 Milvus
→ 把切片元数据写入 MySQL knowledge_chunks 表
```

也可以在 Streamlit 页面“上传/重建 Markdown 知识库”里上传 `.md` 文件。

## 11. 启动服务

启动 FastAPI：

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

另开一个终端启动 Streamlit：

```bash
streamlit run streamlit_app/Home.py --server.port 8501 --server.address 0.0.0.0
```

访问：

```text
http://你的VM或本机IP:8501
```

API 健康检查：

```bash
curl http://127.0.0.1:8000/health
```

## 12. Docker 方式运行 Python 应用

MySQL 和 Milvus 你已经有了，所以这个 compose 只启动 FastAPI 和 Streamlit：

```bash
docker compose -f docker-compose.app.yml up -d --build
```

查看日志：

```bash
docker logs -f campus-api
docker logs -f campus-ui
```

修改 `.env` 后重启：

```bash
docker compose -f docker-compose.app.yml restart
```

Linux Docker 容器访问宿主机 MySQL 时，可以在 `.env` 里设置：

```env
MYSQL_HOST=host.docker.internal
```

项目的 compose 已经包含：

```yaml
extra_hosts:
  - "host.docker.internal:host-gateway"
```

如果 MySQL 容器和 campus-api 在同一个 Docker network，`MYSQL_HOST` 也可以写 MySQL 容器名。

## 13. 修改高校专属关键词库

编辑：

```text
data/campus_keywords.yml
```

建议加入：

- 学校部门名：学生工作处、教务处、后勤处、保卫处、学院办公室。
- 学校系统名：智慧校园、一站式服务大厅、网上办事大厅、教务系统。
- 学工手册高频制度词：请假、销假、奖学金、助学金、处分、解除处分、宿舍、晚归、考勤。
- 学校特有简称：学院简称、校区名、办事窗口简称。

别名例子：

```yaml
aliases:
  饭卡: 校园卡
  一卡通: 校园卡
  寝室: 宿舍
  退选: 退课
```

关键词库会参与：

```text
学生问题别名归一
意图识别
MySQL 关键词召回
Milvus 召回结果加权
```

## 14. 测试一次问答

确保已经启动 API 后：

```bash
python scripts/test_query.py
```

或者打开学生端输入：

```text
校园卡丢了应该怎么补办？
```

如果 `MANUAL_REVIEW_ENABLED=true`：

```text
学生端显示 PENDING_REVIEW
管理员后台加载 PENDING_REVIEW
审核通过后学生端刷新看到答案
```

如果 `MANUAL_REVIEW_ENABLED=false`：

```text
违禁词和安全审核通过：学生端可直接看到 APPROVED 和答案
违禁词或安全审核不通过：学生端看到 REJECTED，不返回答案
```

## 15. 生产注意事项

- MySQL 定期备份，至少备份 `question_records` 和 `knowledge_chunks`。
- Milvus collection 可以重建，但原始 Markdown 必须保存好。
- API Key 不要提交到代码仓库。
- 关闭人工审核会提高响应速度，但也会增加错误答复风险。
- 违禁词表要偏高精度，避免把正常政策解释误拦截。
- 对政策条款、时间、金额、电话、网址，prompt 已要求模型“依据不足则不回答”。
