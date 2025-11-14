"""类名和类名组管理业务逻辑"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from typing import List, Dict, Any, Optional

from database import Class, ClassGroup, ClassGroupItem


async def get_all_classes(db: AsyncSession) -> List[Dict[str, Any]]:
    """获取所有类名
    
    Args:
        db: 数据库会话
    
    Returns:
        类名列表
    """
    result = await db.execute(
        select(Class).order_by(Class.created_at)
    )
    classes = result.scalars().all()
    
    return [
        {
            "id": cls.id,
            "name": cls.name,
            "name_en": cls.name_en,
            "color": cls.color,
            "created_at": cls.created_at.timestamp()
        }
        for cls in classes
    ]


async def create_class(
    db: AsyncSession,
    name: str,
    name_en: str,
    color: str = "#00ff00",
    group_id: Optional[int] = None
) -> Dict[str, Any]:
    """创建新类名
    
    Args:
        db: 数据库会话
        name: 中文类名
        name_en: 英文类名
        color: 颜色
        group_id: 可选的组ID，创建时直接添加到组
    
    Returns:
        创建的类名信息
    """
    # 创建类名
    db_class = Class(
        name=name,
        name_en=name_en,
        color=color,
        created_at=datetime.now()
    )
    db.add(db_class)
    await db.commit()
    await db.refresh(db_class)
    
    # 如果指定了组，添加到组
    if group_id:
        db_item = ClassGroupItem(
            group_id=group_id,
            class_id=db_class.id,
            order=0,
            created_at=datetime.now()
        )
        db.add(db_item)
        await db.commit()
    
    return {
        "id": db_class.id,
        "name": db_class.name,
        "name_en": db_class.name_en,
        "color": db_class.color,
        "created_at": db_class.created_at.timestamp()
    }


async def update_class(
    db: AsyncSession,
    class_id: int,
    name: Optional[str] = None,
    color: Optional[str] = None
) -> Dict[str, Any]:
    """更新类名
    
    Args:
        db: 数据库会话
        class_id: 类名ID
        name: 新名称
        color: 新颜色
    
    Returns:
        更新后的类名信息
    
    Raises:
        ValueError: 如果类名不存在
    """
    result = await db.execute(
        select(Class).where(Class.id == class_id)
    )
    cls = result.scalar_one_or_none()
    
    if not cls:
        raise ValueError("类名不存在")
    
    if name is not None:
        cls.name = name
    
    if color is not None:
        cls.color = color
    
    await db.commit()
    await db.refresh(cls)
    
    return {
        "id": cls.id,
        "name": cls.name,
        "color": cls.color,
        "created_at": cls.created_at.timestamp()
    }


async def delete_class(db: AsyncSession, class_id: int) -> None:
    """删除类名
    
    Args:
        db: 数据库会话
        class_id: 类名ID
    
    Raises:
        ValueError: 如果类名不存在
    """
    result = await db.execute(
        select(Class).where(Class.id == class_id)
    )
    cls = result.scalar_one_or_none()
    
    if not cls:
        raise ValueError("类名不存在")
    
    await db.delete(cls)
    await db.commit()


# ==================== 类名组管理 ====================


async def get_all_class_groups(db: AsyncSession) -> List[Dict[str, Any]]:
    """获取所有类名组
    
    Args:
        db: 数据库会话
    
    Returns:
        类名组列表
    """
    result = await db.execute(
        select(ClassGroup).order_by(ClassGroup.created_at)
    )
    groups = result.scalars().all()
    
    return [
        {
            "id": group.id,
            "name": group.name,
            "description": group.description,
            "created_at": group.created_at.timestamp()
        }
        for group in groups
    ]


async def create_class_group(
    db: AsyncSession,
    name: str,
    description: str = ""
) -> Dict[str, Any]:
    """创建新类名组
    
    Args:
        db: 数据库会话
        name: 组名
        description: 描述
    
    Returns:
        创建的类名组信息
    
    Raises:
        ValueError: 如果组名已存在
    """
    # 检查组名是否已存在
    result = await db.execute(
        select(ClassGroup).where(ClassGroup.name == name)
    )
    if result.scalar_one_or_none():
        raise ValueError("组名已存在")
    
    # 创建类名组
    db_group = ClassGroup(
        name=name,
        description=description,
        created_at=datetime.now()
    )
    db.add(db_group)
    await db.commit()
    await db.refresh(db_group)
    
    return {
        "id": db_group.id,
        "name": db_group.name,
        "description": db_group.description,
        "created_at": db_group.created_at.timestamp()
    }


async def update_class_group(
    db: AsyncSession,
    group_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None
) -> Dict[str, Any]:
    """更新类名组
    
    Args:
        db: 数据库会话
        group_id: 组ID
        name: 新名称
        description: 新描述
    
    Returns:
        更新后的类名组信息
    
    Raises:
        ValueError: 如果组不存在或新名称已被使用
    """
    result = await db.execute(
        select(ClassGroup).where(ClassGroup.id == group_id)
    )
    group = result.scalar_one_or_none()
    
    if not group:
        raise ValueError("类名组不存在")
    
    if name is not None:
        # 检查新名称是否与其他组冲突
        result = await db.execute(
            select(ClassGroup).where(
                ClassGroup.name == name,
                ClassGroup.id != group_id
            )
        )
        if result.scalar_one_or_none():
            raise ValueError("组名已存在")
        group.name = name
    
    if description is not None:
        group.description = description
    
    await db.commit()
    await db.refresh(group)
    
    return {
        "id": group.id,
        "name": group.name,
        "description": group.description,
        "created_at": group.created_at.timestamp()
    }


async def delete_class_group(db: AsyncSession, group_id: int) -> None:
    """删除类名组
    
    Args:
        db: 数据库会话
        group_id: 组ID
    
    Raises:
        ValueError: 如果组不存在
    """
    result = await db.execute(
        select(ClassGroup).where(ClassGroup.id == group_id)
    )
    group = result.scalar_one_or_none()
    
    if not group:
        raise ValueError("类名组不存在")
    
    await db.delete(group)
    await db.commit()


async def get_group_classes(db: AsyncSession, group_id: int) -> Dict[str, Any]:
    """获取类名组中的所有类名
    
    Args:
        db: 数据库会话
        group_id: 组ID
    
    Returns:
        包含组信息和类名列表的字典
    
    Raises:
        ValueError: 如果组不存在
    """
    # 查找类名组
    result = await db.execute(
        select(ClassGroup).where(ClassGroup.id == group_id)
    )
    group = result.scalar_one_or_none()
    
    if not group:
        raise ValueError("类名组不存在")
    
    # 查找组内的类名
    result = await db.execute(
        select(ClassGroupItem)
        .where(ClassGroupItem.group_id == group_id)
        .order_by(ClassGroupItem.order)
    )
    items = result.scalars().all()
    
    # 获取完整的类名信息
    class_ids = [item.class_id for item in items]
    if class_ids:
        result = await db.execute(
            select(Class).where(Class.id.in_(class_ids))
        )
        classes_dict = {cls.id: cls for cls in result.scalars().all()}
        
        return {
            "group_id": group_id,
            "group_name": group.name,
            "classes": [
                {
                    "id": classes_dict[item.class_id].id,
                    "name": classes_dict[item.class_id].name,
                    "name_en": classes_dict[item.class_id].name_en,
                    "color": classes_dict[item.class_id].color,
                    "order": item.order
                }
                for item in items if item.class_id in classes_dict
            ]
        }
    else:
        return {
            "group_id": group_id,
            "group_name": group.name,
            "classes": []
        }


async def add_class_to_group(db: AsyncSession, group_id: int, class_id: int) -> None:
    """添加类名到组
    
    Args:
        db: 数据库会话
        group_id: 组ID
        class_id: 类名ID
    
    Raises:
        ValueError: 如果组不存在、类名不存在或已在组内
    """
    # 检查组是否存在
    result = await db.execute(
        select(ClassGroup).where(ClassGroup.id == group_id)
    )
    if not result.scalar_one_or_none():
        raise ValueError("类名组不存在")
    
    # 检查类名是否存在
    result = await db.execute(
        select(Class).where(Class.id == class_id)
    )
    if not result.scalar_one_or_none():
        raise ValueError("类名不存在")
    
    # 检查是否已存在
    result = await db.execute(
        select(ClassGroupItem).where(
            ClassGroupItem.group_id == group_id,
            ClassGroupItem.class_id == class_id
        )
    )
    if result.scalar_one_or_none():
        raise ValueError("该类名已在组内")
    
    # 添加到组
    db_item = ClassGroupItem(
        group_id=group_id,
        class_id=class_id,
        order=0,
        created_at=datetime.now()
    )
    db.add(db_item)
    await db.commit()


async def remove_class_from_group(db: AsyncSession, group_id: int, class_id: int) -> None:
    """从组中移除类名
    
    Args:
        db: 数据库会话
        group_id: 组ID
        class_id: 类名ID
    
    Raises:
        ValueError: 如果该类名不在组内
    """
    result = await db.execute(
        select(ClassGroupItem).where(
            ClassGroupItem.group_id == group_id,
            ClassGroupItem.class_id == class_id
        )
    )
    item = result.scalar_one_or_none()
    
    if not item:
        raise ValueError("该类名不在组内")
    
    await db.delete(item)
    await db.commit()
