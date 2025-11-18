"""训练管理路由"""
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from typing import Dict, List
import asyncio
import threading

# Import the train module functions directly
import sys
from pathlib import Path
import importlib.util

# Load the train module directly
train_module_path = Path(__file__).parent.parent / "train" / "train.py"
spec = importlib.util.spec_from_file_location("train_module", train_module_path)
if spec is None:
    raise ImportError("无法加载训练模块")
if spec.loader is None:
    raise ImportError("无法加载训练模块加载器")
    
train_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(train_module)

# Import the needed functions
list_models = train_module.list_models
list_datasets = train_module.list_datasets
start_training_job = train_module.start_training_job
TrainingCallback = train_module.TrainingCallback

router = APIRouter(prefix="/api", tags=["train"])

# Store active training jobs
training_jobs: Dict[str, TrainingCallback] = {}
job_lock = threading.Lock()


@router.get("/train/models")
async def get_available_models():
    """获取可用的模型列表"""
    try:
        models = list_models()
        return {"models": models}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/train/datasets")
async def get_available_datasets():
    """获取可用的数据集列表"""
    try:
        datasets = list_datasets()
        return {"datasets": datasets}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/train/start")
async def start_training(data: dict):
    """开始训练任务"""
    try:
        model_name = data.get("model_name")
        dataset_name = data.get("dataset_name")
        epochs = data.get("epochs", 100)
        imgsz = data.get("imgsz", 640)
        batch_size = data.get("batch_size", 16)
        
        if not model_name or not dataset_name:
            raise HTTPException(status_code=400, detail="缺少模型名称或数据集名称")
        
        # Start training job in a separate thread
        callback = start_training_job(model_name, dataset_name, epochs, imgsz, batch_size)
        
        # Generate a job ID and store the callback
        job_id = f"train_{len(training_jobs)}"
        with job_lock:
            training_jobs[job_id] = callback
        
        return {
            "job_id": job_id,
            "message": "训练已开始",
            "model": model_name,
            "dataset": dataset_name
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/train/logs/{job_id}")
async def get_training_logs(job_id: str):
    """获取训练日志"""
    try:
        with job_lock:
            if job_id not in training_jobs:
                raise HTTPException(status_code=404, detail="训练任务不存在")
            
            callback = training_jobs[job_id]
            logs = callback.logs if hasattr(callback, 'logs') else []
        
        return {"logs": logs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
