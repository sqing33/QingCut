"""
数据库迁移脚本 V2
添加类名组功能和多标注支持
"""
import asyncio
from sqlalchemy import text
from database import engine


async def migrate():
    """执行数据库迁移"""
    async with engine.begin() as conn:
        print("开始数据库迁移 V2...")
        
        # 1. 创建 class_groups 表
        print("检查 class_groups 表...")
        result = await conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name='class_groups'
        """))
        if not result.scalar():
            print("创建 class_groups 表...")
            await conn.execute(text("""
                CREATE TABLE class_groups (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR NOT NULL UNIQUE,
                    description VARCHAR,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """))
            print("✓ class_groups 表创建成功")
        else:
            print("✓ class_groups 表已存在")
        
        # 2. 创建 class_group_items 表
        print("检查 class_group_items 表...")
        result = await conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name='class_group_items'
        """))
        if not result.scalar():
            print("创建 class_group_items 表...")
            await conn.execute(text("""
                CREATE TABLE class_group_items (
                    id SERIAL PRIMARY KEY,
                    group_id INTEGER NOT NULL REFERENCES class_groups(id) ON DELETE CASCADE,
                    class_id INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
                    "order" INTEGER DEFAULT 0,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """))
            print("✓ class_group_items 表创建成功")
        else:
            print("✓ class_group_items 表已存在")
        
        # 3. 移除 classes 表的 name UNIQUE 约束（如果存在）
        print("检查 classes 表的 name 唯一约束...")
        result = await conn.execute(text("""
            SELECT constraint_name
            FROM information_schema.table_constraints
            WHERE table_name = 'classes' 
            AND constraint_type = 'UNIQUE'
            AND constraint_name LIKE '%name%'
        """))
        constraint = result.scalar()
        if constraint:
            print(f"删除 classes.name 唯一约束: {constraint}...")
            await conn.execute(text(f"""
                ALTER TABLE classes DROP CONSTRAINT {constraint}
            """))
            print("✓ 唯一约束删除成功")
        else:
            print("✓ classes.name 没有唯一约束")
        
        # 4. 移除 classes 表的 is_global 列（如果存在）
        print("检查 classes 表的 is_global 列...")
        result = await conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='classes' AND column_name='is_global'
        """))
        if result.scalar():
            print("删除 is_global 列...")
            await conn.execute(text("""
                ALTER TABLE classes DROP COLUMN is_global
            """))
            print("✓ is_global 列删除成功")
        else:
            print("✓ is_global 列不存在")
        
        # 5. 创建默认类名组（如果有现有类名）
        print("检查是否需要创建默认类名组...")
        result = await conn.execute(text("SELECT COUNT(*) FROM classes"))
        class_count = result.scalar()
        
        if class_count > 0:
            # 检查是否已有默认组
            result = await conn.execute(text("""
                SELECT id FROM class_groups WHERE name='默认组'
            """))
            default_group_id = result.scalar()
            
            if not default_group_id:
                print(f"发现 {class_count} 个现有类名，创建默认组...")
                result = await conn.execute(text("""
                    INSERT INTO class_groups (name, description, created_at)
                    VALUES ('默认组', '自动迁移创建的默认类名组', CURRENT_TIMESTAMP)
                    RETURNING id
                """))
                default_group_id = result.scalar()
                print(f"✓ 默认组创建成功 (ID: {default_group_id})")
                
                # 将所有现有类名加入默认组
                await conn.execute(text("""
                    INSERT INTO class_group_items (group_id, class_id, "order", created_at)
                    SELECT :group_id, id, 0, CURRENT_TIMESTAMP
                    FROM classes
                """), {"group_id": default_group_id})
                print(f"✓ 已将所有类名添加到默认组")
            else:
                print(f"✓ 默认组已存在 (ID: {default_group_id})")
        else:
            print("✓ 没有现有类名，跳过默认组创建")
        
        print("\n数据库迁移 V2 完成！")
        print("\n新功能说明：")
        print("- ✅ 类名组管理：可以创建多个类名组（如'动物组'、'车辆组'）")
        print("- ✅ 灵活分类：同一个类名可以属于多个组")
        print("- ✅ 向后兼容：现有类名已自动添加到'默认组'")


if __name__ == "__main__":
    asyncio.run(migrate())
