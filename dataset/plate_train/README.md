# Plate Training Dataset

本目录用于车牌检测/识别训练数据。

## 目录说明
- `raw/`：原始图片，未标注。
- `labeled/images/`：已标注图片。
- `labeled/annotations/`：检测框标注文件。
- `labeled/ocr/`：车牌字符标注文件。
- `splits/`：训练/验证/测试划分文件。

## 建议你提供的数据
优先按下面两种方式之一提供：

### 方式 A：车牌整图
每张图里包含完整车辆或完整车牌场景。
适合做检测 + 识别完整流程。

### 方式 B：车牌裁剪图
每张图只包含单张车牌。
适合先做字符识别训练。

## 命名建议
- `raw_0001.jpg`
- `raw_0002.jpg`
- `plate_0001.jpg`

也可以不命名，直接把图片都放到一个目录后执行批量导入脚本，自动重命名为 `0001.jpg`、`0002.jpg`。

## 批量导入与自动重命名
在项目根目录运行：

```powershell
.\scripts\import_images.ps1 -Src "D:\你的图片目录"
```

导入后会自动生成：
- `dataset/plate_train/labeled/images/` 下的连续编号图片
- `dataset/plate_train/labeled/annotations/import_mapping.csv`（原名到新名映射）
- `dataset/plate_train/labeled/annotations/pending_labels.csv`（待标注清单）

## CCPD 自动标注
如果来源是 CCPD 数据集，可以根据原始文件名自动解析车牌文本和框：

```powershell
.\scripts\ccpd_autolabel.ps1
```

输出文件：
- `dataset/plate_train/labeled/annotations/ccpd_labels.csv`

## 你发给我时最好附带的信息
- 图片来源：实拍 / 截图 / 视频抽帧
- 是否同一车牌
- 是否有标注
- 车牌文本内容
- 是否需要我先做清洗和筛选

## 标注建议
如果要做检测训练，建议每张图至少给出：
- 车牌框坐标
- 车牌文本

如果只做识别训练，建议直接给：
- 车牌裁剪图
- 对应车牌文本
