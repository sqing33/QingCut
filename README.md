# QingCut - 智能视频标注与训练系统

## 项目概述

QingCut 是一个基于 YOLO 的智能视频处理系统，集成了视频上传、帧提取、数据标注、模型训练和视频推理等完整功能。系统采用前后端分离架构，提供直观的 Web 界面，支持多类别目标检测模型的训练和部署。

### 核心功能

- 🎬 **视频管理**: 支持视频文件上传、预览、重命名和删除
- 🏷️ **数据标注**: 可视化框选标注工具，支持多类别标注
- 📊 **数据集管理**: YOLO 格式数据集的创建、管理和导出
- 🚀 **模型训练**: 集成 YOLO 训练流程，支持实时监控训练进度
- 🎯 **视频推理**: 使用训练好的模型进行视频目标检测
- 📈 **可视化分析**: 训练指标可视化、结果展示和性能分析

## 技术架构

### 前端技术栈

- **Vue 3**: 现代化前端框架，支持 Composition API
- **TypeScript**: 类型安全的 JavaScript 超集
- **Tailwind CSS**: 实用优先的 CSS 框架
- **DaisyUI**: 基于 Tailwind CSS 的组件库
- **Vue Router**: 单页应用路由管理
- **Axios**: HTTP 客户端，用于 API 通信

### 后端技术栈

- **FastAPI**: 现代、快速的 Python Web 框架
- **SQLAlchemy**: Python SQL 工具包和 ORM
- **PostgreSQL**: 高性能关系型数据库
- **Ultralytics YOLO**: 目标检测模型训练和推理
- **OpenCV**: 计算机视觉库
- **WebSockets**: 实时双向通信

### 数据库设计

系统采用关系型数据库设计，主要数据表包括：

- **videos**: 视频文件信息
- **frames**: 提取的视频帧
- **classes**: 标注类别定义
- **class_groups**: 类别分组管理
- **datasets**: 数据集信息
- **frame_datasets**: 帧与数据集的关联关系
- **training_records**: 训练任务记录
- **training_epoch_metrics**: 训练过程指标

## 项目结构

```
video-cut/
├── server/                     # 后端服务
│   ├── main.py                # FastAPI 应用入口
│   ├── config.py              # 配置文件
│   ├── database.py            # 数据库模型和连接
│   ├── routers/               # API 路由模块
│   │   ├── videos.py          # 视频管理 API
│   │   ├── frames.py          # 帧管理 API
│   │   ├── classes.py         # 类别管理 API
│   │   ├── datasets.py        # 数据集管理 API
│   │   ├── export.py          # 数据导出 API
│   │   └── train.py           # 训练管理 API
│   ├── services/              # 业务逻辑层
│   │   ├── video_service.py   # 视频服务
│   │   ├── frame_service.py   # 帧服务
│   │   ├── class_service.py   # 类别服务
│   │   ├── dataset_service.py # 数据集服务
│   │   ├── export_service.py  # 导出服务
│   │   └── train_service.py   # 训练服务
│   ├── utils/                 # 工具函数
│   │   ├── file_utils.py      # 文件处理工具
│   │   └── yolo_utils.py      # YOLO 相关工具
│   ├── uploads/               # 上传文件存储
│   │   ├── videos/            # 视频文件
│   │   └── frames/            # 帧图片
│   ├── dataset/               # 数据集存储
│   ├── train/                  # 训练结果存储
│   │   ├── models/            # 预训练模型
│   │   └── runs/              # 训练运行结果
│   └── requirements.txt       # Python 依赖
├── web/                       # 前端应用
│   ├── src/
│   │   ├── components/        # Vue 组件
│   │   │   ├── VideoCapture.vue      # 视频捕获和标注
│   │   │   ├── VideoList.vue         # 视频列表
│   │   │   ├── ClassGroupManager.vue # 类别管理
│   │   │   ├── ImagePreviewModal.vue # 图片预览
│   │   │   └── RadialNav.vue         # 导航组件
│   │   ├── views/             # 页面组件
│   │   │   ├── VideoCapturePage.vue # 视频处理页面
│   │   │   ├── DataPage.vue          # 数据管理页面
│   │   │   ├── Train.vue             # 训练管理页面
│   │   │   └── Settings.vue          # 设置页面
│   │   ├── router/            # 路由配置
│   │   ├── styles/            # 样式文件
│   │   │   └── glassmorphism.scss # 玻璃态样式
│   │   ├── App.vue            # 根组件
│   │   └── main.ts            # 应用入口
│   ├── public/                # 静态资源
│   ├── package.json           # Node.js 依赖
│   └── vite.config.ts         # Vite 构建配置
└── README.txt                 # 项目说明文档
```

