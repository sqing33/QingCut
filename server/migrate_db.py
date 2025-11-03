"""
数据库迁移脚本
从旧schema（带labels列）迁移到新schema（带class_id列，去除labels列）
"""
import asyncio
from sqlalchemy import text
from database import engine, init_db


async def migrate():
    """执行数据库迁移"""
    async with engine.begin() as conn:
        print("开始数据库迁移...")
        
        # 检查frames表是否存在class_id列
        result = await conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='frames' AND column_name='class_id'
        """))
        has_class_id = result.scalar() is not None
        
        if not has_class_id:
            print("添加class_id列...")
            await conn.execute(text("""
                ALTER TABLE frames 
                ADD COLUMN class_id INTEGER REFERENCES classes(id)
            """))
            print("✓ class_id列添加成功")
        else:
            print("✓ class_id列已存在")
        
        # 检查frames表是否存在annotations列
        result = await conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='frames' AND column_name='annotations'
        """))
        has_annotations = result.scalar() is not None
        
        if not has_annotations:
            print("添加annotations列...")
            await conn.execute(text("""
                ALTER TABLE frames 
                ADD COLUMN annotations JSONB DEFAULT '{}'::jsonb
            """))
            print("✓ annotations列添加成功")
        else:
            print("✓ annotations列已存在")
        
        # 检查是否有labels列
        result = await conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='frames' AND column_name='labels'
        """))
        has_labels = result.scalar() is not None
        
        if has_labels:
            print("删除labels列...")
            await conn.execute(text("""
                ALTER TABLE frames 
                DROP COLUMN labels
            """))
            print("✓ labels列删除成功")
        else:
            print("✓ labels列不存在")
        
        print("数据库迁移完成！")


if __name__ == "__main__":
    asyncio.run(migrate())
