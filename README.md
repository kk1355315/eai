# EAI Fruit Keeper

这是一个面向 Demo 的水果识别入库与膳食建议后端项目。

系统由两部分组成：

- 视觉模型：YOLO11n，识别 `apple`、`banana`、`litchi`、`pear` 四类水果。
- 后端服务：FastAPI + SQLModel + SQLite，负责识别结果入库、库存管理、保存状态、购物提醒和 LLM 建议校验。

## 当前边界

系统不判断水果是否腐败。

系统不预测“坏的概率”。

系统不做医疗诊断。

保存期限只用于判断：

- `fresh`：可继续保存
- `eat_soon`：建议优先吃
- `check_required`：超过参考保存期，建议人工检查
- `not_recommended`：不进入推荐食用列表，只提示人工确认

营养依据只用于：

- 怎么吃
- 吃多少
- 是否符合用户目标
- 是否需要避免重复购买

## 目录

```text
backend/                  后端服务
models/fruit-yolo11n/     水果识别模型与 IMX500 部署文件
data/foodkeeper.json      FoodKeeper 原始参考数据
docs/                     计划、架构、测试说明
scripts/                  摄像头辅助脚本
```

## 后端运行

```powershell
cd backend
uv sync
Copy-Item .env.example .env
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

接口文档：

```text
http://127.0.0.1:8000/docs
```

测试：

```powershell
cd backend
uv run pytest -q
uv run python -m compileall app tests
```

当前本地验证结果：

```text
80 passed, 1 warning
compileall passed
```

`1 warning` 来自 FastAPI/TestClient 的第三方弃用提示，不是业务错误。

## 模型文件

```text
models/fruit-yolo11n/weights/best.pt
models/fruit-yolo11n/weights/best.onnx
models/fruit-yolo11n/imx500_deploy/fruit.rpk
models/fruit-yolo11n/imx500_deploy/model_imx.onnx
models/fruit-yolo11n/imx500_deploy/labels.txt
```

类别顺序：

```text
apple
banana
litchi
pear
```

## 真实联调状态

已完成：

- 后端自动化测试
- 后端 HTTP 烟测
- 真实 LLM 三类问答测试
- IMX500 模型文件打包
- IMX500 固件加载日志留存

未完成：

- 树莓派重新接摄像头后的连续推流端到端测试
- 前端页面联调
- 生产级登录、权限、HTTPS
