"""文件操作工具函数"""
from pathlib import Path
from datetime import datetime
import shutil


def generate_unique_filename(original_filename: str, directory: Path) -> str:
    """生成唯一的文件名
    
    Args:
        original_filename: 原始文件名
        directory: 目标目录
    
    Returns:
        唯一的文件名
    """
    filepath = directory / original_filename
    
    if not filepath.exists():
        return original_filename
    
    # 文件已存在，添加时间戳
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    name_parts = original_filename.rsplit('.', 1)
    
    if len(name_parts) == 2:
        return f"{name_parts[0]}_{timestamp}.{name_parts[1]}"
    else:
        return f"{original_filename}_{timestamp}"


def save_uploaded_file(upload_file, target_path: Path) -> None:
    """保存上传的文件
    
    Args:
        upload_file: FastAPI UploadFile 对象
        target_path: 目标路径
    """
    with target_path.open("wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)


def delete_file(filepath: Path) -> bool:
    """删除文件
    
    Args:
        filepath: 文件路径
    
    Returns:
        是否成功删除
    """
    if filepath.exists():
        filepath.unlink()
        return True
    return False


def rename_file(old_path: Path, new_path: Path) -> bool:
    """重命名文件
    
    Args:
        old_path: 旧文件路径
        new_path: 新文件路径
    
    Returns:
        是否成功重命名
    """
    if old_path.exists() and not new_path.exists():
        old_path.rename(new_path)
        return True
    return False
