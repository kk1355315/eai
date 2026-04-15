# Ingredient-First Classifier V1 Plan

## 目标

把这个仓库从“一个大概的食物分类训练框架”改成：

- 专门给 AI 冰箱 V1 服务
- 第一版只做食材
- 每个模型类别最后都能落到 `foodkeeper.json` 里的真实条目

这份计划只管图像识别这一层，不管提醒文案和时间记录代码。

## 当前状态

现在仓库里已经有：

- 基础目录结构
- 一个旧的 V1 训练计划
- 一份 `v1_labels.csv`
- 两份很早期的公开数据映射

但现在还不能训练，原因很直接：

- `public_stage_a.csv` 是空的
- `target_stage_b.csv` 是空的
- `grocery_to_v1.csv` 只接了很少几个类
- `chinesefoodnet_to_v1.csv` 只接了少量熟食类
- 当前分类混了食材和熟食，不符合新的 V1 目标

## 第一版到底识别什么

第一版只做食材，不做熟食。

建议 V1 食材类如下：

- `apple`
- `banana`
- `citrus_fruit`
- `berries`
- `tomato`
- `cucumber`
- `leafy_greens`
- `carrot`
- `onion`
- `mushroom`
- `broccoli`
- `pepper`
- `potato`
- `egg`
- `milk`
- `yogurt`
- `tofu`
- `cheese`
- `raw_meat`
- `raw_poultry`
- `fish`
- `shrimp`

这批类的规则是：

- 明显长得不一样的，单独成类
- 肉类不细分牛肉猪肉，但要区分 `肉 / 禽 / 鱼 / 虾`
- 包装里的基础食材也算第一版范围，比如牛奶、酸奶、奶酪

## 这些类怎么落到 FoodKeeper

模型类不是直接照抄 `foodkeeper.json`。

正确做法是：

- 先定义模型类
- 再给每个模型类挂一个或多个 FoodKeeper 真实条目
- 如果对应多个条目，就取最保守的安全建议

第一轮映射建议：

- `apple` -> `Apples`
- `banana` -> `Bananas`
- `citrus_fruit` -> `Citrus fruit`
- `berries` -> `Berries` / `Blueberries` / `Strawberries` / `Raspberries`
- `tomato` -> `Tomatoes`
- `cucumber` -> `Cucumbers`
- `leafy_greens` -> `Lettuce` / `Bagged greens`
- `carrot` -> `Carrots, parsnips` / `Baby carrots`
- `onion` -> `Onions`
- `mushroom` -> `Mushrooms`
- `broccoli` -> `Broccoli and broccoli raab`
- `pepper` -> `Peppers` / `Hot peppers`
- `potato` -> `Potatoes` / `Yams/sweet potatoes`
- `egg` -> `Eggs | in shell`
- `milk` -> `Milk | plain or flavored`
- `yogurt` -> `Yogurt`
- `tofu` -> `Tofu`
- `cheese` -> `Cheese` 相关条目
- `raw_meat` -> `Beef` / `Pork`
- `raw_poultry` -> `Chicken`
- `fish` -> `Lean fish` / `Fatty fish`
- `shrimp` -> `Shrimp, crayfish` / `Shrimp, shellfish`

后续在标签表里要明确存这个映射，不要只靠口头约定。

## 公开数据集怎么用

### 这次补上的数据集

已经下载到本地：

- `data/external_datasets/GroceryStoreDataset`
- `data/external_datasets/freiburg_groceries_dataset`

说明：

- `GroceryStoreDataset` 已经自带图片目录
- `Freiburg Groceries` 已经执行了官方下载脚本，图片目录已展开到 `images/`

### V1 主数据源

V1 公开数据预训练只用：

- `GroceryStoreDataset`
- `Freiburg Groceries`

### 从主计划中移除

`ChineseFoodNet` 不再作为 V1 主训练数据源。

原因不是它不好，而是：

- 它偏熟食
- 现在的 V1 明确不做熟食

后面如果做 V2 熟食版，再单独拉回来。

## 数据和文档要改什么

### 1. 标签表

`docs/taxonomy/v1_labels.csv` 要改成纯食材版本，并新增至少这些字段：

- `class_id`
- `class_name`
- `class_group`
- `status`
- `foodkeeper_targets`
- `notes`

其中 `foodkeeper_targets` 用来存真实条目映射。

### 2. 映射表

要补三类映射文档：

- `grocery_to_v1.csv`
- `freiburg_to_v1.csv`
- `foodkeeper_target_map.csv` 或等价文档

其中：

- 前两个负责“公开数据标签 -> 模型类”
- 最后一个负责“模型类 -> FoodKeeper 真实条目”

### 3. Manifest

`data/manifests/public_stage_a.csv` 要真正填起来。

来源至少包括：

- GroceryStoreDataset
- Freiburg Groceries

`data/manifests/target_stage_b.csv` 继续保留，但 V1 明确要求后续补真实冰箱图。

## 训练路线

### Stage A

目的：

- 用公开数据先让模型学会基本食材外观

输入：

- `GroceryStoreDataset`
- `Freiburg Groceries`

### Stage B

目的：

- 用你们自己拍的真实冰箱图片微调

必须强调：

- 没有 Stage B，模型就不能说已经适合冰箱落地

## 执行顺序

这份计划后续真正实施时，按下面顺序做：

1. 重写 `v1_labels.csv`
2. 建立 `FoodKeeper` 映射表
3. 盘点 `GroceryStoreDataset` 可用类
4. 盘点 `Freiburg` 可用类
5. 写 `grocery_to_v1.csv`
6. 写 `freiburg_to_v1.csv`
7. 生成 `public_stage_a.csv`
8. 再开始训练

不要先急着训练。

如果映射没定好，训练出来也没法稳定接到安全建议库。

## 这版计划的验收标准

执行到位以后，至少要看到这些结果：

- 本地已有两个公开数据集
- V1 类只剩食材，没有熟食
- 每个 V1 类都能找到 FoodKeeper 对应条目
- `public_stage_a.csv` 不再为空
- 新训练计划只围绕“食材识别 -> FoodKeeper 映射”展开
