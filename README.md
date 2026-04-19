# eai

这个仓库已经清零，准备重新开始。

当前只保留这些确定的东西：
- `foodkeeper.json`
- 两个公开数据集名字：`GroceryStoreDataset`、`Freiburg Groceries`
- 后续训练主线固定为 `MobileNetV2`

这次清零后，旧的计划、旧的类目、旧的映射、旧的 manifest、旧的训练代码、旧的测试都不再继续沿用。

当前已经确认的新架构记录见：

- `docs/architecture/foodkeeper-first-training-architecture.md`
- `docs/labels/discovered-label-catalog.md`

当前 discovery / release 分层标签资产见：

- `specs/labels/discovered_label_catalog.json`
- `specs/labels/release_v1.json`
- `docs/labels/discovered-label-catalog.md`

## 公开数据集同步

当前训练主线使用两个公开数据集：

- `GroceryStoreDataset`
- `Freiburg Groceries`

数据默认同步到：

- `data/external_datasets/GroceryStoreDataset`
- `data/external_datasets/freiburg_groceries_dataset`

一键同步命令：

```bash
bash scripts/sync_public_datasets.sh
```

如果只想同步其中一个：

```bash
bash scripts/sync_public_datasets.sh grocery
bash scripts/sync_public_datasets.sh freiburg
```

脚本行为：

- `GroceryStoreDataset`：用 `git clone --depth 1` 拉取官方仓库
- `Freiburg Groceries`：先拉取官方仓库，再从官方公开地址下载 `images/` 到本地目录

同步完成后，可用下面的命令快速查看目录：

```bash
find data/external_datasets -maxdepth 2 -type d | sort
```
