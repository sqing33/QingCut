from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from datetime import datetime
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 从环境变量读取数据库配置参数
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
DB_NAME = os.getenv("DB_NAME", "video_cut")

# 构建数据库连接 URL（异步）
DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# 创建异步引擎
engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()


class Video(Base):
    """视频表"""
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, unique=True, index=True, nullable=False)
    path = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # 关系：一个视频有多个截图
    frames = relationship("Frame", back_populates="video", cascade="all, delete-orphan")


class Frame(Base):
    """截图表"""
    __tablename__ = "frames"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, unique=True, index=True, nullable=False)
    path = Column(String, nullable=False)
    video_id = Column(Integer, ForeignKey("videos.id"), nullable=True)  # 允许为空（旧数据兼容）
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=True)  # 关联的类名ID
    width = Column(Integer, default=640)
    height = Column(Integer, default=640)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    annotations = Column(JSON, default=dict)  # YOLO格式标注数据

    # 关系：一个截图属于一个视频
    video = relationship("Video", back_populates="frames")
    # 关系：一个截图关联一个类名
    class_obj = relationship("Class")


class ClassGroup(Base):
    """类名组表"""
    __tablename__ = "class_groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)  # 组名（如 "动物组", "车辆组"）
    description = Column(String, nullable=True)  # 组描述
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # 关系：一个组包含多个类名
    items = relationship("ClassGroupItem", back_populates="group", cascade="all, delete-orphan")


class Class(Base):
    """类名表"""
    __tablename__ = "classes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)  # 类名（如 "person", "car"） - 移除unique约束，因为不同组可以有同名类
    color = Column(String, default="#00ff00")  # 显示颜色
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # 关系：类名可以属于多个组
    group_items = relationship("ClassGroupItem", back_populates="class_obj", cascade="all, delete-orphan")


class ClassGroupItem(Base):
    """类名组-类名关联表"""
    __tablename__ = "class_group_items"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("class_groups.id", ondelete="CASCADE"), nullable=False)
    class_id = Column(Integer, ForeignKey("classes.id", ondelete="CASCADE"), nullable=False)
    order = Column(Integer, default=0)  # 在组内的排序
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # 关系
    group = relationship("ClassGroup", back_populates="items")
    class_obj = relationship("Class", back_populates="group_items")


class VideoClass(Base):
    """视频-类名关联表（保留用于向后兼容，新功能使用ClassGroup）"""
    __tablename__ = "video_classes"

    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(Integer, ForeignKey("videos.id", ondelete="CASCADE"), nullable=False)
    class_id = Column(Integer, ForeignKey("classes.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # 关系
    video = relationship("Video", backref="class_associations")
    class_obj = relationship("Class")


# 获取数据库会话
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


# 初始化数据库
async def init_db():
    """创建所有表"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
