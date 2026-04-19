# Discovered Label Catalog

这份记录是当前“**先全记，再筛选**”的发现层资产。

它的目标不是直接定义 V1 最终训练集，而是把这次已经验证过的标签完整保留下来，避免下一次扩类时重新从 `foodkeeper.json` 和公开数据集再做一遍发现工作。

## 当前约束

- 单数据集支持即可
- 同语义类允许先合
- 只要 FoodKeeper 中存在可直接数值化的具体项，并且内部最大差值不超过 2 天，就可以作为一个发现层标签成立
- discovery 层和 release 层分离

## 资产文件

- `specs/labels/discovered_label_catalog.json`
  - 当前已发现标签总表
- `specs/labels/release_v1.json`
  - V1 发布层模板，当前故意留空，后面再筛

## 当前统计

- 唯一标签数：`48`
- 跨数据集共享标签：
  - `packaged_juice`
  - `packaged_dairy_milk`

## 设计说明

发现层记录的是：

- label 名称
- 数据来源
- FoodKeeper 锚点
- 使用的时间字段
- 归一化时间范围
- 内部最大差值
- 证据备注

发布层只回答：

- 这一版最终启用哪些 label

这样做的好处是：

- 发现工作只做一次
- V1 缩表不会污染总资产
- 下次扩类只需要从 catalog 中启用，或在 catalog 基础上继续新增
