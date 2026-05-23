# 一阶段 Excel 字段：PV Forecasting

## 任务输入（背景资料【除文本外】）

本题提供一个可运行的多场站光伏功率预测代码仓，工作目录为 `pv-power-forecasting/agent-start`。数据来自真实光伏场站运行观测，已做确定性清洗和字段脱敏；Agent 可见输入材料包括：

1. `dev-data/train/`：公开训练数据，CSV 格式。每个文件对应一个光伏场站的历史观测序列，字段为 `LocationCode, DateTime, WindSpeed(m/s), Pressure(hpa), Temperature(°C), Humidity(%), Sunlight(Lux), Power(mW)`。其中 `Power(mW)` 是训练标签。

2. `dev-data/dev_features.csv`：公开开发集测试特征，CSV 格式，字段为 `LocationCode, DateTime, WindSpeed(m/s), Pressure(hpa), Temperature(°C), Humidity(%), Sunlight(Lux)`，不包含真实功率。

3. `dev-data/dev_labels.csv`：公开开发集标签，CSV 格式，字段为 `LocationCode, DateTime, Power(mW)`，用于 Agent 在本地验证模型迭代效果。

4. `dev-data/sample_submission.csv`：提交格式样例，字段为 `LocationCode, DateTime, PredictedPower(mW)`。

5. `README.md`：任务背景、输入输出格式、运行方式、约束条件和评分指标说明。

6. `train.py`、`predict.py`、`src/baseline.py`：可运行的初始预测框架。初始实现为弱 baseline，Agent 需要自行改进数据处理、特征工程、模型训练、验证策略和预测后处理。

隐藏评测材料不提供给 Agent，包括 `scorer/eval-data/eval_features.csv`、`scorer/eval-data/eval_labels.csv`、`scorer/eval-data/baseline_metrics.json` 和评分脚本内部使用的容量/归一化信息。

当前任务包规模：清洗后总数据 4,117,449 行；Agent 可见训练数据 3,311,762 行；公开开发集 326,138 行；隐藏评测集 479,549 行；共 51 个场站编号。数据准备阶段已对重复的 `LocationCode + DateTime` 记录做确定性清洗，包含文件内去重和全局键级去重。

## 评分方案

本任务采用全自动、确定性评分。Agent 需要在隐藏评测集上生成 `submission.csv`，评分脚本只读取该文件和隐藏标签，不读取 Agent 自报分数。分数范围为 0-100 分。

提交文件必须包含三列：`LocationCode, DateTime, PredictedPower(mW)`。行数、场站编号和时间戳必须与隐藏评测特征完全一致。若缺行、重复行、时间戳错位、列名错误、预测值非数值或程序运行失败，则返回 0 分。预测值为负数或明显超过场站容量上界会触发格式/物理约束惩罚。

综合误差由十四部分组成，重点避免夜间零值主导，并把预测跨度拉长后的长尾泛化、爬坡鲁棒性和场站级偏差纳入评分：

1. 白天常规 RMSE，占 20%。在 `Sunlight(Lux)>100` 或真实功率大于低阈值的样本上计算。
2. 快速爬坡/骤降 RMSE，占 12%。按同一场站相邻时刻真实功率变化量识别高变化率样本。
3. 极端爬坡/骤降 RMSE，占 8%。只评估变化量更靠前的尾部样本。
4. 峰值功率 RMSE，占 10%。在真实功率处于隐藏评测集高分位的样本上计算。
5. 晨昏边界 RMSE，占 6%。评估日出、日落附近太阳角度和低光照建模。
6. 低光照白天 RMSE，占 5%。评估阴天、云遮挡和弱辐照条件。
7. 光照突变 RMSE，占 6%。评估同一场站相邻时刻光照强度快速变化的样本。
8. 场站容量归一化 RMSE，占 7%。按场站容量代理值归一化后平均，防止只拟合大容量站点。
9. 场站平均偏差 MAE，占 4%。评估每个场站预测均值和真实均值的偏差，防止系统性高估或低估。
10. 逐日发电形状 RMSE，占 6%。按场站-日期聚合白天平均功率后计算误差，鼓励日尺度能量校准。
11. 短跨度隐藏尾部 RMSE，占 3%。每个评测场站隐藏尾部前 7 天。
12. 中跨度隐藏尾部 RMSE，占 4%。隐藏尾部第 8-28 天。
13. 长跨度隐藏尾部 RMSE，占 7%。隐藏尾部第 29 天以后。
14. 全局 MAE，占 2%。衡量整体平均绝对误差。

