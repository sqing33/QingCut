"""FastAPI 应用入口"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import (
    UPLOAD_DIR, VIDEO_DIR, FRAME_DIR,
    CORS_ORIGINS, CORS_CREDENTIALS, CORS_METHODS, CORS_HEADERS
)
from database import init_db
from routers import videos, frames, classes, datasets, export

app = FastAPI()

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=CORS_CREDENTIALS,
    allow_methods=CORS_METHODS,
    allow_headers=CORS_HEADERS,
)

# 创建必要的目录
VIDEO_DIR.mkdir(parents=True, exist_ok=True)
FRAME_DIR.mkdir(parents=True, exist_ok=True)

# 挂载静态文件目录
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# 注册路由
app.include_router(videos.router)
app.include_router(frames.router)
app.include_router(classes.router)
app.include_router(datasets.router)
app.include_router(export.router)


@app.on_event("startup")
async def startup_event():
    """应用启动时初始化数据库"""
    await init_db()
    print("数据库初始化完成")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
