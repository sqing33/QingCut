"""YOLO 数据集导出路由"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from services import export_service

router = APIRouter(prefix="/api/export", tags=["export"])


@router.get("/yolo/{video_filename}")
async def export_yolo_by_video(
    video_filename: str,
    db: AsyncSession = Depends(get_db)
):
    """导出指定视频的YOLO格式数据集"""
    try:
        result = await export_service.export_yolo_by_video(db, video_filename)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/yolo")
async def export_all_yolo(db: AsyncSession = Depends(get_db)):
    """导出所有视频的YOLO格式数据集"""
    try:
        result = await export_service.export_all_yolo(db)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/yolo-dataset")
async def export_yolo_dataset_to_folder(
    data: dict,
    db: AsyncSession = Depends(get_db)
):
    """将YOLO数据集导出到指定文件夹"""
    try:
        name = data.get("name", "未命名数据集")
        identifier = data.get("identifier")
        video_filenames = data.get("video_filenames")
        append_mode = data.get("append_mode", False)
        
        if not identifier:
            raise HTTPException(status_code=400, detail="缺少标识符参数")
        
        result = await export_service.export_yolo_dataset_to_folder(
            db, name, identifier, video_filenames, append_mode
        )
        
        return {"success": True, **result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
