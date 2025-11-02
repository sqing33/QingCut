from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import shutil
from datetime import datetime

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

@app.post("/api/upload-video")
async def upload_video(video: UploadFile = File(...)):
    """上传视频文件"""
    try:
        # 生成唯一文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{video.filename}"
        filepath = VIDEO_DIR / filename
        
        # 保存视频文件
        with filepath.open("wb") as buffer:
            shutil.copyfileobj(video.file, buffer)
        
        return {
            "success": True,
            "url": f"/uploads/videos/{filename}",
            "filename": filename
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/save-frame")
async def save_frame(image: UploadFile = File(...)):
    """保存截取的帧"""
    try:
        # 生成唯一文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"frame_{timestamp}.png"
        filepath = FRAME_DIR / filename
        
        # 保存图片文件
        with filepath.open("wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
        
        return {
            "success": True,
            "path": str(filepath),
            "filename": filename
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/frames")
async def list_frames():
    """列出所有截取的帧"""
    frames = []
    for filepath in FRAME_DIR.glob("*.png"):
        frames.append({
            "filename": filepath.name,
            "path": f"/uploads/frames/{filepath.name}",
            "created_at": filepath.stat().st_ctime
        })
    return {"frames": sorted(frames, key=lambda x: x["created_at"], reverse=True)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
