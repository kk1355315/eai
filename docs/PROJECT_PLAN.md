# 项目计划

## 目标

做一个 Demo 级水果库存与健康建议管理系统。

输入来自 AI Camera 的水果检测结果。

后端把水果种类、数量、位置、置信度和检测时间入库。

系统根据保存期限和用户画像生成保守建议。

LLM 只负责生成表达和组合建议，不能直接修改业务数据。

## MVP 范围

只支持四种水果：

| 标签 | 中文 | 用途 |
| --- | --- | --- |
| `apple` | 苹果 | 识别、库存、保存、建议 |
| `banana` | 香蕉 | 识别、库存、保存、建议 |
| `litchi` | 荔枝 | 识别、库存、保存、建议 |
| `pear` | 梨 | 识别、库存、保存、建议 |

## 核心闭环

```text
AI Camera 检测水果
-> POST /recognitions
-> 后端记录识别事件、检测框、图片证据
-> 库存进入 pending_confirm
-> 用户确认数量
-> 系统计算保存状态
-> 首页给出今日优先吃和需要检查
-> LLM 基于库存、保存、营养、膳食规则生成建议
-> 后端校验 LLM 输出
-> 合格建议入库
```

## 产品边界

系统不判断水果是否坏了。

系统不说“还能吃”或“不能吃”。

系统不做医疗诊断。

系统只提供库存管理、保存参考、饮食建议和购物提醒。

超过参考保存期的水果不进入“今日优先吃”。

超过参考保存期的水果只进入“需要检查”。

固定提示：

```text
已超过参考保存期，系统不推荐直接食用。请检查外观、气味和实际状态后再决定。
```

## 保存状态规则

FoodKeeper 如果给保存天数范围，MVP 默认取下限作为 `safe_days`。

这是保守建议。

```text
已存放天数 < 70% safe_days        -> fresh
70% safe_days ~ 100% safe_days    -> eat_soon
100% safe_days ~ 130% safe_days   -> check_required
超过 130% safe_days               -> not_recommended
```

字段：

```text
storage_state
days_stored
safe_days
remaining_days
eat_priority_rank
```

不使用：

```text
risk_score
risk_level
```

## 用户画像

字段：

```text
goal
diet_preference
cooking_condition
avoid_foods
allergies_optional
health_notes_optional
```

用户画像用于限制 LLM 建议。

如果用户声明避免某种水果、过敏或健康备注中要求避免，后端会拒绝冲突建议。

## LLM 规则

LLM 输出必须是结构化 JSON。

每条建议必须包含：

```text
title
content
action_type
related_foods
basis
evidence_ids
confidence
```

后端会校验：

- 证据 ID 必须存在
- 食物必须是四种水果之一
- 不允许推荐 `check_required` / `not_recommended` 水果去吃
- 不允许推荐用户避免或过敏的水果
- 不允许建议购买已有库存的水果
- 不允许使用腐败判断、医疗诊断、写数据库等表述

## 最小前端计划

MVP 前端只需要 4 页：

- 首页：今日优先吃、需要检查
- 库存页：当前水果、数量、保存状态、确认数量变化
- 建议页：LLM 饮食建议、购物提醒
- 个人信息页：目标、偏好、忌口、过敏、健康备注

当前仓库只实现后端。

