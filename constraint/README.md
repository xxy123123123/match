# Constraint（IO 约束文件）

## 📌 当前工程可用约束

### ✅ 完整 FDC 文件（推荐直接用）

👉 [mes50hp_complete.fdc](mes50hp_complete.fdc)

**特点：**
- 包含所有已确认的 IO 管脚（时钟、复位、UART、LED、HDMI RGB 24bit、同步信号）
- 所有 IO 电平标准均为 LVCMOS33（3.3V）
- 可直接导入 PDS 工具链

**如何使用：**
1. 在 PDS 中打开 Pin Planner 或 IO Constraint 界面
2. 导入本文件或手动逐行配置
3. 重新综合确保无冲突
4. 下载验证

---

## 🎯 关键结论（必读）

| 项目 | 决策 | 说明 |
|-----|-----|------|
| 系统时钟 | 用 **P20**（50MHz） | 不用 AA12（AA12 依赖 HDMI 芯片初始化） |
| RGB 输入 | **完整 24bit** | B[0:7] + G[0:7] + R[0:7] 已列齐 |
| IO 电平 | **LVCMOS33** | 所有普通 IO 都是 3.3V 标准 |
| HDMI 现状 | ⚠️ 待补充初始化 | 需要 MS7200 I2C 初始化，当前缺失 |

---

## ⚠️ 重要提醒

1. **HDMI 输入当前不能用**  
   → 需要完成 MS7200 I2C 初始化才能稳定接收数据  
   → 建议先用**软件生成测试源**替代真实输入

2. **DDR3 和 HSST IO**  
   → 不在此约束中（当前工程不用）

3. **约束验证**  
   → 综合通过后，下载验证 LED 闪烁和 UART 收发

---

## 📂 下一步

- 如需"视频测试源模块"（生成 720p 测试图像），见 [rtl/](../rtl/)
- HDMI 实际应用需完成 I2C 初始化流程  
- 参数参考：[doc/board_interface_map.md](../doc/board_interface_map.md)、[MES50HP开发板硬件使用手册_1V1.pdf](../MES50HP开发板硬件使用手册_1V1.pdf)
