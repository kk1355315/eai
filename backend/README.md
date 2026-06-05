# Backend

FastAPI 后端，负责水果识别结果入库、库存管理、保存状态、用户画像、购物提醒和 LLM 建议校验。

## 安装

```powershell
uv sync
Copy-Item .env.example .env
```

填写 `.env`：

```text
LLM_API_BASE=https://xplt.sdu.edu.cn:4000
LLM_API_KEY=replace-with-your-key
LLM_MODEL=Ali-dashscope/DeepSeek-V3.2
LLM_ENABLE_THINKING_DEFAULT=false
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,http://eai.744477.xyz,https://eai.744477.xyz
```

仓库不提交真实密钥。

## CORS

后端默认允许本地前端开发地址和线上域名跨域访问：

```text
http://localhost:5173
http://127.0.0.1:5173
http://eai.744477.xyz
https://eai.744477.xyz
```

如果域名或端口变了，在 `.env` 里修改 `CORS_ALLOWED_ORIGINS`。
多个地址用英文逗号分隔。

## 启动

```powershell
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## 主要接口

```text
GET    /health
GET    /foods
GET    /foods/{food_id}/storage
GET    /guideline-rules
GET    /nutrition-facts
GET    /profile
PATCH  /profile
POST   /recognitions
GET    /recognitions
GET    /images/{image_id}
GET    /inventory
PATCH  /inventory/{item_id}
POST   /inventory/{item_id}/confirm-change
GET    /inventory/storage-states
GET    /advice/today
GET    /advice/shopping
GET    /advice/evidence-search
POST   /advice/llm
POST   /advice/llm/validate
POST   /user-food-events
GET    /habits
```

## 测试

```powershell
uv run pytest -q
uv run python -m compileall app tests
```
