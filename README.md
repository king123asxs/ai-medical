# AI 智能医疗问诊平台（ai-medical）

基于 **RAG + LangChain + Neo4j 知识图谱 + FastAPI + Vue3** 的智能医疗问诊系统。支持患者 / 医生 / 管理员三角色，AI 问诊采用 SSE 流式输出，回答附带可追溯的知识引用。

## 技术栈

| 层次 | 技术 |
|------|------|
| 前端 | Vue3 + Element Plus + Pinia + Vue Router + ECharts + Vite |
| 后端 | Python 3.11 + FastAPI + SQLAlchemy + Pydantic |
| 数据库 | MySQL 8（业务数据）+ Neo4j（疾病-症状-药品-科室图谱）+ Milvus（向量库） |
| AI | 通义千问（OpenAI 兼容接口）+ LangChain RAG + text-embedding-v4 |

## 项目结构

```
├── client/            # Vue3 前端（患者端 / 医生端 / 管理端）
├── server/            # FastAPI 后端
│   ├── api/           # REST + SSE 路由
│   ├── core/          # 配置与安全（JWT）
│   ├── models/        # SQLAlchemy ORM
│   ├── schemas/       # Pydantic 校验
│   ├── services/      # 业务逻辑（认证 / RAG / 图谱 / 统计）
│   ├── rag/           # 文档加载 / 分块 / 向量检索
│   └── scripts/       # 建库 / 图谱 / 知识库初始化
├── database/          # MySQL 初始化 SQL（db_ai_medical）
├── knowledge_base/    # 内置医疗知识文档（可用于快速导入）
└── docs/              # 架构图 / ER 图 / 时序图 / 运行截图
```

## 环境要求

- Python 3.11+
- Node.js 18+（含 npm）
- MySQL 8（默认端口 3306，可改）
- Neo4j 5.x（Bolt 端口 7687）
- 阿里云 DashScope / MaaS 的 API Key（用于通义千问与 Embedding）

## 快速开始

### 1. 数据库初始化

```sql
CREATE DATABASE db_ai_medical DEFAULT CHARACTER SET utf8mb4;
```

导入初始数据：

```bash
mysql -u root -P 3306 -p db_ai_medical < database/db_ai_medical.sql
```

Neo4j 无需手动建库，后面用脚本初始化。

### 2. 后端配置

```bash
cd server
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

复制环境变量模板并填写：

```bash
cp .env.example .env
# Windows PowerShell
Copy-Item .env.example .env
```

至少需要填写：

```env
OPENAI_API_KEY=sk-xxxx
JWT_SECRET_KEY=一段随机字符串
MYSQL_PASSWORD=你的密码
NEO4J_PASSWORD=你的密码
```

没有配置 Key 时系统可启动，但 AI 问诊和向量化功能不可用。

### 3. 初始化图谱与知识库

```bash
cd server
python scripts/init_graph.py       # 构建 Neo4j 疾病-症状-药品-科室图谱
python scripts/init_knowledge.py   # 把 knowledge_base/ 下的文档向量化并写入 Milvus
```

### 4. 启动后端

```bash
cd server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

启动后访问 <http://127.0.0.1:8000/docs> 查看接口文档。

### 5. 启动前端

```bash
cd client
npm install
npm run dev
```

默认 <http://127.0.0.1:5173>。首次使用请先注册患者账号；管理员/医生账号来自数据库初始数据。

## 演示账号

| 角色 | 账号 | 密码 | 说明 |
|------|------|------|------|
| 管理员 | admin | 123456 | 后台统计、知识库与图谱管理 |
| 医生 | doctor01 | 123456 | 咨询处理、预约确认 |
| 患者 | user01 | 123456 | AI 问诊、预约、健康档案 |

> 仅用于本地演示，生产环境请立即修改。

## 部署（生产环境建议）

### 后端

```bash
cd server
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

用 systemd / supervisor / Docker 守护，前置 Nginx 反向代理：

```nginx
location /api/ {
    proxy_pass http://127.0.0.1:8000;
    proxy_http_version 1.1;
    proxy_set_header Connection '';
    proxy_buffering off;
    proxy_read_timeout 300s;
}
```

### 前端

```bash
cd client
npm run build
```

把 dist/ 交给 Nginx：

```nginx
root /var/www/ai-medical/client/dist;
location / {
    try_files $uri $uri/ /index.html;
}
```

### 必做安全项

1. `JWT_SECRET_KEY` 换成 32+ 位随机字符串：`python -c "import secrets; print(secrets.token_hex(32))"`
2. MySQL / Neo4j 密码全部改掉，不要用 123456
3. 数据库账号按最小权限原则拆分
4. 上传目录指向独立挂载点，并配置文件类型与大小白名单
5. 开启 HTTPS
6. CORS 允许的前端域名收紧到真实生产域名

## 常见问题

**Q: 启动时报 OPENAI_API_KEY is not set？**
A: 正常提示，表示没有配置大模型 Key。仅影响 AI 问诊 / 症状自查 / 向量化，注册登录等基础功能可用。

**Q: Neo4j 连接失败？**
A: 确认服务已启动、NEO4J_URI 端口正确（默认 7687），并已设置过密码。

**Q: 上传的知识文件没有生效？**
A: 检查 UPLOAD_DIR 是否有写权限，然后重新执行 `python scripts/init_knowledge.py`，或在管理端"知识库管理"里手动重建索引。

**Q: SSE 输出一段就断？**
A: 前置了 Nginx 时务必加 `proxy_buffering off;`，并调大 `proxy_read_timeout`。

## 许可

仅用于学习与毕业设计演示，不用于生产医疗诊断用途。
