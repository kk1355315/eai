# Fruit YOLO11n Model

## 类别

```text
0 apple
1 banana
2 litchi
3 pear
```

## 文件

```text
weights/best.pt
weights/best.onnx
imx500_deploy/fruit.rpk
imx500_deploy/model_imx.onnx
imx500_deploy/labels.txt
```

## 训练

训练数据来自 Roboflow 重新拉取的数据集。

模型使用 YOLO11n。

训练运行目录：

```text
runs/yolo11n-redownload-e120-p20
```

训练过程设置为最多 120 epoch，实际因为 early stopping 在 107 个 epoch 结束。

## 验证集结果

按 `results.csv`：

| 指标 | 最佳值 |
| --- | ---: |
| best mAP@0.5 epoch | 64 |
| Precision | 0.92645 |
| Recall | 0.91481 |
| mAP@0.5 | 0.96312 |
| mAP@0.5:0.95 | 0.73260 |

按 mAP@0.5:0.95 最佳：

| 指标 | 数值 |
| --- | ---: |
| epoch | 86 |
| Precision | 0.93482 |
| Recall | 0.89593 |
| mAP@0.5 | 0.94789 |
| mAP@0.5:0.95 | 0.75821 |

## IMX500

`imx500_deploy/fruit.rpk` 是 AI Camera 部署文件。

`camera_test.log` 和 `still_test.log` 记录了 IMX500 固件加载过程。

日志里有：

```text
Network Firmware Upload: 100% (3120/3120 KB)
Still capture image received
```

说明模型包可以被 IMX500 流程加载。

还没有完成重新安装摄像头后的连续推流端到端测试。

