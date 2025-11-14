"""数据集管理业务逻辑"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import shutil

from database import Frame, Dataset, FrameDataset
from config import DATASET_DIR


async def get_all_datasets() -> List[Dict[str, Any]]:
    """获取所有已存在的数据集（从文件系统）
    
    Returns:
        数据集列表
    """
    if not DATASET_DIR.exists():
        return []
    
    datasets = []
    for dataset_dir in DATASET_DIR.iterdir():
        if dataset_dir.is_dir():
            info_file = dataset_dir / "dataset_info.txt"
            images_dir = dataset_dir / "images"
            
            # 读取数据集信息
            name = dataset_dir.name

            # 分别统计训练集和验证集的图片数量
            train_images_dir = dataset_dir / "train" / "images"
            val_images_dir = dataset_dir / "val" / "images"

            train_image_count = len(list(train_images_dir.glob("*.png"))) if train_images_dir.exists() else 0
            val_image_count = len(list(val_images_dir.glob("*.png"))) if val_images_dir.exists() else 0
            total_image_count = train_image_count + val_image_count
            
            if info_file.exists():
                try:
                    with info_file.open('r', encoding='utf-8') as f:
                        content = f.read()
                        # 解析名称
                        for line in content.split('\n'):
                            if line.startswith('数据集名称:'):
                                name = line.split(':', 1)[1].strip()
                                break
                except:
                    pass
            
            datasets.append({
                "identifier": dataset_dir.name,
                "name": name,
                "image_count": total_image_count,  # 总图片数量
                "train_images": train_image_count,  # 训练集图片数量
                "val_images": val_image_count,      # 验证集图片数量
                "total_images": total_image_count    # 总图片数量（兼容现有代码）
            })
    
    return datasets


async def get_frame_datasets(db: AsyncSession, frame_filename: str) -> List[Dict[str, str]]:
    """获取图片所属的所有数据集
    
    Args:
        db: 数据库会话
        frame_filename: 图片文件名
    
    Returns:
        数据集列表
    
    Raises:
        ValueError: 如果图片不存在
    """
    # 查找图片
    result = await db.execute(
        select(Frame).where(Frame.filename == frame_filename)
    )
    frame = result.scalar_one_or_none()
    
    if not frame:
        raise ValueError("图片不存在")
    
    # 查找关联的数据集
    result = await db.execute(
        select(FrameDataset).where(FrameDataset.frame_id == frame.id)
    )
    frame_datasets = result.scalars().all()
    
    # 获取数据集信息
    dataset_ids = [fd.dataset_id for fd in frame_datasets]
    datasets = []
    if dataset_ids:
        result = await db.execute(
            select(Dataset).where(Dataset.id.in_(dataset_ids))
        )
        datasets = [
            {"identifier": d.identifier, "name": d.name}
            for d in result.scalars().all()
        ]
    
    return datasets


async def update_frame_datasets(
    db: AsyncSession,
    frame_filename: str,
    dataset_identifiers: List[str]
) -> None:
    """更新图片所属的数据集
    
    Args:
        db: 数据库会话
        frame_filename: 图片文件名
        dataset_identifiers: 数据集标识符列表
    
    Raises:
        ValueError: 如果图片不存在
    """
    # 查找图片
    result = await db.execute(
        select(Frame).where(Frame.filename == frame_filename)
    )
    frame = result.scalar_one_or_none()
    
    if not frame:
        raise ValueError("图片不存在")
    
    # 删除现有关联
    await db.execute(
        delete(FrameDataset).where(FrameDataset.frame_id == frame.id)
    )
    
    # 创建新关联
    for identifier in dataset_identifiers:
        # 查找或创建数据集
        result = await db.execute(
            select(Dataset).where(Dataset.identifier == identifier)
        )
        dataset = result.scalar_one_or_none()
        
        if not dataset:
            # 创建新数据集记录
            dataset = Dataset(
                identifier=identifier,
                name=identifier,
                created_at=datetime.now()
            )
            db.add(dataset)
            await db.flush()
        
        # 创建关联
        frame_dataset = FrameDataset(
            frame_id=frame.id,
            dataset_id=dataset.id,
            created_at=datetime.now()
        )
        db.add(frame_dataset)
    
    await db.commit()


async def batch_assign_dataset(
    db: AsyncSession,
    frame_filenames: List[str],
    dataset_identifier: Optional[str]
) -> int:
    """批量分配图片到数据集（向后兼容）
    
    Args:
        db: 数据库会话
        frame_filenames: 图片文件名列表
        dataset_identifier: 数据集标识符，None表示取消分配
    
    Returns:
        成功分配的图片数量
    """
    count = 0
    for filename in frame_filenames:
        result = await db.execute(
            select(Frame).where(Frame.filename == filename)
        )
        frame = result.scalar_one_or_none()
        if frame:
            frame.dataset_identifier = dataset_identifier
            count += 1
    
    await db.commit()
    return count


async def update_dataset_name(db: AsyncSession, identifier: str, new_name: str) -> None:
    """更新数据集名称
    
    Args:
        db: 数据库会话
        identifier: 数据集标识符
        new_name: 新名称
    
    Raises:
        ValueError: 如果数据集不存在
    """
    # 查找数据集
    result = await db.execute(
        select(Dataset).where(Dataset.identifier == identifier)
    )
    dataset = result.scalar_one_or_none()
    
    if not dataset:
        raise ValueError("数据集不存在")
    
    # 更新名称
    dataset.name = new_name
    await db.commit()
    
    # 更新dataset_info.txt文件
    dataset_dir = DATASET_DIR / identifier
    info_file = dataset_dir / "dataset_info.txt"
    
    if info_file.exists():
        # 读取现有内容并更新名称
        with info_file.open('r', encoding='utf-8') as f:
            lines = f.readlines()
        
        with info_file.open('w', encoding='utf-8') as f:
            for line in lines:
                if line.startswith('数据集名称:'):
                    f.write(f'数据集名称: {new_name}\n')
                else:
                    f.write(line)


async def delete_dataset(db: AsyncSession, identifier: str) -> None:
    """删除指定数据集及其所有文件
    
    Args:
        db: 数据库会话
        identifier: 数据集标识符
    
    Raises:
        ValueError: 如果数据集不存在
    """
    # 查找数据集
    result = await db.execute(
        select(Dataset).where(Dataset.identifier == identifier)
    )
    dataset = result.scalar_one_or_none()
    
    if not dataset:
        raise ValueError("数据集不存在")
    
    # 删除文件系统中的数据集目录
    dataset_dir = DATASET_DIR / identifier
    if dataset_dir.exists():
        shutil.rmtree(dataset_dir)
    
    # 删除数据库中的关联记录
    await db.execute(
        delete(FrameDataset).where(FrameDataset.dataset_id == dataset.id)
    )
    
    # 删除数据集记录
    await db.delete(dataset)
    await db.commit()
