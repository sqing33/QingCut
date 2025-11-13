"""截图管理路由"""
from fastapi import APIRouter, File, UploadFile, HTTPException, Form, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from database import get_db
from services import frame_service

router = APIRouter(prefix="/api", tags=["frames"])


@router.post("/save-frame")
async def save_frame(
    image: UploadFile = File(...),
    video_filename: Optional[str] = Form(None),
    class_id: Optional[int] = Form(None),
    annotation: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db)
):
    """保存截取的帧（单标注模式）"""
    try:
        result = await frame_service.create_frame(
            db, image, video_filename, class_id, annotation
        )
        return {"success": True, **result}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/save-frame-multi")
async def save_frame_multi(
    image: UploadFile = File(...),
    video_filename: Optional[str] = Form(None),
    annotations: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db)
):
    """保存截取的帧（多标注模式）"""
    try:
        result = await frame_service.create_frame_multi(
            db, image, video_filename, annotations
        )
        return {"success": True, **result}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/frames")
async def list_frames(db: AsyncSession = Depends(get_db)):
    """列出所有截取的帧"""
    try:
        frames = await frame_service.get_all_frames(db)
        return {"frames": frames}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/frames/{frame_filename}/annotations")
async def get_frame_annotations(
    frame_filename: str,
    db: AsyncSession = Depends(get_db)
):
    """获取指定截图的标注数据"""
    try:
        result = await frame_service.get_frame_annotations(db, frame_filename)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/frames/{frame_filename}/annotations")
async def update_frame_annotations(
    frame_filename: str,
    data: dict,
    db: AsyncSession = Depends(get_db)
):
    """更新指定截图的标注数据"""
    try:
        annotations = data.get("annotations", [])
        result = await frame_service.update_frame_annotations(
            db, frame_filename, annotations
        )
        return {"success": True, **result}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/frames/{video_filename}")
async def list_frames_by_video(
    video_filename: str,
    db: AsyncSession = Depends(get_db)
):
    """根据视频文件名列出关联的截图"""
    try:
        frames = await frame_service.get_frames_by_video(db, video_filename)
        return {"frames": frames}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rename-frame")
async def rename_frame(data: dict, db: AsyncSession = Depends(get_db)):
    """重命名截图文件"""
    old_name = data.get("old_name")
    new_name = data.get("new_name")
    
    if not old_name or not new_name:
        raise HTTPException(status_code=400, detail="缺少文件名参数")
    
    try:
        await frame_service.rename_frame(db, old_name, new_name)
        return {"success": True, "message": "重命名成功"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/delete-frame")
async def delete_frame(data: dict, db: AsyncSession = Depends(get_db)):
    """删除截图文件"""
    filename = data.get("filename")
    
    if not filename:
        raise HTTPException(status_code=400, detail="缺少文件名参数")
    
    try:
        await frame_service.delete_frame(db, filename)
        return {"success": True, "message": "删除成功"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
