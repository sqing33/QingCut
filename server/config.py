"""应用配置模块"""
from pathlib import Path

# 上传目录配置
UPLOAD_DIR = Path("uploads")
VIDEO_DIR = UPLOAD_DIR / "videos"
FRAME_DIR = UPLOAD_DIR / "frames"

# 数据集目录
DATASET_DIR = Path("dataset")

# 训练输出目录
TRAIN_OUTPUT_DIR = Path("train")

# CORS 配置
CORS_ORIGINS = ["*"]
CORS_CREDENTIALS = True
CORS_METHODS = ["*"]
CORS_HEADERS = ["*"]

# 图片处理配置
DEFAULT_IMAGE_SIZE = 640  # YOLO 默认尺寸

# 数据集分割配置，训练集比例（80% 训练集，20% 验证集）
TRAIN_SPLIT_RATIO = 0.8
