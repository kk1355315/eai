# UI 风格调控规范

## 目标

本规范用于约束前端整体视觉风格，确保页面严格贴近现有三张 UI 参考图。

前端可以使用 AI 能力作为业务功能，但界面不能呈现“AI 产品模板感”。页面必须像一个轻量、精致、生活化的食材库存 App，而不是聊天机器人、数据大屏、SaaS 控制台或营销落地页。

参考图位于工作区根目录：

```text
c44a80babda7e41b29feca705da4bf42.png          Home
e688cdca500af924d291f36b61bee63d.png          Inventory
f55ba4840a514fe57320a9fb00239a3f_720.png      Profile
```

## 一句话风格

浅蓝白背景、柔和玻璃卡片、真实食材视觉、大字号标题、克制图标、移动端优先。

## 必须坚持

- 页面第一眼必须接近参考图的移动端 App，不做网页营销页。
- 视觉重心是食材库存和生活管理，不是 AI 助手。
- 所有页面都使用同一套浅蓝白空间、白色玻璃卡片、蓝灰阴影和底部三栏导航。
- 内容必须以真实后端 MVP 四种水果为准：`apple`、`banana`、`litchi`、`pear`。
- AI 入口只能作为一个功能卡片或建议页能力出现，不能抢占首页主体。
- 页面必须安静、清爽、可扫描，不使用夸张动效和装饰。

## 严禁出现

### AI 典型前端样式

- 紫蓝渐变大面积背景。
- 发光球、渐变光斑、bokeh、粒子背景。
- 黑色科技风、赛博风、霓虹边框。
- 机器人、芯片、大脑、电路、宇宙星云类插画。
- 大号聊天输入框占据首页中心。
- `Ask anything`、`Powered by AI` 等 AI 产品模板文案作为主视觉。
- 复杂 Prompt 面板、模型选择器、token 统计、对话历史侧栏。
- SaaS 仪表盘式布局、数据大屏式卡片堆叠。
- 营销落地页 hero，包括左右分栏 hero、夸张 slogan、CTA 按钮组。

### 和参考 UI 冲突的样式

- 深色模式作为默认视觉。
- 高饱和背景或纯白硬边卡片。
- 圆角过小的企业后台卡片。
- 大面积单一蓝紫色主题。
- 过多边框线、表格线、分隔线。
- 强烈投影、硬阴影、外发光。
- 字号随视口宽度缩放。
- 页面宽度铺满桌面。
- 复杂顶部导航或侧边栏。

## 布局规范

### 应用容器

- 移动端优先，主容器宽度贴近手机 App。
- 推荐最大宽度：`430px` 到 `520px`。
- 桌面端只做居中展示，不改造成 dashboard。
- 页面背景铺满视口，App 内容在中间自然下落。
- 内容区必须给底部导航留出安全距离。

### 页面结构

每个主页面遵循：

```text
大标题
简短副标题或无副标题
核心内容卡片
次级内容卡片
底部导航
```

不能在首屏加入解释型说明区。用户打开页面应直接看到功能内容。

### 间距

- 页面左右边距保持宽松，但小屏不能挤压内容。
- 卡片之间保持明显呼吸感。
- 卡片内部元素使用稳定间距，避免密集堆叠。
- 底部导航与最后一张卡片之间必须留出距离。

## 色彩规范

### 主色

```text
primary: #2584ff
text: #07152f
muted: #697895
soft-muted: #8a98b3
panel: rgba(255, 255, 255, 0.72)
panel-strong: rgba(255, 255, 255, 0.86)
line: rgba(143, 164, 194, 0.22)
background-top: #f8fbff
background-bottom: #eaf4ff
```

### 状态色

```text
fresh: #42bd4d
eat_soon: #ff8a00
check_required: #ef4444
not_recommended: #8b5e63
inactive: #6d7c98
```

### 使用原则

- 蓝色只用于主操作、选中导航、重点文字和 AI 入口小图标。
- 绿色、橙色、红色只用于库存状态。
- 背景必须是轻柔蓝白，不使用强渐变。
- 不允许紫色成为主视觉。

## 背景规范

背景应模拟参考图的柔和浅蓝白空间。

允许：

- 极轻的线性渐变。
- 极轻的径向提亮。
- 细腻、低对比的蓝白层次。

不允许：

- 可见的装饰光球。
- 大面积彩色渐变。
- 暗色背景。
- 科技纹理、网格、电路线。

推荐方向：

```css
background:
  radial-gradient(circle at 50% 0%, rgba(255, 255, 255, 0.95), rgba(255, 255, 255, 0) 34%),
  linear-gradient(180deg, #f8fbff 0%, #edf6ff 52%, #eaf4ff 100%);
```

## 卡片规范

### 玻璃卡片

卡片是整个 UI 的核心。

要求：

- 白色半透明背景。
- 细白边或低对比蓝灰边。
- 圆角偏大，但不能影响小屏内容排布。
- 阴影柔和、浅蓝灰、扩散大。
- 卡片内部不能再套装饰性卡片。

推荐值：

```text
border-radius: 28px 到 36px
background: rgba(255, 255, 255, 0.72)
border: 1px solid rgba(255, 255, 255, 0.78)
box-shadow: 0 22px 60px rgba(74, 103, 139, 0.14)
```

### 列表项卡片

- 列表项可使用更小圆角。
- 内容应一眼扫到：图片、名称、数量或状态、箭头。
- 不使用表格样式。
- 分隔线必须非常浅。

