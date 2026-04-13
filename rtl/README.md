# RTL

放置 FPGA 端 Verilog 源码。
建议按功能拆分：
- sensor_if: 摄像头输入接口（OV5640）
- preprocess: 去噪/灰度/缩放等预处理
- roi: 感兴趣区域提取
- accel: 硬件加速模块
- common: 公共模块（FIFO 包装、时钟域跨越等）
