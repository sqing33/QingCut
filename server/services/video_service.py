"""视频管理业务逻辑"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from database import Video, VideoClass, Frame
from config import VIDEO_DIR
from utils.file_utils import save_uploaded_file, generate_unique_filename, delete_file, rename_file


async def create_video(
    db: AsyncSession,
    upload_file,
    original_filename: str
) -> Dict[str, Any]:
    """创建视频记录并保存文件
    
    Args:
        db: 数据库会话
        upload_file: 上传的文件对象
        original_filename: 原始文件名
    
    Returns:
        包含视频信息的字典
    """
    # 生成唯一文件名
    filename = generate_unique_filename(original_filename, VIDEO_DIR)
    renamed = filename != original_filename
    
    # 保存文件
    filepath = VIDEO_DIR / filename
    save_uploaded_file(upload_file, filepath)
    
    # 保存到数据库
    db_video = Video(
        filename=filename,
        path=f"/uploads/videos/{filename}",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    db.add(db_video)
    await db.commit()
    await db.refresh(db_video)
    
    return {
        "url": f"/uploads/videos/{filename}",
        "filename": filename,
        "original_filename": original_filename,
        "renamed": renamed
    }


async def get_all_videos(db: AsyncSession) -> List[Dict[str, Any]]:
    """获取所有视频列表
    
    Args:
        db: 数据库会话
    
    Returns:
        视频列表
    """
    result = await db.execute(
        select(Video).order_by(Video.created_at.desc())
    )
    videos = result.scalars().all()
    
    return [
        {
            "filename": video.filename,
            "path": video.path,
            "created_at": video.created_at.timestamp()
        }
        for video in videos
    ]


async def rename_video(
    db: AsyncSession,
    old_name: str,
    new_name: str
) -> None:
    """重命名视频
    
    Args:
        db: 数据库会话
        old_name: 旧文件名
        new_name: 新文件名
    
    Raises:
        ValueError: 如果文件不存在或新文件名已存在
    """
    # 查找视频
    result = await db.execute(
        select(Video).where(Video.filename == old_name)
    )
    video = result.scalar_one_or_none()
    
    if not video:
        raise ValueError("源文件不存在")
    
    # 检查新文件名是否已存在
    result = await db.execute(
        select(Video).where(Video.filename == new_name)
    )
    if result.scalar_one_or_none():
        raise ValueError("目标文件名已存在")
    
    # 重命名文件
    old_path = VIDEO_DIR / old_name
    new_path = VIDEO_DIR / new_name
    
    if not old_path.exists():
        raise ValueError("文件不存在")
    
    if not rename_file(old_path, new_path):
        raise ValueError("重命名失败")
    
    # 更新数据库
    video.filename = new_name
    video.path = f"/uploads/videos/{new_name}"
    video.updated_at = datetime.now()
    await db.commit()


async def delete_video(db: AsyncSession, filename: str) -> None:
    """删除视频
    
    Args:
        db: 数据库会话
        filename: 文件名
    
    Raises:
        ValueError: 如果文件不存在
    """
    # 查找视频
    result = await db.execute(
        select(Video).where(Video.filename == filename)
    )
    video = result.scalar_one_or_none()
    
    if not video:
        raise ValueError("文件不存在")
    
    # 删除文件
    filepath = VIDEO_DIR / filename
    delete_file(filepath)
    
    # 从数据库删除（级联删除关联的截图记录）
    await db.delete(video)
    await db.commit()


async def get_video_classes(db: AsyncSession, video_id: int) -> List[Dict[str, Any]]:
    """获取视频关联的类名
    
    Args:
        db: 数据库会话
        video_id: 视频ID
    
    Returns:
        类名列表
    
    Raises:
        ValueError: 如果视频不存在
    """
    from database import Class
    
    # 查找视频
    result = await db.execute(
        select(Video).where(Video.id == video_id)
    )
    video = result.scalar_one_or_none()
    
    if not video:
        raise ValueError("视频不存在")
    
    # 查找关联的类名
    result = await db.execute(
        select(VideoClass).where(VideoClass.video_id == video_id)
    )
    video_classes = result.scalars().all()
    
    # 获取完整的类名信息
    class_ids = [vc.class_id for vc in video_classes]
    if class_ids:
        result = await db.execute(
            select(Class).where(Class.id.in_(class_ids))
        )
        classes = result.scalars().all()
    else:
        classes = []
    
    return [
        {
            "id": cls.id,
            "name": cls.name,
            "color": cls.color
        }
        for cls in classes
    ]


async def bind_classes_to_video(
    db: AsyncSession,
    video_id: int,
    class_ids: List[int]
) -> None:
    """绑定类名到视频
    
    Args:
        db: 数据库会话
        video_id: 视频ID
        class_ids: 类名ID列表
    
    Raises:
        ValueError: 如果视频不存在
    """
    # 查找视频
    result = await db.execute(
        select(Video).where(Video.id == video_id)
    )
    video = result.scalar_one_or_none()
    
    if not video:
        raise ValueError("视频不存在")
    
    # 删除现有关联
    await db.execute(
        delete(VideoClass).where(VideoClass.video_id == video_id)
    )
    
    # 添加新关联
    for class_id in class_ids:
        db_video_class = VideoClass(
            video_id=video_id,
            class_id=class_id,
            created_at=datetime.now()
        )
        db.add(db_video_class)
    
    await db.commit()
