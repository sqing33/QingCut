from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from pathlib import Path
from typing import Optional
import shutil
from datetime import datetime

from database import get_db, init_db, Video, Frame, Class, VideoClass

app = FastAPI()

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 创建必要的目录
UPLOAD_DIR = Path("uploads")
VIDEO_DIR = UPLOAD_DIR / "videos"
FRAME_DIR = UPLOAD_DIR / "frames"

VIDEO_DIR.mkdir(parents=True, exist_ok=True)
FRAME_DIR.mkdir(parents=True, exist_ok=True)

# 挂载静态文件目录
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


@app.on_event("startup")
async def startup_event():
    """应用启动时初始化数据库"""
    await init_db()
    print("数据库初始化完成")


@app.post("/api/upload-video")
async def upload_video(
    video: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """上传视频文件"""
    try:
        if not video.filename:
            raise HTTPException(status_code=400, detail="No filename provided")

        original_filename = video.filename
        filepath = VIDEO_DIR / original_filename

        # 检查文件是否已存在
        renamed = False
        if filepath.exists():
            # 文件已存在，添加时间戳重命名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            name_parts = original_filename.rsplit('.', 1)
            if len(name_parts) == 2:
                filename = f"{name_parts[0]}_{timestamp}.{name_parts[1]}"
            else:
                filename = f"{original_filename}_{timestamp}"
            filepath = VIDEO_DIR / filename
            renamed = True
        else:
            filename = original_filename

        # 保存视频文件
        with filepath.open("wb") as buffer:
            shutil.copyfileobj(video.file, buffer)

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
            "success": True,
            "url": f"/uploads/videos/{filename}",
            "filename": filename,
            "original_filename": original_filename,
            "renamed": renamed
        }
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/save-frame")
async def save_frame(
    image: UploadFile = File(...),
    video_filename: Optional[str] = Form(None),
    class_id: Optional[int] = Form(None),
    annotation: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db)
):
    """保存截取的帧，并关联到源视频和类名，支持标注数据"""
    try:
        import json
        
        # 生成唯一文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"frame_{timestamp}.png"
        filepath = FRAME_DIR / filename

        # 保存图片文件
        with filepath.open("wb") as buffer:
            shutil.copyfileobj(image.file, buffer)

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

        return {"success": True, "path": str(filepath), "filename": filename}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/save-frame-multi")
