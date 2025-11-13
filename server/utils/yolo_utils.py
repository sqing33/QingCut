"""YOLO 格式转换工具函数"""
from typing import Dict, List, Any
from PIL import Image


def convert_box_to_yolo_format(box: Dict[str, float], image_width: int, image_height: int) -> Dict[str, float]:
    """将像素坐标的边界框转换为 YOLO 格式（归一化）
    
    Args:
        box: 包含 x, y, width, height 的字典（像素坐标）
        image_width: 图片宽度
        image_height: 图片高度
    
    Returns:
        YOLO 格式的边界框 (x_center, y_center, width, height)，值在 0-1 之间
    """
    x_center = (box['x'] + box['width'] / 2) / image_width
    y_center = (box['y'] + box['height'] / 2) / image_height
    width = box['width'] / image_width
    height = box['height'] / image_height
    
    return {
        'x_center': x_center,
        'y_center': y_center,
        'width': width,
        'height': height
    }


def process_image_with_padding(image_path: str, target_size: int = 640) -> Image.Image:
    """处理图片：添加黑色填充使其成为正方形，然后缩放到目标尺寸
    
    Args:
        image_path: 图片路径
        target_size: 目标尺寸（默认 640x640）
    
    Returns:
        处理后的图片对象
    """
    # 打开原始图片
    img = Image.open(image_path)
    orig_width, orig_height = img.size
    
    # 计算填补后的尺寸（1:1宽高比）
    max_dim = max(orig_width, orig_height)
    
    # 创建正方形画布（黑色背景）
    square_img = Image.new('RGB', (max_dim, max_dim), (0, 0, 0))
    
    # 计算粘贴位置（居中）
    paste_x = (max_dim - orig_width) // 2
    paste_y = (max_dim - orig_height) // 2
    
    # 将原图粘贴到正方形画布上
    square_img.paste(img, (paste_x, paste_y))
    
    # 缩放到目标尺寸
    resized_img = square_img.resize((target_size, target_size), Image.Resampling.LANCZOS)
    
    return resized_img


def map_annotations_to_processed_image(
    annotations: List[Dict[str, Any]], 
    orig_width: int, 
    orig_height: int,
    target_size: int = 640
) -> List[str]:
    """将原始标注映射到处理后的图片坐标系（填充+缩放），并转换为 YOLO 格式
    
    Args:
        annotations: 标注列表，每个标注包含 class_id 和 box
        orig_width: 原始图片宽度
        orig_height: 原始图片高度
        target_size: 目标尺寸（默认 640x640）
    
    Returns:
        YOLO 格式的标注字符串列表
    """
    max_dim = max(orig_width, orig_height)
    paste_x = (max_dim - orig_width) // 2
    paste_y = (max_dim - orig_height) // 2
    scale = target_size / max_dim
    
    yolo_annotations = []
    
    for ann in annotations:
        if 'box' not in ann or 'class_id' not in ann:
            continue
            
        box = ann['box']
        
        # 原始坐标映射到填补后的坐标系
        mapped_x = box['x'] + paste_x
        mapped_y = box['y'] + paste_y
        mapped_width = box['width']
        mapped_height = box['height']
        
        # 缩放到目标尺寸
        scaled_x = mapped_x * scale
        scaled_y = mapped_y * scale
        scaled_width = mapped_width * scale
        scaled_height = mapped_height * scale
        
        # 转换为 YOLO 格式（归一化到 0-1）
        yolo_x_center = (scaled_x + scaled_width / 2) / target_size
        yolo_y_center = (scaled_y + scaled_height / 2) / target_size
        yolo_width = scaled_width / target_size
        yolo_height = scaled_height / target_size
        
        yolo_annotations.append(
            f"{ann['class_id']} {yolo_x_center} {yolo_y_center} {yolo_width} {yolo_height}"
        )
    
    return yolo_annotations


def format_yolo_annotation(class_idx: int, bbox: Dict[str, float]) -> str:
    """格式化 YOLO 标注字符串
    
    Args:
        class_idx: 类别索引
        bbox: YOLO 格式的边界框
    
    Returns:
        YOLO 格式的标注字符串
    """
    return f"{class_idx} {bbox['x_center']} {bbox['y_center']} {bbox['width']} {bbox['height']}"
