"""截图管理业务逻辑"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from typing import Optional, List, Dict, Any
import json

from database import Frame, Video, Dataset, FrameDataset
from config import FRAME_DIR
from utils.file_utils import save_uploaded_file, delete_file, rename_file


async def create_frame(
    db: AsyncSession,
    upload_file,
    video_filename: Optional[str] = None,
    class_id: Optional[int] = None,
    annotation: Optional[str] = None
) -> Dict[str, Any]:
    """创建截图记录（单标注模式）
    
    Args:
        db: 数据库会话
        upload_file: 上传的图片文件
        video_filename: 源视频文件名
        class_id: 类别ID
        annotation: 标注数据（JSON字符串）
    
    Returns:
        包含截图信息的字典
    """
    # 生成唯一文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"frame_{timestamp}.png"
    filepath = FRAME_DIR / filename
    
    # 保存图片文件
    save_uploaded_file(upload_file, filepath)
    
    # 查找关联的视频
    video_id = None
    if video_filename:
        result = await db.execute(
            select(Video).where(Video.filename == video_filename)
        )
        video = result.scalar_one_or_none()
        if video:
            video_id = video.id
    
    # 解析标注数据
    annotation_dict = {}
    if annotation:
        try:
            annotation_dict = json.loads(annotation)
        except json.JSONDecodeError:
            pass
    
    # 保存到数据库
    db_frame = Frame(
        filename=filename,
        path=f"/uploads/frames/{filename}",
        video_id=video_id,
        class_id=class_id,
        width=640,
        height=640,
        annotations=annotation_dict,
        created_at=datetime.now()
    )
    db.add(db_frame)
    await db.commit()
    await db.refresh(db_frame)
    
    return {"path": str(filepath), "filename": filename}


async def create_frame_multi(
    db: AsyncSession,
    upload_file,
    video_filename: Optional[str] = None,
    annotations: Optional[str] = None
) -> Dict[str, Any]:
    """创建截图记录（多标注模式）
    
    Args:
        db: 数据库会话
        upload_file: 上传的图片文件
        video_filename: 源视频文件名
        annotations: 标注数据（JSON字符串，包含多个标注）
    
    Returns:
        包含截图信息的字典
    """
    # 生成唯一文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"frame_{timestamp}.png"
    filepath = FRAME_DIR / filename
    
    # 保存图片文件
    save_uploaded_file(upload_file, filepath)
    
    # 查找关联的视频
    video_id = None
    if video_filename:
        result = await db.execute(
            select(Video).where(Video.filename == video_filename)
        )
        video = result.scalar_one_or_none()
        if video:
            video_id = video.id
    
    # 解析标注数据
    annotations_list = []
    if annotations:
        try:
            annotations_data = json.loads(annotations)
            annotations_list = annotations_data.get('annotations', [])
        except json.JSONDecodeError:
            pass
    
    # 保存到数据库
    db_frame = Frame(
        filename=filename,
        path=f"/uploads/frames/{filename}",
        video_id=video_id,
        class_id=None,
        width=640,
        height=640,
        annotations=annotations_list,
        created_at=datetime.now()
    )
    db.add(db_frame)
    await db.commit()
    await db.refresh(db_frame)
    
    return {
        "path": str(filepath),
        "filename": filename,
        "annotation_count": len(annotations_list)
    }


async def get_all_frames(db: AsyncSession) -> List[Dict[str, Any]]:
    """获取所有截图列表
    
    Args:
        db: 数据库会话
    
    Returns:
        截图列表
    """
    result = await db.execute(
        select(Frame).order_by(Frame.created_at.desc())
    )
    frames = result.scalars().all()
    
    # 获取视频文件名映射
    video_result = await db.execute(select(Video))
    videos = {v.id: v.filename for v in video_result.scalars().all()}
    
    # 获取所有数据集映射
    dataset_result = await db.execute(select(Dataset))
    datasets = {d.id: {"identifier": d.identifier, "name": d.name} for d in dataset_result.scalars().all()}
    
    # 获取所有frame-dataset关联
    frame_dataset_result = await db.execute(select(FrameDataset))
    frame_datasets_map = {}
    for fd in frame_dataset_result.scalars().all():
        if fd.frame_id not in frame_datasets_map:
            frame_datasets_map[fd.frame_id] = []
        if fd.dataset_id in datasets:
            frame_datasets_map[fd.frame_id].append(datasets[fd.dataset_id])
    
    return [
        {
            "filename": frame.filename,
            "path": frame.path,
            "created_at": frame.created_at.timestamp(),
            "video_filename": videos.get(frame.video_id) if frame.video_id else None,
            "dataset_identifier": frame.dataset_identifier,
            "datasets": frame_datasets_map.get(frame.id, [])
        }
        for frame in frames
    ]


async def get_frame_annotations(db: AsyncSession, frame_filename: str) -> Dict[str, Any]:
    """获取截图的标注数据
    
    Args:
        db: 数据库会话
        frame_filename: 截图文件名
    
    Returns:
        标注数据
    
    Raises:
        ValueError: 如果截图不存在
    """
    result = await db.execute(
        select(Frame).where(Frame.filename == frame_filename)
    )
    frame = result.scalar_one_or_none()
    
    if not frame:
        raise ValueError("截图不存在")
    
    return {
        "filename": frame.filename,
        "annotations": frame.annotations if frame.annotations else []
    }


async def update_frame_annotations(
    db: AsyncSession,
    frame_filename: str,
    annotations: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """更新截图的标注数据
    
    Args:
        db: 数据库会话
        frame_filename: 截图文件名
        annotations: 标注数据列表
    
    Returns:
        更新后的截图信息
    
    Raises:
        ValueError: 如果截图不存在
    """
    result = await db.execute(
        select(Frame).where(Frame.filename == frame_filename)
    )
    frame = result.scalar_one_or_none()
    
    if not frame:
        raise ValueError("截图不存在")
    
    frame.annotations = annotations
    await db.commit()
    await db.refresh(frame)
    
    return {
        "filename": frame.filename,
        "annotations": frame.annotations
    }


async def get_frames_by_video(db: AsyncSession, video_filename: str) -> List[Dict[str, Any]]:
    """根据视频获取关联的截图列表
    
    Args:
        db: 数据库会话
        video_filename: 视频文件名
    
    Returns:
        截图列表
    """
    # 查找视频
    result = await db.execute(
        select(Video).where(Video.filename == video_filename)
    )
    video = result.scalar_one_or_none()
    
    if not video:
        return []
    
    # 查找关联的截图
    result = await db.execute(
        select(Frame)
        .where(Frame.video_id == video.id)
        .order_by(Frame.created_at.desc())
    )
    frames = result.scalars().all()
    
    return [
        {
            "filename": frame.filename,
            "path": frame.path,
            "created_at": frame.created_at.timestamp(),
            "video_filename": video_filename
        }
        for frame in frames
    ]


async def rename_frame(db: AsyncSession, old_name: str, new_name: str) -> None:
    """重命名截图
    
    Args:
        db: 数据库会话
        old_name: 旧文件名
        new_name: 新文件名
    
    Raises:
        ValueError: 如果文件不存在或新文件名已存在
    """
    # 查找截图
    result = await db.execute(
        select(Frame).where(Frame.filename == old_name)
    )
    frame = result.scalar_one_or_none()
    
    if not frame:
        raise ValueError("源文件不存在")
    
    # 检查新文件名是否已存在
    result = await db.execute(
        select(Frame).where(Frame.filename == new_name)
    )
    if result.scalar_one_or_none():
        raise ValueError("目标文件名已存在")
    
    # 重命名文件
    old_path = FRAME_DIR / old_name
    new_path = FRAME_DIR / new_name
    
    if not old_path.exists():
        raise ValueError("文件不存在")
    
    if not rename_file(old_path, new_path):
        raise ValueError("重命名失败")
    
    # 更新数据库
    frame.filename = new_name
    frame.path = f"/uploads/frames/{new_name}"
    await db.commit()


async def delete_frame(db: AsyncSession, filename: str) -> None:
    """删除截图
    
    Args:
        db: 数据库会话
        filename: 文件名
    
    Raises:
        ValueError: 如果文件不存在
    """
    # 查找截图
    result = await db.execute(
        select(Frame).where(Frame.filename == filename)
    )
    frame = result.scalar_one_or_none()
    
    if not frame:
        raise ValueError("文件不存在")
    
    # 删除文件
    filepath = FRAME_DIR / filename
    delete_file(filepath)
    
    # 从数据库删除
    await db.delete(frame)
    await db.commit()
