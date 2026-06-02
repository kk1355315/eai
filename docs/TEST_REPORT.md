# 测试报告

## 自动化测试

本地最后一次完整结果：

```text
uv run pytest -q
80 passed, 1 warning
```

仍有 1 个依赖弃用 warning：`fastapi.testclient` 通过 Starlette `TestClient` 使用旧版 `httpx` 集成，提示后续安装 `httpx2`。

编译检查：

```text
uv run python -m compileall app tests
passed
```

## 覆盖场景

已覆盖：

- 4 种水果基础数据
- FoodKeeper 保存规则
- `safe_days` 保守取值
- `fresh / eat_soon / check_required / not_recommended`
- 今日优先吃
- 需要检查列表
- 防重复购买
- 识别结果入库
- 检测框入库
- 图片证据入库
- AI Camera 缺图拒绝
- 低置信度、未知类别、包装类待确认
- 数量增加、减少、待确认
- 用户食用、丢弃、购买事件
- 消耗/丢弃数量不能超过库存
- 用户习惯形成阈值
- 用户画像影响 LLM 校验
- LLM evidence_ids 校验
- LLM 禁止医疗和腐败判断
- LLM 禁止购买已有库存
- LLM 文本提到需检查/不推荐水果时禁止推荐食用
- LLM basis 提到需检查水果和食用建议时禁止推荐食用
- 英文 `buy / purchase / restock` 购买意图拦截
- 英文 `eat / breakfast / snack / serving / use as / with yogurt` 食用意图拦截

## 真实测试

已完成：

- 后端 HTTP 服务烟测
- 真实 LLM 问答测试
- IMX500 模型包加载日志检查

真实 LLM 通过的问题类型：

- 今天吃什么
- 控糖怎么吃
- 哪些不用买

未完成：

- 树莓派摄像头重新安装后的连续推流端到端测试
- 长时间运行稳定性测试
- 前端联调

## 测试残留

发布仓库不包含：

- `.env`
- `.venv`
- `fruit_health.db`
- `test_fruit_health.db`
- `http_smoke.db`
- pytest 缓存
