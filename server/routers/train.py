"""训练相关路由"""
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Optional, List
import uuid
import shutil
from pathlib import Path

from services.train_service import training_manager


router = APIRouter(prefix="/api/train", tags=["train"])


class CreateTrainingRequest(BaseModel):
    """创建训练任务请求"""
    dataset_identifier: str
    model_name: str
    epochs: int = 100
    batch_size: int = 16
    image_size: int = 640


class TrainingResponse(BaseModel):
    """训练任务响应"""
    task_id: str
    dataset_identifier: str
    model_name: str
    epochs: int
    batch_size: int
    image_size: int
    status: str
    progress: int
    current_epoch: int
    total_epochs: int
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None
    results_dir: Optional[str] = None


@router.get("/datasets")
async def get_available_datasets():
    """获取所有可用的数据集"""
    datasets = training_manager.get_available_datasets()
    return {"datasets": datasets}


@router.get("/models")
async def get_available_models():
    """获取所有可用的预训练模型"""
    models = training_manager.get_available_models()
    return {"models": models}


@router.post("/models/{model_name}/download")
async def download_model(model_name: str):
    """下载预训练模型"""
    try:
        result = await training_manager.download_model(model_name)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"下载模型失败: {str(e)}")


@router.get("/models/{model_name}/download-progress")
async def get_download_progress(model_name: str):
    """获取模型下载进度"""
    progress = training_manager.get_download_progress(model_name)
    if not progress:
        raise HTTPException(status_code=404, detail="下载任务不存在")
    return progress


@router.post("/models/upload")
async def upload_model(file: UploadFile = File(...)):
    """上传预训练模型"""
    try:
        # 验证文件扩展名
        if not file.filename or not file.filename.endswith('.pt'):
            raise HTTPException(status_code=400, detail="只能上传 .pt 格式的模型文件")
        
        # 保存文件到模型目录
        models_dir = Path("train/models")
        models_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = models_dir / file.filename
        
        # 如果文件已存在，抛出错误
        if file_path.exists():
            raise HTTPException(status_code=400, detail=f"模型 {file.filename} 已存在")
        
        # 保存文件
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        return {
            "status": "success",
            "message": "模型上传成功",
            "model_name": file.filename,
            "path": str(file_path)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传模型失败: {str(e)}")


@router.post("/create")
async def create_training_task(request: CreateTrainingRequest):
    """创建训练任务"""
    try:
        # 生成唯一的任务ID
        task_id = f"train_{uuid.uuid4().hex[:8]}"
        
        task_info = await training_manager.create_training_task(
            task_id=task_id,
            dataset_identifier=request.dataset_identifier,
            model_name=request.model_name,
            epochs=request.epochs,
            batch_size=request.batch_size,
            image_size=request.image_size
        )
        
        return task_info
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建训练任务失败: {str(e)}")


@router.post("/{task_id}/start")
async def start_training(task_id: str):
    """开始训练任务"""
    try:
        await training_manager.start_training(task_id)
        return {"message": "训练已开始", "task_id": task_id}
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启动训练失败: {str(e)}")


@router.get("/{task_id}/status")
async def get_training_status(task_id: str):
    """获取训练任务状态"""
    status = training_manager.get_training_status(task_id)
    if not status:
        raise HTTPException(status_code=404, detail="训练任务不存在")
    return status


@router.get("/tasks")
async def list_training_tasks():
    """列出所有训练任务（包括历史记录）"""
    tasks = await training_manager.list_all_training_records()
    return {"tasks": tasks}


@router.post("/{task_id}/cancel")
async def cancel_training(task_id: str):
    """取消训练任务"""
    success = await training_manager.cancel_training(task_id)
    if not success:
        raise HTTPException(status_code=404, detail="训练任务不存在或无法取消")
    return {"message": "训练已取消", "task_id": task_id}


@router.delete("/{task_id}")
async def delete_training_record(task_id: str):
    """删除训练记录"""
    try:
        success = await training_manager.delete_training_record(task_id)
        if not success:
            raise HTTPException(status_code=404, detail="训练任务不存在")
        return {"message": "训练记录已删除", "task_id": task_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除训练记录失败: {str(e)}")


@router.get("/{task_id}/results")
async def get_training_results(task_id: str):
    """获取训练结果详情"""
    results = await training_manager.get_training_results(task_id)
    if not results:
        raise HTTPException(status_code=404, detail="训练任务不存在或结果不可用")
    return results
