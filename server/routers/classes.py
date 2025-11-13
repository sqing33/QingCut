"""类名和类名组管理路由"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from services import class_service

router = APIRouter(prefix="/api", tags=["classes"])


# ==================== 类名管理 ====================


@router.get("/classes")
async def list_classes(db: AsyncSession = Depends(get_db)):
    """获取所有类名"""
    try:
        classes = await class_service.get_all_classes(db)
        return {"classes": classes}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/classes")
async def create_class(data: dict, db: AsyncSession = Depends(get_db)):
    """创建新类名"""
    name = data.get("name")
    color = data.get("color", "#00ff00")
    group_id = data.get("group_id")
    
    if not name:
        raise HTTPException(status_code=400, detail="类名不能为空")
    
    try:
        cls = await class_service.create_class(db, name, color, group_id)
        return {"success": True, "class": cls}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/classes/{class_id}")
async def delete_class(class_id: int, db: AsyncSession = Depends(get_db)):
    """删除类名"""
    try:
        await class_service.delete_class(db, class_id)
        return {"success": True, "message": "删除成功"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/classes/{class_id}")
async def update_class(class_id: int, data: dict, db: AsyncSession = Depends(get_db)):
    """更新类名"""
    try:
        name = data.get("name")
        color = data.get("color")
        cls = await class_service.update_class(db, class_id, name, color)
        return {"success": True, "class": cls}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 类名组管理 ====================


@router.get("/class-groups")
async def list_class_groups(db: AsyncSession = Depends(get_db)):
    """获取所有类名组"""
    try:
        groups = await class_service.get_all_class_groups(db)
        return {"groups": groups}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/class-groups")
async def create_class_group(data: dict, db: AsyncSession = Depends(get_db)):
    """创建新类名组"""
    name = data.get("name")
    description = data.get("description", "")
    
    if not name:
        raise HTTPException(status_code=400, detail="组名不能为空")
    
    try:
        group = await class_service.create_class_group(db, name, description)
        return {"success": True, "group": group}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/class-groups/{group_id}")
async def update_class_group(
    group_id: int,
    data: dict,
    db: AsyncSession = Depends(get_db)
):
    """更新类名组"""
    try:
        name = data.get("name")
        description = data.get("description")
        group = await class_service.update_class_group(db, group_id, name, description)
        return {"success": True, "group": group}
    except ValueError as e:
        if "不存在" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        else:
            raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/class-groups/{group_id}")
async def delete_class_group(group_id: int, db: AsyncSession = Depends(get_db)):
    """删除类名组"""
    try:
        await class_service.delete_class_group(db, group_id)
        return {"success": True, "message": "删除成功"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/class-groups/{group_id}/classes")
async def get_group_classes(group_id: int, db: AsyncSession = Depends(get_db)):
    """获取类名组中的所有类名"""
    try:
        result = await class_service.get_group_classes(db, group_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/class-groups/{group_id}/classes")
async def add_class_to_group(
    group_id: int,
    data: dict,
    db: AsyncSession = Depends(get_db)
):
    """添加类名到组"""
    class_id = data.get("class_id")
    
    if not class_id:
        raise HTTPException(status_code=400, detail="缺少class_id参数")
    
    try:
        await class_service.add_class_to_group(db, group_id, class_id)
        return {"success": True, "message": "添加成功"}
    except ValueError as e:
        if "不存在" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        else:
            raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/class-groups/{group_id}/classes/{class_id}")
async def remove_class_from_group(
    group_id: int,
    class_id: int,
    db: AsyncSession = Depends(get_db)
):
    """从组中移除类名"""
    try:
        await class_service.remove_class_from_group(db, group_id, class_id)
        return {"success": True, "message": "移除成功"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
