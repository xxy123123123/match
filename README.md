#Pango50k + PC 车牌识别工程：YOLOv8 多目标检测与跟踪、FPGA 协议联调、无摄像头离线回放评估
# Pango50k + OV5640 + PC(OpenCV) 车牌识别工程

## 1. 目标
- FPGA(Pango50k)负责图像流预处理/加速。
- PC 上位机负责车牌检测与识别算法迭代。
- 当前阶段支持无摄像头离线回归（virtual/mock/replay），可先完成算法与链路验证。

## 2. 目录说明
- `rtl/`：Verilog 源码。
- `sim/`：仿真工程与测试激励。
- `constraint/`：引脚约束与时钟约束。
- `ip/`：IP 核管理与说明。
- `doc/`：架构、接口、联调与里程碑文档。
- `pc/`：PC 端 OpenCV 程序。
- `dataset/`：样例与后续采集数据。
- `results/`：性能与识别结果输出。
- `scripts/`：一键运行脚本。

## 3. 当前可运行内容
- 虚拟场景视频流（模拟车辆和车牌）。
- YOLOv8 车牌检测（当前默认 run7 权重）。
- 多目标跟踪（IoU+中心距离联合匹配、短轨过滤、轨迹预测续航）。
- FPGA TCP 协议模拟联调（mock sender + fpga_tcp）。
- 固定回放流评估（fpga_replay）。
- 离线评估脚本（连续率、恢复率、短轨占比等指标）。
- 识别器模式：
  - `mock`：使用虚拟源标签，验证流程与联调。
  - `baseline`：占位识别器，后续替换 OCR/深度模型。

## 4. 快速开始（Windows PowerShell）
```powershell
cd pc
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m app.main --config config/default.yaml --source virtual --show
```

默认配置位于 `pc/config/default.yaml`，当前关键项：
- `detector.mode: yolo`
- `detector.model: ./runs/results/training/plate_legal_illegal_multitarget_run7/weights/best.pt`
- `tracking.spawn_iou_threshold / center_dist_threshold / center_dist_weight / min_persist_frames`

## 5. 方案2联调（无摄像头但有开发板前的预演）

### 5.1 本地模拟 FPGA->PC 链路
```powershell
cd ..
.\scripts\run_mock_link.ps1 -Show
```

该脚本会启动一个模拟发送端（TCP）并让 PC 端以 `fpga_tcp` 模式接收。

可选：录制固定回放流（后续做可复现回归）
```powershell
.\scripts\run_mock_link.ps1 -Frames 120 -SaveStream "..\dataset\samples\fpga_stream.bin"
```

### 5.2 使用开发板真实发送
当开发板侧能够按协议发送数据后，直接运行：
```powershell
cd pc
python -m app.main --config config/default.yaml --source fpga_tcp --show
```

默认地址在配置文件中：`pc/config/default.yaml` -> `fpga_source.host/port`。

## 6. 协议说明
- 协议文档：`doc/fpga_pc_protocol.md`
- 板端发送说明：`doc/fpga_board_tx_spec.md`
- 协议代码：`pc/transport/protocol.py`
- 接收代码：`pc/transport/fpga_stream.py`
- 已确认接口总表：`doc/board_interface_map.md`
- 硬件加速模块说明：`doc/fpga_accel_module.md`

## 6.1 上电当天执行单
- 快速执行：`doc/power_on_day_checklist.md`

## 7. 下一步建议
- 接入 OV5640 后，在 `pc/vision/frame_source.py` 增加真实采集源。
- 让 FPGA 端按 `doc/fpga_pc_protocol.md` 发送帧数据。
- 替换 `pc/inference/recognizer.py` 为 OCR/深度学习识别器。

## 8. 无摄像头离线回归（推荐）

一键执行 virtual -> mock tcp + 录制 -> replay -> 评估：
```powershell
.\scripts\run_offline_regression.ps1 -Frames 120
```

主要产物：
- `results/run_result.csv`
- `results/metrics_virtual.json`
- `results/metrics_mock_tcp.json`
- `results/metrics_replay.json`

单独评估命令：
```powershell
cd pc
python -m tools.eval_run_result --csv ..\results\run_result.csv --out-json ..\results\run_metrics.json
```

## 9. 训练数据入口
- 数据目录：`dataset/plate_train/README.md`
- 数据要求：`doc/training_data_requirements.md`
- 批量导入脚本：`scripts/import_images.ps1`
