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


@router.get("/yolo-dataset-zip/{dataset_identifier}")
async def export_yolo_dataset_as_zip(
    dataset_identifier: str,
    db: AsyncSession = Depends(get_db)
):
    """将现有YOLO数据集导出为ZIP文件下载"""
    try:
        zip_content, zip_filename = await export_service.export_yolo_dataset_as_zip(
            db, dataset_identifier
        )

        # 返回ZIP文件
        from fastapi.responses import StreamingResponse
        from io import BytesIO
        from urllib.parse import quote

        def iter_file(content: bytes):
            yield content

        # 对中文文件名进行URL编码，确保支持中文
        encoded_filename = quote(zip_filename.encode('utf-8'))

        return StreamingResponse(
            iter_file(zip_content),
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"}
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
