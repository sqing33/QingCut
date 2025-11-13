"""YOLO 数据集导出业务逻辑"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import shutil
import yaml

from database import Video, Frame, Class, Dataset, FrameDataset
from config import FRAME_DIR, DATASET_DIR, DEFAULT_IMAGE_SIZE, TRAIN_SPLIT_RATIO
from utils.yolo_utils import process_image_with_padding, map_annotations_to_processed_image


async def export_yolo_by_video(
    db: AsyncSession,
    video_filename: str
) -> Dict[str, Any]:
    """导出指定视频的YOLO格式数据（支持多标注）
    
    Args:
        db: 数据库会话
        video_filename: 视频文件名
    
    Returns:
        YOLO格式的数据
    
    Raises:
        ValueError: 如果视频不存在或没有标注数据
    """
    # 查找视频
    result = await db.execute(
        select(Video).where(Video.filename == video_filename)
    )
    video = result.scalar_one_or_none()
    
    if not video:
        raise ValueError("视频不存在")
    
    # 查找该视频的所有截图
    result = await db.execute(
        select(Frame).where(Frame.video_id == video.id)
    )
    frames = result.scalars().all()
    
    # 获取所有类名
    result = await db.execute(select(Class).order_by(Class.id))
    classes = result.scalars().all()
    class_map = {cls.id: idx for idx, cls in enumerate(classes)}
    
    # 生成YOLO格式数据
    yolo_data = []
    for frame in frames:
        # 新格式：annotations包含数组
        if frame.annotations and isinstance(frame.annotations, list):
            for ann in frame.annotations:
                if 'class_id' in ann and 'yolo_format' in ann:
                    class_idx = class_map.get(ann['class_id'])
                    if class_idx is not None:
                        yolo_data.append({
                            "image": frame.filename,
                            "image_path": frame.path,
                            "class_id": class_idx,
                            "bbox": [
                                ann['yolo_format']['x_center'],
                                ann['yolo_format']['y_center'],
                                ann['yolo_format']['width'],
                                ann['yolo_format']['height']
                            ]
                        })
        # 旧格式：单个标注（向后兼容）
        elif frame.class_id and frame.annotations and isinstance(frame.annotations, dict) and 'yolo_format' in frame.annotations:
            class_idx = class_map.get(frame.class_id)
            if class_idx is not None:
                yolo_data.append({
                    "image": frame.filename,
                    "image_path": frame.path,
                    "class_id": class_idx,
                    "bbox": [
                        frame.annotations['yolo_format']['x_center'],
                        frame.annotations['yolo_format']['y_center'],
                        frame.annotations['yolo_format']['width'],
                        frame.annotations['yolo_format']['height']
                    ]
                })
    
    if not yolo_data:
        raise ValueError("该视频没有标注数据")
    
    # 生成类名文件内容
    class_names = [cls.name for cls in classes]
    
    return {
        "video_filename": video_filename,
        "total_frames": len(set(d["image"] for d in yolo_data)),
        "total_annotations": len(yolo_data),
        "classes": class_names,
        "annotations": yolo_data
    }


async def export_all_yolo(db: AsyncSession) -> Dict[str, Any]:
    """导出所有视频的YOLO格式数据（支持多标注）
    
    Args:
        db: 数据库会话
    
    Returns:
        YOLO格式的数据
    
    Raises:
        ValueError: 如果没有标注数据
    """
    # 查找所有截图
    result = await db.execute(select(Frame))
    frames = result.scalars().all()
    
    # 获取所有类名
    result = await db.execute(select(Class).order_by(Class.id))
    classes = result.scalars().all()
    class_map = {cls.id: idx for idx, cls in enumerate(classes)}
    
    # 生成YOLO格式数据
    yolo_data = []
    for frame in frames:
        # 新格式：annotations包含数组
        if frame.annotations and isinstance(frame.annotations, list):
            for ann in frame.annotations:
                if 'class_id' in ann and 'yolo_format' in ann:
                    class_idx = class_map.get(ann['class_id'])
                    if class_idx is not None:
                        yolo_data.append({
                            "image": frame.filename,
                            "image_path": frame.path,
                            "class_id": class_idx,
                            "bbox": [
                                ann['yolo_format']['x_center'],
                                ann['yolo_format']['y_center'],
                                ann['yolo_format']['width'],
                                ann['yolo_format']['height']
                            ]
                        })
        # 旧格式：单个标注（向后兼容）
        elif frame.class_id and frame.annotations and isinstance(frame.annotations, dict) and 'yolo_format' in frame.annotations:
            class_idx = class_map.get(frame.class_id)
            if class_idx is not None:
                yolo_data.append({
                    "image": frame.filename,
                    "image_path": frame.path,
                    "class_id": class_idx,
                    "bbox": [
                        frame.annotations['yolo_format']['x_center'],
                        frame.annotations['yolo_format']['y_center'],
                        frame.annotations['yolo_format']['width'],
                        frame.annotations['yolo_format']['height']
                    ]
                })
    
    if not yolo_data:
        raise ValueError("没有标注数据")
    
    # 生成类名文件内容
    class_names = [cls.name for cls in classes]
    
    return {
        "total_frames": len(set(d["image"] for d in yolo_data)),
        "total_annotations": len(yolo_data),
        "classes": class_names,
        "annotations": yolo_data
    }


async def export_yolo_dataset_to_folder(
    db: AsyncSession,
    name: str,
    identifier: str,
    video_filenames: Optional[List[str]] = None,
    append_mode: bool = False,
    train_split: float = TRAIN_SPLIT_RATIO
) -> Dict[str, Any]:
    """将YOLO数据集导出到指定文件夹，并自动分割训练集和验证集
    
    Args:
        db: 数据库会话
        name: 数据集名称
        identifier: 数据集标识符
        video_filenames: 视频文件名列表，None表示全部
        append_mode: 是否追加模式
        train_split: 训练集比例，默认从配置文件读取（80%训练集，20%验证集）
    
    Returns:
        导出结果
    
    Raises:
        ValueError: 如果参数错误或没有数据
    """
    # 验证标识符格式
    if not all(c.isalnum() or c == '_' for c in identifier):
        raise ValueError("标识符只能包含字母、数字和下划线")
    
    # 创建数据集目录结构（train/val分离）
    dataset_dir = DATASET_DIR / identifier
    train_images_dir = dataset_dir / "train" / "images"
    train_labels_dir = dataset_dir / "train" / "labels"
    val_images_dir = dataset_dir / "val" / "images"
    val_labels_dir = dataset_dir / "val" / "labels"
    
    # 根据模式处理目录
    if append_mode:
        if not dataset_dir.exists():
            raise ValueError("数据集不存在")
        train_images_dir.mkdir(parents=True, exist_ok=True)
        train_labels_dir.mkdir(parents=True, exist_ok=True)
        val_images_dir.mkdir(parents=True, exist_ok=True)
        val_labels_dir.mkdir(parents=True, exist_ok=True)
    else:
        if dataset_dir.exists():
            shutil.rmtree(dataset_dir)
        train_images_dir.mkdir(parents=True, exist_ok=True)
        train_labels_dir.mkdir(parents=True, exist_ok=True)
        val_images_dir.mkdir(parents=True, exist_ok=True)
        val_labels_dir.mkdir(parents=True, exist_ok=True)
    
    # 获取所有类名
    result = await db.execute(select(Class).order_by(Class.id))
    classes = result.scalars().all()
    class_map = {cls.id: idx for idx, cls in enumerate(classes)}
    class_names = [cls.name for cls in classes]
    
    # 获取要导出的帧
    if video_filenames:
        result = await db.execute(
            select(Video).where(Video.filename.in_(video_filenames))
        )
        videos = result.scalars().all()
        video_ids = [v.id for v in videos]
        
        result = await db.execute(
            select(Frame).where(Frame.video_id.in_(video_ids))
        )
    else:
        result = await db.execute(select(Frame))
    
    frames = result.scalars().all()
    
    # 收集所有有效的帧数据
    valid_frames = []
    for frame in frames:
        annotations_list = []
        
        # 检查annotations字段并收集标注
        if frame.annotations:
            if isinstance(frame.annotations, list):
                for ann in frame.annotations:
                    if isinstance(ann, dict) and 'class_id' in ann and 'box' in ann:
                        annotations_list.append(ann)
            elif isinstance(frame.annotations, dict) and 'yolo_format' in frame.annotations and frame.class_id:
                # 旧格式转换
                annotations_list.append({
                    'class_id': frame.class_id,
                    'box': frame.annotations.get('box', {})
                })
        
        # 只收集有标注的图片
        if annotations_list:
            valid_frames.append((frame, annotations_list))
    
    if not valid_frames:
        raise ValueError("没有可导出的标注数据")
    
    # 打乱并分割数据集
    import random
    random.shuffle(valid_frames)
    train_count = int(len(valid_frames) * train_split)
    train_frames = valid_frames[:train_count]
    val_frames = valid_frames[train_count:]
    
    # 处理训练集
    total_train_images = 0
    total_train_annotations = 0
    
    for frame, annotations_list in train_frames:
        src_image = FRAME_DIR / frame.filename
        dst_image = train_images_dir / frame.filename
        
        if src_image.exists():
            # 处理图片（填充+缩放）
            processed_img = process_image_with_padding(str(src_image), DEFAULT_IMAGE_SIZE)
            processed_img.save(dst_image)
            
            # 获取原始图片尺寸
            from PIL import Image
            orig_img = Image.open(src_image)
            orig_width, orig_height = orig_img.size
            orig_img.close()
            
            # 映射标注到处理后的图片
            mapped_annotations = map_annotations_to_processed_image(
                annotations_list,
                orig_width,
                orig_height,
                DEFAULT_IMAGE_SIZE
            )
            
            # 写入标注文件
            if mapped_annotations:
                label_filename = frame.filename.rsplit('.', 1)[0] + '.txt'
                label_path = train_labels_dir / label_filename
                with label_path.open('w') as f:
                    f.write('\n'.join(mapped_annotations))
                
                total_train_images += 1
                total_train_annotations += len(mapped_annotations)
    
    # 处理验证集
    total_val_images = 0
    total_val_annotations = 0
    
    for frame, annotations_list in val_frames:
        src_image = FRAME_DIR / frame.filename
        dst_image = val_images_dir / frame.filename
        
        if src_image.exists():
            # 处理图片（填充+缩放）
            processed_img = process_image_with_padding(str(src_image), DEFAULT_IMAGE_SIZE)
            processed_img.save(dst_image)
            
            # 获取原始图片尺寸
            from PIL import Image
            orig_img = Image.open(src_image)
            orig_width, orig_height = orig_img.size
            orig_img.close()
            
            # 映射标注到处理后的图片
            mapped_annotations = map_annotations_to_processed_image(
                annotations_list,
                orig_width,
                orig_height,
                DEFAULT_IMAGE_SIZE
            )
            
            # 写入标注文件
            if mapped_annotations:
                label_filename = frame.filename.rsplit('.', 1)[0] + '.txt'
                label_path = val_labels_dir / label_filename
                with label_path.open('w') as f:
                    f.write('\n'.join(mapped_annotations))
                
                total_val_images += 1
                total_val_annotations += len(mapped_annotations)
    
    total_images = total_train_images + total_val_images
    total_annotations = total_train_annotations + total_val_annotations
    
    if total_images == 0:
        raise ValueError("没有可导出的标注数据")
    
    # 更新数据库：创建Dataset记录和Frame-Dataset关联
    result = await db.execute(
        select(Dataset).where(Dataset.identifier == identifier)
    )
    dataset = result.scalar_one_or_none()
    
    if not dataset:
        dataset = Dataset(
            identifier=identifier,
            name=name,
            created_at=datetime.now()
        )
        db.add(dataset)
        await db.commit()
        await db.refresh(dataset)
    else:
        dataset.name = name
        await db.commit()
    
    # 为每个有标注的图片创建关联
    for frame in frames:
        if frame.annotations:
            has_valid_annotation = False
            if isinstance(frame.annotations, list):
                has_valid_annotation = any(
                    isinstance(ann, dict) and 'class_id' in ann 
                    for ann in frame.annotations
                )
            elif isinstance(frame.annotations, dict) and 'yolo_format' in frame.annotations:
                has_valid_annotation = True
            
            if has_valid_annotation:
                result = await db.execute(
                    select(FrameDataset).where(
                        FrameDataset.frame_id == frame.id,
                        FrameDataset.dataset_id == dataset.id
                    )
                )
                existing = result.scalar_one_or_none()
                
                if not existing:
                    frame_dataset = FrameDataset(
                        frame_id=frame.id,
                        dataset_id=dataset.id,
                        created_at=datetime.now()
                    )
                    db.add(frame_dataset)
    
    await db.commit()
    
    # 创建或更新类名文件
    classes_file = dataset_dir / "classes.txt"
    with classes_file.open('w', encoding='utf-8') as f:
        f.write('\n'.join(class_names))
    
    # 生成 YOLO 训练配置文件 (train.yaml)
    train_yaml_path = dataset_dir / "train.yaml"
    yaml_content = {
        'path': str(dataset_dir.absolute()),
        'train': 'train/images',
        'val': 'val/images',
        'test': None,
        'nc': len(class_names),
        'names': class_names
    }
    
    with train_yaml_path.open('w', encoding='utf-8') as f:
        yaml.dump(yaml_content, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    
    # 更新数据集信息文件
    info_file = dataset_dir / "dataset_info.txt"
    
    if append_mode:
        existing_train_images = len(list(train_images_dir.glob("*.png")))
        existing_val_images = len(list(val_images_dir.glob("*.png")))
        existing_train_labels = len(list(train_labels_dir.glob("*.txt")))
        existing_val_labels = len(list(val_labels_dir.glob("*.txt")))
        
        with info_file.open('w', encoding='utf-8') as f:
            f.write(f"数据集名称: {name}\n")
            f.write(f"标识符: {identifier}\n")
            f.write(f"训练集图片数量: {existing_train_images}\n")
            f.write(f"验证集图片数量: {existing_val_images}\n")
            f.write(f"总图片数量: {existing_train_images + existing_val_images}\n")
            f.write(f"训练集标注数量: {existing_train_labels}\n")
            f.write(f"验证集标注数量: {existing_val_labels}\n")
            f.write(f"类别数量: {len(class_names)}\n")
            f.write(f"类别列表:\n")
            for idx, cls_name in enumerate(class_names):
                f.write(f"  {idx}: {cls_name}\n")
            f.write(f"\n最后更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    else:
        with info_file.open('w', encoding='utf-8') as f:
            f.write(f"数据集名称: {name}\n")
            f.write(f"标识符: {identifier}\n")
            f.write(f"训练集图片数量: {total_train_images}\n")
            f.write(f"验证集图片数量: {total_val_images}\n")
            f.write(f"总图片数量: {total_images}\n")
            f.write(f"训练集标注数量: {total_train_annotations}\n")
            f.write(f"验证集标注数量: {total_val_annotations}\n")
            f.write(f"总标注数量: {total_annotations}\n")
            f.write(f"训练集比例: {train_split * 100:.0f}%\n")
            f.write(f"验证集比例: {(1 - train_split) * 100:.0f}%\n")
            f.write(f"类别数量: {len(class_names)}\n")
            f.write(f"类别列表:\n")
            for idx, cls_name in enumerate(class_names):
                f.write(f"  {idx}: {cls_name}\n")
    
    return {
        "name": name,
        "identifier": identifier,
        "path": str(dataset_dir),
        "total_images": total_images,
        "total_annotations": total_annotations,
        "classes": class_names
    }
