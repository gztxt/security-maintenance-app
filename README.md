# 安防维保管理系统

[![GitHub Release](https://img.shields.io/github/v/release/gztxt/security-maintenance-app)](https://github.com/gztxt/security-maintenance-app/releases)
[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://python.org)

基于 Python 开发的安防设备维保管理系统，管理日常巡查记录并一键生成月度 PDF 报告。

---

## 功能一览

| 功能 | 说明 |
|------|------|
| 📝 **日志管理** | 记录每日巡查地点和工作内容，支持按日期查询 |
| 📸 **图片管理** | 拖拽上传现场照片，自动缩略图，每日最多 4 张 |
| 📄 **PDF 报告生成** | 一键生成符合格式要求的 A4 月度报告 |
| 💾 **SQLite 存储** | 数据本地存储，无需数据库服务 |
| 📱 **PWA 支持** | Web 端支持移动设备 PWA 安装 |
| 🎨 **Material Design** | 响应式界面，移动端友好 |

## PDF 报告排版（V16-final）

- **封面**: 标题 36pt 居中，4 行信息底部居中+左对齐
- **维保简述**: 自动按自然填充分页，全角字母数字排版
- **排查现场**: 每页固定 **3 个表格**，行高 `[10,12,32,41]mm`
- **图片**: 框高 41mm，图片最大 40mm，间距 3mm
- **边距**: 上下左右 **5mm** 对称边距
- **字体**: DroidSansFallback（数字/英文字母全角转换）

## 快速开始

```bash
# 1. 克隆仓库
git clone https://github.com/gztxt/security-maintenance-app.git
cd security-maintenance-app

# 2. 安装依赖
pip install -r requirements.txt

# 3. 运行（两种模式）
# Web 模式
bash start-server.sh

# 桌面模式
python app.py
```

## 项目结构

```
security-maintenance-app/
├── app.py                  # Web 应用入口
├── config.py               # 配置管理
├── database.py             # SQLite 数据库操作
├── report_generator.py     # PDF 报告生成（核心）
├── image_processor.py      # 图片处理
├── start-server.sh         # Web 服务启动脚本
├── requirements.txt        # 依赖清单
├── static/                 # 前端静态资源
│   ├── css/style.css       # 样式
│   ├── js/app.js           # 前端逻辑
│   └── ...
├── templates/              # HTML 模板
├── data/                   # 运行时数据目录
│   ├── database.db         # SQLite 数据库
│   ├── images/             # 图片存储
│   └── reports/            # PDF 报告输出
└── DroidSansFallbackFull.ttf  # PDF 中文字体
```

## 技术栈

- **后端**: Python + Flask
- **PDF**: ReportLab
- **数据库**: SQLite
- **图片**: Pillow (PIL)
- **前端**: HTML + CSS + JavaScript + PWA
- **桌面端**: Flet (Flutter-based)

## 开发相关

### 排版参数（改前必读）

PDF 排版的 **铁律参数** 已定稿于 V16-final：

- `_add_detailed_records_pages`: 固定行高 `[10,12,32,41]mm`
- 列宽：排查现场 `44.7+44.7+49.5+61.1=200mm`
- 简述页列宽：左 30 + 右 170 = 200mm
- 图片：`photo_table` 子表结构不可删除
- 全角转换：`_fw()` 函数不可删除

### 更新日志

**v1.0.0** (2026-07-05)
- 首次发布
- 完整的日志管理、图片管理、PDF 报告生成
- PWA 支持
- -->

## 许可证

MIT
