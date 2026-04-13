# CBLPRD 新图例预置区

此目录用于新一轮 YOLO 优化，和旧数据集隔离。

## 目录
- images/: 导入后的图像（已重命名）
- annotations/pending_labels.csv: 待标注清单
- annotations/import_mapping.csv: 源文件名与重命名映射
- annotations/template.csv: 标注模板（合法/非法 + 常见/特殊）
- yolo/: 训练前转换输出目录

## 合法/非法分类规则

- legal + common -> legal_common
- legal + special -> legal_special
- illegal -> illegal
- unknown/no_bbox -> unknown（不进入检测训练）

建议标注字段：
- legality: legal / illegal / unknown
- plate_type: common / special / illegal / unknown

## 开训前动作
1. 在 annotations/pending_labels.csv 中补齐 x,y,w,h（检测框）。
2. 按 template.csv 补 legality 与 plate_type。
3. 执行 prepare_yolo_legal_dataset 生成三分类检测数据集（同时导出 unknown_samples.csv）。
4. 用 plate_legal_data.yaml 启动 train_yolo.py。
