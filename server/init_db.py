"""
数据库初始化脚本
运行此脚本创建数据库表
"""
import asyncio
from database import init_db

async def main():
    print("开始初始化数据库...")
    await init_db()
    print("数据库初始化完成！")
    print("\n表结构:")
    print("- videos: 存储视频信息")
    print("- frames: 存储截图信息，通过 video_id 关联到 videos 表")

if __name__ == "__main__":
    asyncio.run(main())
