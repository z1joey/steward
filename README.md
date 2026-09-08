# Steward·司舵

多门店人·财·事工作台（MVP）。Vue 3 SPA + FastAPI + Postgres。

## 启动（Docker）

```bash
cp .env.example .env
docker compose up --build
# 前端 http://localhost:8080 · 后端 http://localhost:8000/health
```

## 本地开发

```bash
# 1. 数据库（任选其一）
docker compose up -d db
#   或本机 Postgres：createdb steward

# 2. 后端（uv）
cd backend
uv sync
cp ../.env.example ../.env   # 按需修改连接串
uv run alembic upgrade head
uv run uvicorn app.main:app --reload   # http://localhost:8000/health

# 3. 前端
cd frontend
npm install
npm run dev                  # http://localhost:5173（/api 代理到 8000）
```

## 测试

```bash
# 后端 API 测试：需要可用的 Postgres，创建测试库后运行
createdb steward_test
cd backend
STEWARDS_DATABASE_URL=postgresql+psycopg://localhost/steward_test uv run pytest
```

## 目录

见 `PROJECT.md` 与 `docs/plan/B-specs.md` §0.1（`frontend/` · `backend/` · `docker-compose.yml`）。
