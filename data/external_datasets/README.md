# external_datasets

本目录用于存放仓库外部同步得到的公开数据集。

当前约定：

- `data/external_datasets/GroceryStoreDataset`
- `data/external_datasets/freiburg_groceries_dataset`

同步方式：

```bash
bash scripts/sync_public_datasets.sh
```

说明：

- 原始数据不纳入 git
- 本目录只保留说明文档，其余内容由同步脚本生成
