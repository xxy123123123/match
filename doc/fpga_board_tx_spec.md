# FPGA 板端发送实现说明

本文档面向 RTL 实现，目标是把板端图像数据稳定送到 PC 端。

## 1. 发送目标
板端输出一个连续字节流，每一帧由两部分组成：
1. 40 字节头部。
2. payload 图像数据。

PC 端按协议解析并校验 CRC。

## 2. 推荐状态机

### 状态 0：IDLE
- 等待一帧发送请求。
- 清零包计数器或准备新帧编号。

### 状态 1：HEAD
- 按固定顺序输出 40 字节头部。
- 每拍输出 1 字节或按总线宽度拆分后输出。
- 头部全部发送完毕后进入 PAYLOAD。

### 状态 2：PAYLOAD
- 顺序输出图像字节流。
- 保证顺序和长度严格等于 `payload_len`。
- 输出结束后返回 IDLE。

## 3. 头部字段写入顺序
按照小端序依次写入：
1. magic
2. version
3. header_len
4. flags
5. frame_id
6. timestamp_ms
7. width
8. height
9. channels
10. pixel_format
11. roi_x
12. roi_y
13. roi_w
14. roi_h
15. payload_len
16. crc32

参考：[doc/fpga_pc_protocol.md](fpga_pc_protocol.md)

## 4. RTL 实现建议
- 头部字段建议先在寄存器或 ROM 中拼好，再逐字节送出。
- payload_len 与真实图像长度必须一致，否则 PC 端会报错。
- CRC32 建议在图像产生后计算，或者先用固定测试图验证通信，再补动态 CRC。
- 如果先做验证阶段，可以先把 ROI 全置零。

## 5. 推荐调试顺序
1. 先发固定测试帧，确认 PC 能收并解析。
2. 再发连续多帧，确认 frame_id 递增正常。
3. 再接真实图像源。
4. 最后再做板端 ROI 和预处理输出。

## 6. 最小可用字段集合
至少要保证以下字段正确：
- magic
- version
- header_len
- frame_id
- timestamp_ms
- width
- height
- channels
- pixel_format
- payload_len
- crc32

其余字段可先固定为 0。
