# 前端与后端完善项目计划书

## 目标

在现有 FastAPI 后端基础上，补齐 Demo 级前端应用。

前端优先完成移动端体验，视觉参考当前三张 UI 图：浅蓝白背景、玻璃拟态卡片、大标题、底部三栏导航。

业务实现必须以当前后端 MVP 为准：只支持 `apple`、`banana`、`litchi`、`pear` 四种水果。

整体视觉与风格审查以 `docs/UI_STYLE_GUIDE.md` 为准，避免出现典型 AI 产品页样式。

## 范围边界

### 必须做

- 首页：展示今日优先吃、需要检查、Ask AI 入口。
- 库存页：展示四种水果库存、数量、保存状态、剩余天数、数量确认。
- 建议页：展示购物建议、LLM 饮食建议、LLM 校验错误与兜底建议。
- 个人信息页：展示和编辑用户画像字段。
- API 联调：接入库存、建议、个人画像、用户食物事件等接口。
- 基础状态：loading、error、empty、retry。
- 移动端适配：优先保证 375px 到 430px 宽度体验，桌面居中展示。

### 暂不做

- 登录、注册、权限。
- 草莓、牛奶、肉类、鸡蛋、蔬菜等全品类库存。
- 后端没有字段的姓名、邮箱、头像上传、家庭人数、提醒设置。
- 医疗诊断、腐败判断、自动判断“还能不能吃”。
- 生产级部署、HTTPS、账号体系。

## 技术方案

### 前端技术栈

建议新建目录：

```text
frontend/
```

技术选择：

| 方向 | 方案 | 原因 |
| --- | --- | --- |
| 应用框架 | React + Vite + TypeScript | 快速搭建 Demo，类型约束 API 字段 |
| 路由 | react-router-dom | 对应 Home、Inventory、Advice、Profile |
| 请求状态 | @tanstack/react-query | 统一 loading、error、refetch、mutation invalidation |
| 样式 | CSS Modules + CSS variables | 便于复刻玻璃卡片、阴影和主题 token |
| 图标 | lucide-react | Home、Package、User、Sparkles、ChevronRight 等图标齐全 |
| 测试 | Vitest + React Testing Library | 覆盖 mapper、空态、错误态和关键交互 |

### 本地联调策略

开发阶段优先使用 Vite proxy，减少后端改动。

前端请求：

```text
/api/inventory
/api/advice/today
/api/profile
```

Vite proxy 转发到：

```text
http://127.0.0.1:8000
```

后续如果前端和后端部署到不同域名，再在 `backend/app/main.py` 增加 CORS 白名单。

## 页面与路由

```text
/            HomePage
/inventory   InventoryPage
/advice      AdvicePage
/profile     ProfilePage
```

底部导航保持三栏：

```text
Home / Inventory / Profile
```

`Advice` 不放入底部主导航，从首页 `Ask AI` 卡片进入。这样保留参考图的三栏结构，同时满足 MVP 的建议页需求。

## 信息架构

### 首页

接口：

- `GET /advice/today`
- 兜底读取 `GET /inventory`

内容：

- 顶部标题：`Today`，副标题：`Eat smarter`
- 今日推荐水果：从 `today_priority` 取第一项
- Priority：展示优先吃列表
- Need Check：展示 `check_required` 和 `not_recommended`
- Ask AI：进入 `/advice`
- 待确认提示：统计 `status === "pending_confirm"` 或 `pending_change_type !== "none"` 的库存项

注意：

- 不展示草莓、牛奶、三文鱼、鸡蛋等非 MVP 数据。
- `check_required` 和 `not_recommended` 不能进入推荐食用列表，只能进入检查提示。

### 库存页

接口：

- `GET /inventory`
- `PATCH /inventory/{item_id}`
- `POST /inventory/{item_id}/confirm-change`
- `POST /user-food-events`

内容：

- 顶部标题：`Inventory`
- 统计卡：
  - Total：`sum(confirmed_quantity)`
  - Fresh：`storage_state === "fresh"` 的数量
  - Check：`eat_soon + check_required + not_recommended` 的数量
- 四种水果列表：
  - 水果图片或占位
  - 中文名
  - 确认数量
  - 保存位置
  - 剩余天数
  - 保存状态 badge
  - 进度条
- 待确认弹层：
  - 支持确认新数量
  - 支持 `possible_added` 作为新批次
  - 支持取消或标记为 `available`
