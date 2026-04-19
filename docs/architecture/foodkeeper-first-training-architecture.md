# FoodKeeper 优先的食材识别训练仓库架构记录

## 1. 定位

本仓库的核心任务不是先训练出一个“看起来准确”的分类模型，而是先建立一套以 `foodkeeper.json` 为最高约束的训练标签系统。

训练标签必须首先服从 FoodKeeper 的保鲜建议边界，其次才考虑视觉可分性和数据可得性。

当前仓库只负责：

- 标签治理
- 数据映射
- manifest 生成
- `MobileNetV2` baseline 训练与评估

当前仓库不负责：

- 部署
- 提醒系统
- 库存时间逻辑
- 端侧原生微调

## 2. 第一性原理

这个项目最终不是单纯做“食物图片分类”，而是为未来“识别冰箱食材并结合保存时长给出建议”打基础。

因此一个合法训练类，不能只满足“图片上像一类”，还必须满足：

1. **FoodKeeper 一致性**
   - 这个类内部的食材在 `foodkeeper.json` 中对应的冷藏建议窗口足够接近
   - 不能把保鲜差异明显的食材硬合并
2. **视觉可识别性**
   - 这个类在冰箱摄像头场景中有稳定视觉边界
3. **训练可获得性**
   - 这个类能够从公开数据集或后续补充数据中获得足够样本

三者同时满足才是可发布训练类。

优先级严格为：

1. FoodKeeper 语义正确
2. 视觉可分
3. 数据可得

如果三者冲突，宁可暂不纳入当前训练主线，也不做错误合并。

## 3. 行业标准落地方式

按常见 CV / ML 数据治理流程，本仓库应分成 5 个事实层：

1. **Source of Truth**
   - `foodkeeper.json`
   - 公开数据集原始标签体系
2. **Taxonomy**
   - 仓库内部真正用于训练的标签体系
3. **Mapping**
   - FoodKeeper 条目到训练标签的约束映射
   - 数据集原始标签到训练标签或 `DROP` 的映射
4. **Manifest / Dataset Contract**
   - 统一训练样本清单和 split
5. **Training / Evaluation**
   - `MobileNetV2` 训练、评估和误差分析

顺序不能倒置。标签边界错误比训练不足更致命。

## 4. 仓库主线

仓库主线固定为：

1. 解析并审查 `foodkeeper.json`
2. 定义训练标签体系（taxonomy）
3. 建立 FoodKeeper 到 taxonomy 的约束映射
4. 建立公开数据集原始标签到 taxonomy / `DROP` 的映射
5. 生成 manifest / split
6. 跑 `MobileNetV2` baseline 训练
7. 做评估与误差分析，决定类保留、拆分或降级

## 5. 仓库结构

建议固定为以下分层：

- `docs/`
  - 架构说明、决策记录、数据同步说明
- `specs/`
  - taxonomy、FoodKeeper 映射、数据集映射、manifest schema
- `data/`
  - 轻量元数据、生成的 manifest、统计报告
- `scripts/`
  - 数据同步、校验、manifest 生成、训练、评估入口
- `src/`
  - dataset / transforms / model / train / eval 复用代码
- `artifacts/`
  - checkpoints、metrics、reports、label assets

原始公开数据不入库；仓库只保留同步方式、规则文件和生成产物。

## 6. 核心规格文件

需要明确的规格包括：

### 6.1 taxonomy spec

至少包含：

- `class_id`
- `class_name`
- `status`（`active` / `candidate`）
- `foodkeeper_consistency_note`
- `vision_rule`
- `data_feasibility_note`

### 6.2 FoodKeeper mapping spec

至少定义：

- `class_name -> one_or_more foodkeeper_product_id`

如果一个训练类映射多个 FoodKeeper 条目，必须记录：

- 为什么允许归并到同一训练类
- 它们的保鲜窗口为什么仍然可接受
- 未来做提醒时应采用什么保守策略

### 6.3 dataset mapping spec

至少定义：

- `dataset_name + source_label -> class_name | DROP`

每个 `DROP` 必须给出原因，例如：

- 语义不一致
- 视觉不稳定
- 数据太脏
- 没有对应 FoodKeeper 合理锚点

### 6.4 manifest schema

至少包含：

- `image_path`
- `source_dataset`
- `source_label`
- `mapped_label`
- `split`

## 7. 类别发布策略

类别发布采用 `candidate -> active` 双层机制。

### `candidate`

表示业务上可能合理，但当前存在以下至少一种问题：

- 视觉边界还不稳定
- 公开数据不足
- FoodKeeper 合并依据还不够扎实

### `active`

只有同时满足以下条件才能进入：

1. FoodKeeper 边界自洽
2. 视觉上可分
3. 数据上可训

默认规则：

- 只有 `active` 类进入 manifest、训练和评估
- `candidate` 类只进入规格和评审流程，不进入当前训练闭环
- 新类只能追加，不能重用旧 ID

## 8. 验证规则

至少要有以下校验：

- 每个 `active` 类必须至少锚定 1 个 FoodKeeper 条目
- 一个源标签不能映射到多个训练类
- manifest 中只能出现 `active` 类
- 类内如果存在明显不同保鲜窗口，必须拆类或降级为 `candidate`
- baseline 训练必须完成 smoke run
- 评估报告必须输出：
  - 每类样本量
  - `DROP` 覆盖率
  - confusion matrix

## 9. 当前默认项

- 训练主干固定为 **PyTorch + MobileNetV2**
- 原始公开数据不入库，README 需要提供一键同步方式
- 公开数据集只是训练资源，不决定标签边界
- 如果现有公开数据不够，可以后续补充新数据源，但不反过来迁就错误标签设计

## 10. 当前窗口的后续讨论重点

按当前共识，接下来优先讨论的不是训练细节，而是标签如何实现。建议按下面顺序推进：

1. 先从 `foodkeeper.json` 把候选食材簇整理出来
2. 判断哪些簇在保鲜窗口上可以成为单独训练类
3. 再判断这些类在视觉上是否稳定
4. 最后才检查 `GroceryStoreDataset` 与 `Freiburg Groceries` 能否支撑这些类

也就是说，标签从 FoodKeeper 出发定义，再去适配数据，而不是反过来由现有数据集决定。