## 核心功能详解

### 1. 视频捕获与标注 (VideoCapture)

#### 功能特性

- **视频播放控制**: 支持播放、暂停、快进、快退和变速播放
- **智能框选标注**: 可视化框选工具，支持多目标标注
- **实时标注预览**: 标注框实时显示，支持调整大小和位置
- **类别快速选择**: 支持类别分组和快速选择
- **键盘快捷键**: 空格键标注、R 键进入框选模式等
- **进度持久化**: 自动保存播放进度和标注状态

#### 技术实现

- 使用 HTML5 Video API 进行视频播放
- Canvas 叠加层实现标注框绘制
- 原始分辨率坐标系统，确保标注精度
- 支持标注框的拖拽调整和编辑

### 2. 数据管理 (DataPage)

#### 功能特性

- **数据筛选**: 按视频、类别、时间、数据集等多维度筛选
- **批量操作**: 支持批量分配到数据集、批量删除
- **数据集管理**: 创建、编辑、删除数据集
- **YOLO 格式导出**: 一键导出 YOLO 训练格式数据集
- **标注编辑**: 在线编辑标注信息

#### 数据流

1. 视频帧提取 → 标注数据保存 → 数据集组织 → YOLO 格式转换 → 模型训练

### 3. 模型训练 (Train)

#### 功能特性

- **训练任务管理**: 创建、启动、取消、删除训练任务
- **实时监控**: WebSocket 实时推送训练日志和进度
- **模型管理**: 预训练模型下载、上传和管理
- **结果可视化**: 训练指标图表、损失曲线、mAP 变化
- **超参数配置**: 轮数、批次大小、图片尺寸等参数设置

#### 训练流程

1. 选择数据集和预训练模型
2. 配置训练超参数
3. 启动异步训练任务
4. 实时监控训练进度
5. 查看训练结果和模型文件

### 4. API 接口设计

#### 视频管理 API

- `POST /api/upload-video` - 上传视频文件
- `GET /api/videos` - 获取视频列表
- `POST /api/rename-video` - 重命名视频
- `POST /api/delete-video` - 删除视频

#### 帧管理 API

- `GET /api/frames` - 获取帧列表
- `POST /api/save-frame-multi` - 保存带标注的帧
- `GET /api/frames/{filename}/annotations` - 获取帧标注
- `POST /api/frames/{filename}/annotations` - 更新帧标注

#### 类别管理 API

- `GET /api/classes` - 获取类别列表
- `POST /api/classes` - 创建新类别
- `PUT /api/classes/{id}` - 更新类别信息
- `DELETE /api/classes/{id}` - 删除类别

#### 数据集管理 API

- `GET /api/datasets` - 获取数据集列表
- `POST /api/export/yolo-dataset` - 导出 YOLO 数据集
- `GET /api/export/yolo-dataset-zip/{identifier}` - 下载数据集压缩包

#### 训练管理 API

- `GET /api/train/datasets` - 获取可训练数据集
- `GET /api/train/models` - 获取可用模型
- `POST /api/train/create` - 创建训练任务
- `POST /api/train/{task_id}/start` - 启动训练
- `GET /api/train/{task_id}/status` - 获取训练状态
- `GET /api/train/{task_id}/results` - 获取训练结果

## 使用指南

### 工作流程

#### 1. 数据准备阶段

1. **上传视频**: 在视频捕获页面上传需要处理的视频文件
2. **设置类别**: 在类别管理中创建检测目标类别（如：人、车、动物等）
3. **视频标注**: 播放视频，在关键帧上进行框选标注
4. **数据集创建**: 将标注好的帧组织成训练数据集

#### 2. 模型训练阶段

1. **选择数据集**: 在训练页面选择准备好的数据集
2. **选择模型**: 选择预训练模型或上传自定义模型
3. **配置参数**: 设置训练轮数、批次大小等超参数
4. **启动训练**: 开始训练并实时监控进度
5. **评估结果**: 查看训练指标和模型性能

#### 3. 模型应用阶段

1. **模型部署**: 选择训练好的模型进行推理
2. **视频处理**: 对新视频进行目标检测
3. **结果分析**: 查看检测结果和性能统计