- 快捷事件：
  - consumed
  - discarded
  - purchased

注意：

- `InventoryResponse.food` 是嵌套对象，包含 `id`、`model_label`、`display_name`。
- `pending_change_type` 可能是 `none`、`new_quantity`、`possible_added`、`possible_consumed`。

### 建议页

接口：

- `GET /advice/shopping`
- `POST /advice/llm`

内容：

- 购物提醒：展示不要重复购买、需要补买等建议。
- Ask AI 输入框：
  - 请求体：`{ question?, enable_thinking?, search_query? }`
  - 返回：`{ accepted, errors, advice, record_id }`
- LLM 建议列表：
  - `summary`
  - `recommendations`
  - `errors`
  - evidence ids

注意：

- 普通用户 Ask AI 使用 `/advice/llm`，不是 `/advice/llm/validate`。
- 如果没有配置 LLM key，后端可能返回 `accepted: false` 和 fallback advice，前端必须正常展示。

### 个人信息页

接口：

- `GET /profile`
- `PATCH /profile`

真实字段：

```text
goal
diet_preference
cooking_condition
avoid_foods
allergies_optional
health_notes_optional
```

内容：

- 顶部仍保留 Profile 视觉风格，但账户资料用静态占位。
- 主要交互是用户画像表单：
  - 健康目标
  - 饮食偏好
  - 烹饪条件
  - 忌口水果
  - 过敏备注
  - 健康备注

注意：

- 后端没有姓名、邮箱、头像、家庭人数、提醒设置字段。
- `goal`、`diet_preference`、`cooking_condition` 不能 PATCH 为 `null`。

## 数据类型重点

前端类型必须按后端真实字段建立。

### Inventory

```text
storage_location: pantry | refrigerate | freeze
status: pending_confirm | available | consumed | discarded | unknown
storage_state: fresh | eat_soon | check_required | not_recommended | null
pending_change_type: none | new_quantity | possible_added | possible_consumed
```

关键字段：

```text
id
food.model_label
food.display_name
detected_quantity
confirmed_quantity
unit
days_stored
safe_days
remaining_days
eat_priority_rank
message
```

### Advice

建议条目字段：

```text
title
content
action_type
related_foods
basis
evidence_ids
confidence
```

`/advice/today` 中的 `today_priority` 和 `check_required` 是 `dict` 列表，实施前需要从 OpenAPI 或接口响应中确认具体 shape。

### Profile

`avoid_foods` 是字符串数组，其余画像字段多为字符串或可空字符串。

## 组件规划

优先保留少量稳定组件，避免过早抽象。

```text
src/components/layout/AppShell.tsx
src/components/layout/BottomNav.tsx
src/components/ui/GlassCard.tsx
src/components/ui/StatusBadge.tsx
src/components/ui/FruitAvatar.tsx
src/components/ui/LoadingCard.tsx
src/components/ui/ErrorCard.tsx
src/components/home/RecommendedFruitCard.tsx
src/components/home/AskAiCard.tsx
src/components/inventory/InventoryItemRow.tsx
src/components/inventory/ConfirmChangeSheet.tsx
src/components/advice/AdviceCard.tsx
src/components/advice/AskAiPanel.tsx
src/components/profile/ProfileForm.tsx
```

API 和业务映射：

```text
src/api/client.ts
src/api/types.ts
src/api/inventory.ts
src/api/advice.ts
src/api/profile.ts
src/api/userEvents.ts
src/lib/mappers.ts
src/lib/status.ts
```

## 视觉规范

### 布局

- 移动优先。
- 页面最大宽度建议 `430px` 到 `520px`。
- 桌面居中显示，不改成复杂后台 dashboard。
- 底部导航固定在应用容器底部，内容区预留底部安全距离。

### 色彩

```text
primary: #2584ff
text: #07152f
muted: #697895
panel: rgba(255, 255, 255, 0.72)
fresh: #3fb950
eat_soon: #ff8a00
check_required: #ef4444
not_recommended: #8b5e63
```

### 卡片

- 半透明白色背景。
- 细白边。
- 蓝灰色柔和阴影。
- 圆角可接近参考图，但需要适配小屏。
- 卡片内文字不使用 viewport 字号。

### 图片资产

优先使用本地四种水果资产：

```text
src/assets/foods/apple.webp
src/assets/foods/banana.webp
src/assets/foods/litchi.webp
src/assets/foods/pear.webp
```

如果暂时没有图片，先实现 `FruitAvatar`：