async def save_frame_multi(
    image: UploadFile = File(...),
    video_filename: Optional[str] = Form(None),
    annotations: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db)
):
    """保存截取的帧，支持多个标注"""
    try:
        import json
        
        # 生成唯一文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"frame_{timestamp}.png"
        filepath = FRAME_DIR / filename

        # 保存图片文件
        with filepath.open("wb") as buffer:
            shutil.copyfileobj(image.file, buffer)

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
        annotations_data = {}
        annotations_list = []
        if annotations:
            try:
                annotations_data = json.loads(annotations)
                annotations_list = annotations_data.get('annotations', [])
            except json.JSONDecodeError:
                pass

        # 保存到数据库 - 使用新格式存储多标注
        db_frame = Frame(
            filename=filename,
            path=f"/uploads/frames/{filename}",
            video_id=video_id,
            class_id=None,  # 多标注模式不使用class_id字段
            width=640,
            height=640,
            annotations=annotations_list,  # 直接存储标注数组
            created_at=datetime.now()
        )
        db.add(db_frame)
        await db.commit()
        await db.refresh(db_frame)

        return {
            "success": True,
            "path": str(filepath),
            "filename": filename,
            "annotation_count": len(annotations_list)
        }
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/frames")
async def list_frames(db: AsyncSession = Depends(get_db)):
    """列出所有截取的帧"""
    try:
        result = await db.execute(
            select(Frame).order_by(Frame.created_at.desc())
        )
        frames = result.scalars().all()

        # 获取视频文件名映射
        video_result = await db.execute(select(Video))
        videos = {v.id: v.filename for v in video_result.scalars().all()}

        return {
            "frames": [
                {
                    "filename": frame.filename,
                    "path": frame.path,
                    "created_at": frame.created_at.timestamp(),
                    "video_filename": videos.get(frame.video_id) if frame.video_id else None
                }
                for frame in frames
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/frames/{frame_filename}/annotations")
async def get_frame_annotations(
    frame_filename: str,
    db: AsyncSession = Depends(get_db)
):
    """获取指定截图的标注数据"""
    try:
        # 查找截图
        result = await db.execute(
            select(Frame).where(Frame.filename == frame_filename)
        )
        frame = result.scalar_one_or_none()
        
        if not frame:
            raise HTTPException(status_code=404, detail="截图不存在")
        
        # 返回标注数据
        return {
            "filename": frame.filename,
            "annotations": frame.annotations if frame.annotations else []
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/frames/{frame_filename}/annotations")
async def update_frame_annotations(
    frame_filename: str,
    data: dict,
    db: AsyncSession = Depends(get_db)
):
    """更新指定截图的标注数据"""
    try:
        # 查找截图
        result = await db.execute(
            select(Frame).where(Frame.filename == frame_filename)
        )
        frame = result.scalar_one_or_none()
        
        if not frame:
            raise HTTPException(status_code=404, detail="截图不存在")
        
        # 更新标注数据
        annotations = data.get("annotations", [])
        frame.annotations = annotations
        
        await db.commit()
        await db.refresh(frame)
        
        return {
            "success": True,
            "filename": frame.filename,
            "annotations": frame.annotations
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/frames/{video_filename}")
async def list_frames_by_video(
    video_filename: str,
    db: AsyncSession = Depends(get_db)
):
    """根据视频文件名列出关联的截图"""
    try:
        # 查找视频
        result = await db.execute(
            select(Video).where(Video.filename == video_filename)
        )
        video = result.scalar_one_or_none()
        
        if not video:
            return {"frames": []}

        # 查找关联的截图
        result = await db.execute(
            select(Frame)
            .where(Frame.video_id == video.id)
            .order_by(Frame.created_at.desc())
        )
        frames = result.scalars().all()

        return {
            "frames": [
                {
                    "filename": frame.filename,
                    "path": frame.path,
                    "created_at": frame.created_at.timestamp(),
                    "video_filename": video_filename
                }
                for frame in frames
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/videos")
async def list_videos(db: AsyncSession = Depends(get_db)):
    """列出所有已上传的视频"""
    try:
        result = await db.execute(
            select(Video).order_by(Video.created_at.desc())
        )
        videos = result.scalars().all()

        return {
            "videos": [
                {
                    "filename": video.filename,
                    "path": video.path,
                    "created_at": video.created_at.timestamp()
                }
                for video in videos
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/rename-video")
async def rename_video(data: dict, db: AsyncSession = Depends(get_db)):
    """重命名视频文件"""
    old_name = data.get("old_name")
    new_name = data.get("new_name")
    
    if not old_name or not new_name:
        raise HTTPException(status_code=400, detail="缺少文件名参数")
    
    try:
        # 查找视频
        result = await db.execute(
            select(Video).where(Video.filename == old_name)
        )
        video = result.scalar_one_or_none()
        
        if not video:
            raise HTTPException(status_code=404, detail="源文件不存在")
        
        # 检查新文件名是否已存在
        result = await db.execute(
            select(Video).where(Video.filename == new_name)
        )
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="目标文件名已存在")
        
        # 重命名文件
        old_path = VIDEO_DIR / old_name
        new_path = VIDEO_DIR / new_name
        
        if not old_path.exists():
            raise HTTPException(status_code=404, detail="文件不存在")
        
        old_path.rename(new_path)
        
        # 更新数据库
        video.filename = new_name
        video.path = f"/uploads/videos/{new_name}"
        video.updated_at = datetime.now()
        await db.commit()
        
        return {"success": True, "message": "重命名成功"}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/delete-video")
async def delete_video(data: dict, db: AsyncSession = Depends(get_db)):
    """删除视频文件"""
    filename = data.get("filename")
    
    if not filename:
        raise HTTPException(status_code=400, detail="缺少文件名参数")
    
    try:
        # 查找视频
        result = await db.execute(
            select(Video).where(Video.filename == filename)
        )
        video = result.scalar_one_or_none()
        
        if not video:
            raise HTTPException(status_code=404, detail="文件不存在")
        
        # 删除文件
        filepath = VIDEO_DIR / filename
        if filepath.exists():
            filepath.unlink()
        
        # 从数据库删除（级联删除关联的截图记录）
        await db.delete(video)
        await db.commit()
        
        return {"success": True, "message": "删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/rename-frame")
async def rename_frame(data: dict, db: AsyncSession = Depends(get_db)):
    """重命名截图文件"""
    old_name = data.get("old_name")
    new_name = data.get("new_name")
    
    if not old_name or not new_name:
        raise HTTPException(status_code=400, detail="缺少文件名参数")
    
    try:
        # 查找截图
        result = await db.execute(
            select(Frame).where(Frame.filename == old_name)
        )
        frame = result.scalar_one_or_none()
        
        if not frame:
            raise HTTPException(status_code=404, detail="源文件不存在")
        
        # 检查新文件名是否已存在
        result = await db.execute(
            select(Frame).where(Frame.filename == new_name)
        )
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="目标文件名已存在")
        
        # 重命名文件
        old_path = FRAME_DIR / old_name
        new_path = FRAME_DIR / new_name
        
        if not old_path.exists():
            raise HTTPException(status_code=404, detail="文件不存在")
        
        old_path.rename(new_path)
        
        # 更新数据库
        frame.filename = new_name
        frame.path = f"/uploads/frames/{new_name}"
        await db.commit()
        
        return {"success": True, "message": "重命名成功"}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/delete-frame")
async def delete_frame(data: dict, db: AsyncSession = Depends(get_db)):
    """删除截图文件"""
    filename = data.get("filename")
    
    if not filename:
        raise HTTPException(status_code=400, detail="缺少文件名参数")
    
    try:
        # 查找截图
        result = await db.execute(
            select(Frame).where(Frame.filename == filename)
        )
        frame = result.scalar_one_or_none()
        
        if not frame:
            raise HTTPException(status_code=404, detail="文件不存在")
        
        # 删除文件
        filepath = FRAME_DIR / filename
        if filepath.exists():
            filepath.unlink()
        
        # 从数据库删除
        await db.delete(frame)
        await db.commit()
        
        return {"success": True, "message": "删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 类名管理 API ====================

@app.get("/api/classes")
async def list_classes(db: AsyncSession = Depends(get_db)):
    """获取所有类名"""
    try:
        result = await db.execute(
            select(Class).order_by(Class.created_at)
        )
        classes = result.scalars().all()
        
        return {
            "classes": [
                {
                    "id": cls.id,
                    "name": cls.name,
                    "color": cls.color,
                    "created_at": cls.created_at.timestamp()
                }
                for cls in classes
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/classes")
async def create_class(data: dict, db: AsyncSession = Depends(get_db)):
    """创建新类名，可选择添加到组"""
    from database import ClassGroupItem
    
    name = data.get("name")
    color = data.get("color", "#00ff00")
    group_id = data.get("group_id")  # 可选：创建时直接添加到组
    
    if not name:
        raise HTTPException(status_code=400, detail="类名不能为空")
    
    try:
        # 创建类名（允许重名，因为不同组可以有同名类）
        db_class = Class(
            name=name,
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
            "success": True,
            "class": {
                "id": db_class.id,
                "name": db_class.name,
                "color": db_class.color,
                "created_at": db_class.created_at.timestamp()
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/classes/{class_id}")
async def delete_class(class_id: int, db: AsyncSession = Depends(get_db)):
    """删除类名"""
    try:
        result = await db.execute(
            select(Class).where(Class.id == class_id)
        )
        cls = result.scalar_one_or_none()
        
        if not cls:
            raise HTTPException(status_code=404, detail="类名不存在")
        
        await db.delete(cls)
        await db.commit()
        
        return {"success": True, "message": "删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/classes/{class_id}")
async def update_class(class_id: int, data: dict, db: AsyncSession = Depends(get_db)):
    """更新类名"""
    try:
        result = await db.execute(
            select(Class).where(Class.id == class_id)
        )
        cls = result.scalar_one_or_none()
        
        if not cls:
            raise HTTPException(status_code=404, detail="类名不存在")
        
        if "name" in data:
            cls.name = data["name"]
        
        if "color" in data:
            cls.color = data["color"]
        
        await db.commit()
        await db.refresh(cls)
        
        return {
            "success": True,
            "class": {
                "id": cls.id,
                "name": cls.name,
                "color": cls.color,
                "created_at": cls.created_at.timestamp()
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 类名组管理 API ====================

@app.get("/api/class-groups")
async def list_class_groups(db: AsyncSession = Depends(get_db)):
    """获取所有类名组"""
    try:
        from database import ClassGroup, ClassGroupItem
        
        result = await db.execute(
            select(ClassGroup).order_by(ClassGroup.created_at)
        )
        groups = result.scalars().all()
        
        return {
            "groups": [
                {
                    "id": group.id,
                    "name": group.name,
                    "description": group.description,
                    "created_at": group.created_at.timestamp()
                }
                for group in groups
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/class-groups")
async def create_class_group(data: dict, db: AsyncSession = Depends(get_db)):
    """创建新类名组"""
    from database import ClassGroup
    
    name = data.get("name")
    description = data.get("description", "")
    
    if not name:
        raise HTTPException(status_code=400, detail="组名不能为空")
    
    try:
        # 检查组名是否已存在
        result = await db.execute(
            select(ClassGroup).where(ClassGroup.name == name)
        )
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="组名已存在")
        
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
            "success": True,
            "group": {
                "id": db_group.id,
                "name": db_group.name,
                "description": db_group.description,
                "created_at": db_group.created_at.timestamp()
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/class-groups/{group_id}")
async def update_class_group(group_id: int, data: dict, db: AsyncSession = Depends(get_db)):
    """更新类名组"""
    from database import ClassGroup
    
    try:
        result = await db.execute(
            select(ClassGroup).where(ClassGroup.id == group_id)
        )
        group = result.scalar_one_or_none()
        
        if not group:
            raise HTTPException(status_code=404, detail="类名组不存在")
        
        if "name" in data:
            # 检查新名称是否与其他组冲突
            result = await db.execute(
                select(ClassGroup).where(
                    ClassGroup.name == data["name"],
                    ClassGroup.id != group_id
                )
            )
            if result.scalar_one_or_none():
                raise HTTPException(status_code=400, detail="组名已存在")
            group.name = data["name"]
        
        if "description" in data:
            group.description = data["description"]
        
        await db.commit()
        await db.refresh(group)
        
        return {
            "success": True,
            "group": {
                "id": group.id,
                "name": group.name,
                "description": group.description,
                "created_at": group.created_at.timestamp()
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/class-groups/{group_id}")
async def delete_class_group(group_id: int, db: AsyncSession = Depends(get_db)):
    """删除类名组"""
    try:
        from database import ClassGroup
        
        result = await db.execute(
            select(ClassGroup).where(ClassGroup.id == group_id)
        )
        group = result.scalar_one_or_none()
        
        if not group:
            raise HTTPException(status_code=404, detail="类名组不存在")
        
        await db.delete(group)
        await db.commit()
        
        return {"success": True, "message": "删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/class-groups/{group_id}/classes")
async def get_group_classes(group_id: int, db: AsyncSession = Depends(get_db)):
    """获取类名组中的所有类名"""
    try:
        from database import ClassGroup, ClassGroupItem
        
        # 查找类名组
        result = await db.execute(
            select(ClassGroup).where(ClassGroup.id == group_id)
        )
        group = result.scalar_one_or_none()
        
        if not group:
            raise HTTPException(status_code=404, detail="类名组不存在")
        
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
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/class-groups/{group_id}/classes")
async def add_class_to_group(group_id: int, data: dict, db: AsyncSession = Depends(get_db)):
    """添加类名到组"""
    from database import ClassGroup, ClassGroupItem
    
    class_id = data.get("class_id")
    
    if not class_id:
        raise HTTPException(status_code=400, detail="缺少class_id参数")
    
    try:
        # 检查组是否存在
        result = await db.execute(
            select(ClassGroup).where(ClassGroup.id == group_id)
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="类名组不存在")
        
        # 检查类名是否存在
        result = await db.execute(
            select(Class).where(Class.id == class_id)
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="类名不存在")
        
        # 检查是否已存在
        result = await db.execute(
            select(ClassGroupItem).where(
                ClassGroupItem.group_id == group_id,
                ClassGroupItem.class_id == class_id
            )
        )
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="该类名已在组内")
        
        # 添加到组
        db_item = ClassGroupItem(
            group_id=group_id,
            class_id=class_id,
            order=0,
            created_at=datetime.now()
        )
        db.add(db_item)
        await db.commit()
        
        return {"success": True, "message": "添加成功"}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/class-groups/{group_id}/classes/{class_id}")
async def remove_class_from_group(group_id: int, class_id: int, db: AsyncSession = Depends(get_db)):
    """从组中移除类名"""
    try:
        from database import ClassGroupItem
        
        result = await db.execute(
            select(ClassGroupItem).where(
                ClassGroupItem.group_id == group_id,
                ClassGroupItem.class_id == class_id
            )
        )
        item = result.scalar_one_or_none()
        
        if not item:
            raise HTTPException(status_code=404, detail="该类名不在组内")
        
        await db.delete(item)
        await db.commit()
        
        return {"success": True, "message": "移除成功"}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 视频-类名关联 API ====================

@app.get("/api/videos/{video_id}/classes")
async def get_video_classes(video_id: int, db: AsyncSession = Depends(get_db)):
    """获取视频关联的类名（向后兼容接口）"""
    try:
        # 查找视频
        result = await db.execute(
            select(Video).where(Video.id == video_id)
        )
        video = result.scalar_one_or_none()
        
        if not video:
            raise HTTPException(status_code=404, detail="视频不存在")
        
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
        
        return {
            "video_id": video_id,
            "classes": [
                {
                    "id": cls.id,
                    "name": cls.name,
                    "color": cls.color
                }
                for cls in classes
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/videos/{video_id}/classes")
async def bind_classes_to_video(video_id: int, data: dict, db: AsyncSession = Depends(get_db)):
    """绑定类名到视频"""
    class_ids = data.get("class_ids", [])
    
    try:
        # 查找视频
        result = await db.execute(
            select(Video).where(Video.id == video_id)
        )
        video = result.scalar_one_or_none()
        
        if not video:
            raise HTTPException(status_code=404, detail="视频不存在")
        
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
        
        return {"success": True, "message": "绑定成功"}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ==================== YOLO导出 API ====================

@app.get("/api/export/yolo/{video_filename}")
async def export_yolo_dataset(
    video_filename: str,
    db: AsyncSession = Depends(get_db)
):
    """导出指定视频的YOLO格式数据集（支持多标注）"""
    try:
        import json
        from pathlib import Path
        
        # 查找视频
        result = await db.execute(
            select(Video).where(Video.filename == video_filename)
        )
        video = result.scalar_one_or_none()
        
        if not video:
            raise HTTPException(status_code=404, detail="视频不存在")
        
        # 查找该视频的所有截图（包括有annotations或class_id的）
        result = await db.execute(
            select(Frame).where(Frame.video_id == video.id)
        )
        frames = result.scalars().all()
        
        # 获取所有类名
        result = await db.execute(select(Class))
        classes = result.scalars().all()
        class_map = {cls.id: idx for idx, cls in enumerate(classes)}
        
        # 生成YOLO格式数据
        yolo_data = []
        for frame in frames:
            # 新格式：annotations包含数组
            if frame.annotations and isinstance(frame.annotations, list):
                for ann in frame.annotations:
                    if 'class_id' in ann and 'yolo_format' in ann:
                        class_idx = class_map.get(ann['class_id'])
                        if class_idx is not None:
                            yolo_data.append({
                                "image": frame.filename,
                                "image_path": frame.path,
                                "class_id": class_idx,
                                "bbox": [
                                    ann['yolo_format']['x_center'],
                                    ann['yolo_format']['y_center'],
                                    ann['yolo_format']['width'],
                                    ann['yolo_format']['height']
                                ]
                            })
            # 旧格式：单个标注（向后兼容）
            elif frame.class_id and frame.annotations and 'yolo_format' in frame.annotations:
                class_idx = class_map.get(frame.class_id)
                if class_idx is not None:
                    yolo_data.append({
                        "image": frame.filename,
                        "image_path": frame.path,
                        "class_id": class_idx,
                        "bbox": [
                            frame.annotations['yolo_format']['x_center'],
                            frame.annotations['yolo_format']['y_center'],
                            frame.annotations['yolo_format']['width'],
                            frame.annotations['yolo_format']['height']
                        ]
                    })
        
        if not yolo_data:
            raise HTTPException(status_code=404, detail="该视频没有标注数据")
        
        # 生成类名文件内容
        class_names = [cls.name for cls in classes]
        
        return {
            "video_filename": video_filename,
            "total_frames": len(set(d["image"] for d in yolo_data)),
            "total_annotations": len(yolo_data),
            "classes": class_names,
            "annotations": yolo_data
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/export/yolo")
async def export_all_yolo_dataset(db: AsyncSession = Depends(get_db)):
    """导出所有视频的YOLO格式数据集（支持多标注）"""
    try:
        import json
        
        # 查找所有截图
        result = await db.execute(select(Frame))
        frames = result.scalars().all()
        
        # 获取所有类名
        result = await db.execute(select(Class).order_by(Class.id))
        classes = result.scalars().all()
        class_map = {cls.id: idx for idx, cls in enumerate(classes)}
        
        # 生成YOLO格式数据
        yolo_data = []
        for frame in frames:
            # 新格式：annotations包含数组
            if frame.annotations and isinstance(frame.annotations, list):
                for ann in frame.annotations:
                    if 'class_id' in ann and 'yolo_format' in ann:
                        class_idx = class_map.get(ann['class_id'])
                        if class_idx is not None:
                            yolo_data.append({
                                "image": frame.filename,
                                "image_path": frame.path,
                                "class_id": class_idx,
                                "bbox": [
                                    ann['yolo_format']['x_center'],
                                    ann['yolo_format']['y_center'],
                                    ann['yolo_format']['width'],
                                    ann['yolo_format']['height']
                                ]
                            })
            # 旧格式：单个标注（向后兼容）
            elif frame.class_id and frame.annotations and isinstance(frame.annotations, dict) and 'yolo_format' in frame.annotations:
                class_idx = class_map.get(frame.class_id)
                if class_idx is not None:
                    yolo_data.append({
                        "image": frame.filename,
                        "image_path": frame.path,
                        "class_id": class_idx,
                        "bbox": [
                            frame.annotations['yolo_format']['x_center'],
                            frame.annotations['yolo_format']['y_center'],
                            frame.annotations['yolo_format']['width'],
                            frame.annotations['yolo_format']['height']
                        ]
                    })
        
        if not yolo_data:
            raise HTTPException(status_code=404, detail="没有标注数据")
        
        # 生成类名文件内容
        class_names = [cls.name for cls in classes]
        
        return {
            "total_frames": len(set(d["image"] for d in yolo_data)),
            "total_annotations": len(yolo_data),
            "classes": class_names,
            "annotations": yolo_data
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