## 字体规范

### 字体

使用系统字体：

```text
-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif
```

### 字号层级

```text
页面标题: 48px 左右，小屏可降到 42px
卡片标题: 24px 到 30px
重点名称: 30px 到 38px
正文: 16px 到 20px
辅助文字: 14px 到 17px
底部导航: 13px 到 15px
```

### 规则

- 不使用 `vw` 控制字体。
- 不使用负字距。
- 页面标题必须厚重但干净。
- 卡片内标题不能过大，避免挤压内容。
- 中文和英文混排时保持行高舒适。

## 图标规范

使用线性图标，优先 `lucide-react`。

允许：

- Home
- Package
- User
- Sparkles
- ChevronRight
- Leaf
- ShieldPlus
- Bell
- Users
- CircleGauge

规则：

- 图标线宽统一。
- 未选中图标使用蓝灰色。
- 选中图标使用主蓝色。
- 不手绘复杂 SVG 插画。
- 不使用机器人、芯片、电路、大脑图标作为主视觉。

## 图片资产规范

### 食材图片

真实食材图是参考 UI 的重要部分。

优先准备四张本地资产：

```text
frontend/src/assets/foods/apple.webp
frontend/src/assets/foods/banana.webp
frontend/src/assets/foods/litchi.webp
frontend/src/assets/foods/pear.webp
```

图片要求：

- 背景干净。
- 光线柔和。
- 视角接近产品图。
- 不使用暗色、模糊、裁切过度的图片。
- 四张图风格尽量一致。

### 占位策略

如果暂时没有图片，使用 `FruitAvatar`。

`FruitAvatar` 必须：

- 形状柔和。
- 背景浅色。
- 使用水果首字母或简化图标。
- 不使用 emoji 作为正式资产。

## 页面级规范

### Home

必须像参考图第一张。

保留：

- 大标题 `Today`。
- 副标题 `Eat smarter`。
- 大推荐卡。
- Priority 小列表。
- Need Check 或 Expiring Soon 区域。
- Ask AI 功能入口。
- 底部三栏导航。

调整：

- 推荐内容替换为四种水果。
- 不出现 Strawberries、Milk、Salmon、Eggs 等非 MVP 数据。
- Ask AI 是一张功能卡，不是聊天首页。

### Inventory

必须像参考图第二张。

保留：

- 大标题 `Inventory`。
- 顶部统计卡。
- 纵向库存列表。
- 每行左侧食材图、中间名称和数量、右侧状态和箭头。
- 底部导航。

调整：

- 列表不做 Vegetables、Fruits、Dairy、Meat、Seafood 分类。
- 改为 Apple、Banana、Litchi、Pear 或真实库存批次。
- 状态来自 `storage_state`，不是静态文案。

### Profile

必须像参考图第三张的空间感，但内容按后端字段重写。

保留：

- 大标题 `Profile`。
- 大卡片。
- 图标 + 文案 + 右箭头的行结构。
- 标签 pill。
- 底部导航。

调整：

- 不做真实姓名、邮箱、头像上传。
- 不做 Household 和 Reminders 的真实功能。
- 改为用户画像：目标、偏好、烹饪条件、忌口、过敏、健康备注。

### Advice

Advice 没有参考图，必须从 Home 的 Ask AI 卡片风格延展。

要求：

- 仍使用浅蓝白背景和玻璃卡片。
- 顶部标题可以是 `Advice` 或 `Ask AI`。
- AI 输入区不能做成全屏 ChatGPT 复制品。
- 建议结果以卡片列表展示。
- `accepted=false` 和 `errors` 必须有安静但清楚的提示。

## 交互动效

允许：

- 轻微按钮按压。
- 卡片 hover 在桌面端轻微上浮。
- 弹层轻微滑入。
- loading skeleton。

不允许：

- 粒子动画。
- 大面积背景动效。
- 打字机效果作为主要表达。
- 夸张弹跳。
- 连续闪烁或发光。

## 文案规范

文案要像生活工具，不像 AI 营销页。

允许：

```text
Today
Eat smarter
Priority
Need Check
Ask AI
Get personalized advice
Inventory
Profile
```

避免：

```text
AI-powered intelligence
Unlock the future of food
Your autonomous nutrition copilot
Ask anything, anytime
Revolutionary AI assistant
```

中文文案要直接、短、安静。

## 实施审查清单

每次提交前检查：

- 是否仍像三张参考 UI，而不是 AI 模板页。
- 是否没有紫蓝大渐变、光球、机器人、芯片、电路视觉。
- 是否没有非 MVP 食材作为真实业务数据。
- 是否保持三栏底部导航。
- 是否移动端优先，桌面只居中展示。
- 是否卡片、阴影、圆角、字号统一。
- 是否使用真实后端字段，不展示不存在的功能。
- 是否 Ask AI 只是功能入口和建议页能力，没有抢占首页。
- 是否 375px 宽度无文字重叠、按钮溢出、导航挤压。

## 最终验收标准

通过验收的界面应满足：

- 截图第一眼能对应 Home、Inventory、Profile 三张参考图。
- 色彩安静、明亮、生活化。
- 没有典型 AI 产品页视觉套路。
- 数据严格来自四水果 MVP。
- Advice 页面虽有 AI 功能，但仍属于同一套食材库存 App。
- 任何新增页面都能复用同一套空间、卡片、字体、图标和状态语言。