- 用水果首字母或简化图标。
- 使用不同背景色区分四种水果。
- 后续再替换为统一风格图片。

## 后端完善项

### 必做配套

- 确认 `/openapi.json` 可正常访问，用于前端核对类型。
- 保持当前 `/inventory`、`/advice/*`、`/profile`、`/user-food-events` API 稳定。
- 为前端补充接口示例响应到文档或测试 fixture。
- 确认种子数据可以提供四种水果和默认用户画像。

### 可选增强

- 如果不用 Vite proxy，则在 `backend/app/main.py` 增加 CORS 白名单。
- 增加前端需要的 profile 展示字段时，应同步修改后端模型、迁移、API 和计划范围。
- 增加 `/frontend-demo-seed` 或脚本，快速生成库存、待确认、过期检查等演示数据。
- 增加接口字段说明文档，特别是 `/advice/today` 的 `dict` 响应结构。

## 里程碑

### 阶段 1：前端骨架

输出：

- `frontend/package.json`
- `frontend/vite.config.ts`
- `frontend/src/main.tsx`
- `frontend/src/App.tsx`
- `frontend/src/routes/*`
- `frontend/src/styles/*`

验收：

- 四个路由可打开。
- 底部导航可切换。
- 页面视觉基调接近参考图。
- `npm run build` 通过。

### 阶段 2：API client 与类型

输出：

- `src/api/*`
- `src/lib/mappers.ts`
- `src/lib/status.ts`
- React Query hooks

验收：

- 能请求 `/inventory`、`/advice/today`、`/profile`。
- 后端未启动时显示错误卡片和重试按钮。
- mapper 单测覆盖关键状态。

### 阶段 3：首页与库存只读

输出：

- Home 推荐卡
- Priority 列表
- Need Check 列表
- Inventory 统计
- 四水果库存列表

验收：

- 只展示四种水果。
- `check_required` 和 `not_recommended` 不进入推荐食用列表。
- 空库存有清晰空态。
- 移动端不溢出。

### 阶段 4：库存闭环

输出：

- 待确认弹层
- 数量确认
- 修改保存位置
- consumed、discarded、purchased 事件
- mutation 后自动刷新

验收：

- `pending_confirm` 可确认成 `available`。
- `possible_added` 可作为新批次处理。
- 吃掉或丢弃后库存状态刷新。

### 阶段 5：建议页与 Ask AI

输出：

- 购物建议卡片
- Ask AI 表单
- LLM 建议列表
- errors 和 fallback 展示

验收：

- `/advice/shopping` 可展示。
- `/advice/llm` 请求成功或失败都能展示结果。
- `accepted=false` 时用户能看到原因。

### 阶段 6：个人画像

输出：

- Profile 表单
- PATCH 保存
- 表单校验

验收：

- 用户画像可读取、编辑、保存。
- 必填字段不提交 null。
- 忌口水果可影响后续建议校验。

### 阶段 7：联调与打磨

输出：

- README 前端启动说明
- 截图验收记录
- build/typecheck/test 结果

验收：

- 后端 `uv run uvicorn app.main:app --host 127.0.0.1 --port 8000`。
- 前端 dev server 可联调。
- `npm run typecheck` 通过。
- `npm run build` 通过。
- 375px、430px、桌面居中三种视口视觉正常。

## 风险与应对

| 风险 | 影响 | 应对 |
| --- | --- | --- |
| UI 图和后端能力不一致 | 前端可能展示假数据 | 只复刻视觉，不扩展真实品类 |
| `/advice/today` 使用 dict 响应 | 手写类型容易错 | 实施前查看 OpenAPI 或真实响应 |
| LLM key 缺失 | Ask AI 可能返回 fallback | UI 必须展示 errors 和 accepted 状态 |
| 没有水果图片资产 | 页面不够像参考图 | 先做 FruitAvatar，后续替换本地 WebP |
| CORS 问题 | 浏览器无法访问后端 | 开发阶段用 Vite proxy |
| Profile 字段不足 | 参考图无法完整复刻 | Profile 改为用户画像页 |

## 最终交付标准

- 前端可以独立启动。
- 首页、库存、建议、个人画像四个页面可用。
- 主流程覆盖：识别入库后的确认、库存状态展示、今日建议、Ask AI、画像编辑。
- 视觉风格接近参考图，但数据和交互严格符合后端 MVP 边界。
- 构建、类型检查、关键测试通过。
