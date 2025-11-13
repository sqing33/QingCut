"""视频管理路由"""
from fastapi import APIRouter, File, UploadFile, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from services import video_service

router = APIRouter(prefix="/api", tags=["videos"])


@router.post("/upload-video")
async def upload_video(
    video: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """上传视频文件"""
    try:
        if not video.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        
        result = await video_service.create_video(db, video, video.filename)
        return {"success": True, **result}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/videos")
async def list_videos(db: AsyncSession = Depends(get_db)):
    """列出所有已上传的视频"""
    try:
        videos = await video_service.get_all_videos(db)
        return {"videos": videos}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rename-video")
async def rename_video(data: dict, db: AsyncSession = Depends(get_db)):
    """重命名视频文件"""
    old_name = data.get("old_name")
    new_name = data.get("new_name")
    
    if not old_name or not new_name:
        raise HTTPException(status_code=400, detail="缺少文件名参数")
    
    try:
        await video_service.rename_video(db, old_name, new_name)
        return {"success": True, "message": "重命名成功"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/delete-video")
async def delete_video(data: dict, db: AsyncSession = Depends(get_db)):
    """删除视频文件"""
    filename = data.get("filename")
    
    if not filename:
        raise HTTPException(status_code=400, detail="缺少文件名参数")
    
    try:
        await video_service.delete_video(db, filename)
        return {"success": True, "message": "删除成功"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/videos/{video_id}/classes")
async def get_video_classes(video_id: int, db: AsyncSession = Depends(get_db)):
    """获取视频关联的类名"""
    try:
        classes = await video_service.get_video_classes(db, video_id)
        return {"video_id": video_id, "classes": classes}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/videos/{video_id}/classes")
async def bind_classes_to_video(
    video_id: int,
    data: dict,
    db: AsyncSession = Depends(get_db)
):
    """绑定类名到视频"""
    class_ids = data.get("class_ids", [])
    
    try:
        await video_service.bind_classes_to_video(db, video_id, class_ids)
        return {"success": True, "message": "绑定成功"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
