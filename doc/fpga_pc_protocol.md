# FPGA 到 PC 数据协议（V1）

## 1. 设计目标
- 定义稳定的 FPGA->PC 帧传输格式。
- 支持 TCP 实时传输与文件回放。
- 携带 ROI 信息，便于 PC 侧识别流程联调。

## 2. 字段定义（Little Endian）
头部固定长度：40 字节。

1. magic (u32): 固定值 `0x45544C50`，表示 `PLTE`。
2. version (u8): 协议版本，当前 `1`。
3. header_len (u8): 头部长度，固定 `40`。
4. flags (u16): 标志位，预留。
5. frame_id (u32): 帧编号。
6. timestamp_ms (u64): 采集时间戳（毫秒）。
7. width (u16): 图像宽。
8. height (u16): 图像高。
9. channels (u8): 通道数，1或3。
10. pixel_format (u8): 0=GRAY8, 1=BGR24。
11. roi_x (u16): ROI左上角x。
12. roi_y (u16): ROI左上角y。
13. roi_w (u16): ROI宽。
14. roi_h (u16): ROI高。
15. payload_len (u32): 图像数据长度。
16. crc32 (u32): payload 的 CRC32。

payload 紧随头部，长度为 payload_len。

## 2.1 字节偏移表

| 偏移 | 长度 | 字段 | 说明 |
| --- | --- | --- | --- |
| 0x00 | 4 | magic | 固定值 `0x45544C50` |
| 0x04 | 1 | version | 当前 `1` |
| 0x05 | 1 | header_len | 固定 `40` |
| 0x06 | 2 | flags | 预留 |
| 0x08 | 4 | frame_id | 帧编号 |
| 0x0C | 8 | timestamp_ms | 毫秒时间戳 |
| 0x14 | 2 | width | 图像宽 |
| 0x16 | 2 | height | 图像高 |
| 0x18 | 1 | channels | 1 或 3 |
| 0x19 | 1 | pixel_format | 0=GRAY8, 1=BGR24 |
| 0x1A | 2 | roi_x | ROI 左上角 x |
| 0x1C | 2 | roi_y | ROI 左上角 y |
| 0x1E | 2 | roi_w | ROI 宽 |
| 0x20 | 2 | roi_h | ROI 高 |
| 0x22 | 4 | payload_len | 负载长度 |
| 0x26 | 4 | crc32 | 对 payload 的 CRC32 |

其中 `payload` 从偏移 `0x2A` 开始。

## 2.2 负载约束
- 灰度图：`payload_len = width * height * 1`
- BGR24：`payload_len = width * height * 3`
- payload 必须是连续内存，不允许带额外行填充

## 2.3 包格式示例
以 `width=1280, height=720, channels=3, pixel_format=1` 为例：
- 头部长度：40 字节
- 负载长度：`1280 * 720 * 3 = 2,764,800`
- 整包长度：`40 + 2,764,800`

## 2.4 发送约定
- 小端序写入所有多字节字段。
- 先发头部，再发 payload。
- `crc32` 计算范围只包含 payload，不包含头部。
- ROI 暂时可置零；若板端已有车牌框，也可以直接带上。

## 3. 传输方式
- 实时流：TCP，按“头+负载”连续发送。
- 回放流：多个包直接顺序拼接写入二进制文件。

## 4. 代码对应
- 协议定义与编解码：[pc/transport/protocol.py](../pc/transport/protocol.py)
- TCP/回放输入源：[pc/transport/fpga_stream.py](../pc/transport/fpga_stream.py)
- 上位机主入口：[pc/app/main.py](../pc/app/main.py)

## 5. 联调要求
- FPGA 端必须保证 `payload_len = width * height * channels`。
- PC 端会校验 magic、header_len、payload_len、crc32。
- ROI 无效时可置 0。

## 6. 建议的板端实现顺序
1. 先固定一张测试图，验证头部能正确解析。
2. 再接真实图像流，但保持分辨率不变。
3. 最后再加 ROI 和动态帧编号。
