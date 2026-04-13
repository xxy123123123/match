# Pango50k + OV5640 + PC(OpenCV) 车牌识别工程

## 1. 目标
- FPGA(Pango50k)负责图像流预处理/加速。
- PC 上位机负责车牌检测与识别算法迭代。
- 当前阶段支持虚拟视频源，在无摄像头条件下联调整链路。

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
- 车牌区域检测（OpenCV 基线算法）。
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

## 5. 方案2联调（无摄像头但有开发板前的预演）

### 5.1 本地模拟 FPGA->PC 链路
```powershell
cd ..
.\scripts\run_mock_link.ps1 -Show
```

该脚本会启动一个模拟发送端（TCP）并让 PC 端以 `fpga_tcp` 模式接收。

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

## 8. 训练数据入口
- 数据目录：`dataset/plate_train/README.md`
- 数据要求：`doc/training_data_requirements.md`
- 批量导入脚本：`scripts/import_images.ps1`
