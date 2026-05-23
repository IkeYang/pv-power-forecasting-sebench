# 多场站光伏功率多跨度预测

你需要构建一个多场站光伏功率预测系统。训练数据来自真实光伏场站运行观测，包含时间戳、气象变量、光照强度和真实功率；测试数据只包含特征，不包含真实功率。请改进当前代码，在隐藏评测集上尽可能准确地预测 `Power(mW)`。

公开训练数据位于 `dev-data/train/`，字段为 `LocationCode, DateTime, WindSpeed(m/s), Pressure(hpa), Temperature(°C), Humidity(%), Sunlight(Lux), Power(mW)`。公开开发测试特征为 `dev-data/dev_features.csv`，标签为 `dev-data/dev_labels.csv`，仅用于本地验证。最终评测会使用隐藏 `eval_features.csv`。

运行方式：

```bash
python train.py --train-dir dev-data/train --model-dir artifacts
python predict.py --input dev-data/dev_features.csv --output submission.csv --model-dir artifacts
```

输出文件必须包含 `LocationCode, DateTime, PredictedPower(mW)` 三列，行数、场站编号和时间戳必须与输入特征完全一致。预测值应为非负数，且不应明显超过场站可能容量。

评分会综合考察白天常规误差、峰值时段误差、快速爬坡/骤降时段误差、极端爬坡误差、光照突变时段误差、晨昏边界、低光照白天、场站容量归一化误差、场站平均偏差、逐日发电形状误差，以及隐藏时间尾部的短/中/长跨度误差。夜间大量零功率不会主导分数；普通单模型参考不会直接满分，容量归一化、太阳周期特征、站点校准、爬坡事件建模、逐日能量校准和长跨度后处理都可能带来持续提升。当前实现只是弱 baseline，你可以重写特征工程、模型训练、验证策略和预测后处理，但不要依赖外部网络或隐藏评测标签。