加权误差公式为：

`weighted_error = 0.20*day_rmse + 0.12*ramp_rmse + 0.08*extreme_ramp_rmse + 0.10*peak_rmse + 0.06*edge_rmse + 0.05*low_sun_rmse + 0.06*sunlight_transition_rmse + 0.07*station_norm_rmse + 0.04*station_bias_mae + 0.06*daily_energy_rmse + 0.03*horizon_short_rmse + 0.04*horizon_mid_rmse + 0.07*horizon_long_rmse + 0.02*mae`

最终分数采用多锚点分段归一化，而不是把普通参考模型或短时 HGB ensemble 直接设为高分；30 分以上留给显著优于短跑强模型的长跨度校准、爬坡专项建模、日尺度能量校准和模型融合：

- 初始弱 baseline 加权误差 `272.047485`，得分 `0.0`。
- 普通 HistGradientBoosting 参考模型加权误差 `166.461598`，得分 `2.0`。
- 容量归一化强参考模型加权误差 `150.603459`，得分 `5.0`。
- 真实 16min Agent 短跑 HGB ensemble 加权误差 `147.406850`，得分 `7.0`。
- 真实约 1h Agent 强 ensemble 加权误差 `129.706352`，得分 `15.0`。该锚点来自 2026-05-23 真实 Harness run，旧曲线下该提交曾达到 `30.822215`，因此用于防止短时自动优化过早越过验收上限。
- 2h 验收上界锚点加权误差 `112.000000`，得分 `30.0`。
- 专家目标满分线加权误差 `90.000000`，得分 `100.0`，用于给特征工程、模型集成、爬坡专门建模、日尺度能量校准和长跨度后处理保留上升空间。

分数截断到 0-100。格式错误/空白提交返回 `0.0`。

## 评分文件/脚本

评分入口为：

`pv-power-forecasting/scorer/score.sh`

用法：

`bash scorer/score.sh /path/to/agent-start`

评分相关文件：

```text
pv-power-forecasting/scorer/
  score.sh
  evaluate.py
  eval-data/
    eval_features.csv
    eval_labels.csv
    sample_submission.csv
    station_meta.json
    baseline_metrics.json
```

评分流程：

1. 进入 Agent 工作目录。
2. 若 `artifacts/model.json` 不存在，执行 `python train.py --train-dir dev-data/train --model-dir artifacts`。
3. 执行 `python predict.py --input scorer/eval-data/eval_features.csv --output submission.csv --model-dir artifacts` 生成隐藏评测预测。
4. 调用 `evaluate.py` 读取 `submission.csv`、`eval_features.csv`、`eval_labels.csv` 和 `baseline_metrics.json`。
5. 校验提交格式、行数、键一致性、重复行、缺失值、非数值、负功率和超容量预测。
6. 计算 `mae`、`day_rmse`、`ramp_rmse`、`extreme_ramp_rmse`、`peak_rmse`、`edge_rmse`、`low_sun_rmse`、`sunlight_transition_rmse`、`station_norm_rmse`、`station_bias_mae`、`daily_energy_rmse`、`horizon_short_rmse`、`horizon_mid_rmse`、`horizon_long_rmse`、`weighted_error` 和 `total_score`。
7. 输出 JSON 格式评分结果，包括 `valid`、`error`、`total_score`、`format_penalty`、各项误差、指标权重、归一化锚点和运行时间。

已跑通验证日志位于：

```text
pv-power-forecasting/baseline/blank-log.json
pv-power-forecasting/baseline/score-sh-baseline-log.json
pv-power-forecasting/baseline/reference-log.json
pv-power-forecasting/baseline/reference-score-log.json
```

验证结果：错误/空白提交 0 分；Agent 初始弱 baseline 0 分；普通 HGB 参考模型 2 分；容量归一化强参考模型约 5 分；真实 16min Agent 短跑强模型约 7 分；真实约 1h Agent 强模型约 15 分。评分过程不依赖外部网络，不需要 GPU。
