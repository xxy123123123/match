# FPGA 硬件加速模块说明

## 1. 模块目标
当前实现提供一条轻量实时链路：
1. RGB 转灰度
2. 灰度阈值二值化
3. 基于二值图提取整帧 ROI 包围框

该版本适合先完成板端-上位机闭环联调，后续可继续替换为更复杂算子（Sobel、形态学、连通域）。

## 2. RTL 文件
- `rtl/preprocess/rgb2gray.v`
- `rtl/preprocess/gray_threshold.v`
- `rtl/roi/roi_bbox_accum.v`
- `rtl/accel/plate_accel_top.v`

## 3. 接口协议（像素流）
输入控制信号：
- `i_valid`：当前拍像素有效
- `i_sof`：帧首像素
- `i_eol`：当前行末像素
- `i_eof`：帧尾像素

输入像素：
- `i_r/i_g/i_b`：8bit RGB

输出：
- `o_gray`：灰度像素
- `o_bin`：二值结果
- `o_bbox_valid` + `o_x_min/o_y_min/o_x_max/o_y_max`：一帧结束时给出 ROI 包围框

## 4. 参数建议
- `TH_LOW/TH_HIGH`：根据场景亮度调整阈值。
- `MIN_W/MIN_H`：用于过滤噪声小块。
- `IMG_W/IMG_H`：应与实际输入分辨率一致。

## 5. 基础仿真
- 仿真文件：`sim/tb_plate_accel_top.v`
- 仿真逻辑：构造一个亮矩形目标，检查输出 bbox 是否匹配。

## 6. 上板联调建议
1. 先用板端测试图像流验证 `o_bbox_valid` 是否稳定输出。
2. 将 `o_bbox_*` 通过你现有协议送到 PC。
3. 在 PC 端把 ROI 与识别模块对接，形成端到端闭环。
