"""数据集管理路由"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from services import dataset_service

router = APIRouter(prefix="/api", tags=["datasets"])


@router.get("/datasets")
async def list_datasets():
    """列出所有已存在的数据集"""
    try:
        datasets = await dataset_service.get_all_datasets()
        return {"datasets": datasets}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/frames/{frame_filename}/datasets")
async def get_frame_datasets(
    frame_filename: str,
    db: AsyncSession = Depends(get_db)
):
    """获取图片所属的所有数据集"""
    try:
        datasets = await dataset_service.get_frame_datasets(db, frame_filename)
        return {"filename": frame_filename, "datasets": datasets}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/frames/{frame_filename}/datasets")
async def update_frame_datasets(
    frame_filename: str,
    data: dict,
    db: AsyncSession = Depends(get_db)
):
    """更新图片所属的数据集"""
    try:
        dataset_identifiers = data.get("dataset_identifiers", [])
        await dataset_service.update_frame_datasets(
            db, frame_filename, dataset_identifiers
        )
        return {
            "success": True,
            "message": "数据集归属已更新",
            "datasets": dataset_identifiers
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/frames/batch-assign-dataset")
async def batch_assign_dataset(data: dict, db: AsyncSession = Depends(get_db)):
    """批量分配图片到数据集（向后兼容）"""
    try:
        frame_filenames = data.get("frame_filenames", [])
        dataset_identifier = data.get("dataset_identifier")
        
        if not frame_filenames:
            raise HTTPException(status_code=400, detail="未选择任何图片")
        
        count = await dataset_service.batch_assign_dataset(
            db, frame_filenames, dataset_identifier
        )
        
        return {
            "success": True,
            "message": f"已将 {count} 张图片分配到数据集",
            "count": count
        }
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/datasets/{dataset_identifier}")
async def update_dataset(
    dataset_identifier: str,
    data: dict,
    db: AsyncSession = Depends(get_db)
):
    """更新数据集名称"""
    new_name = data.get("name")
    if not new_name:
        raise HTTPException(status_code=400, detail="缺少名称参数")
    
    try:
        await dataset_service.update_dataset_name(db, dataset_identifier, new_name)
        return {
            "success": True,
            "message": "数据集名称已更新",
            "dataset": {
                "identifier": dataset_identifier,
                "name": new_name
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/datasets/{dataset_identifier}")
async def delete_dataset(
    dataset_identifier: str,
    db: AsyncSession = Depends(get_db)
):
    """删除指定数据集及其所有文件"""
    try:
        await dataset_service.delete_dataset(db, dataset_identifier)
        return {"success": True, "message": f"数据集已删除"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
