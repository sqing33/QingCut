"""YOLO 模型训练业务逻辑"""
import asyncio
import os
import gc
import re
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import json
import subprocess
import httpx
from sqlalchemy import select, update, desc
from sqlalchemy.ext.asyncio import AsyncSession

from config import DATASET_DIR
from database import AsyncSessionLocal, TrainingRecord, TrainingEpochMetric

try:
    import torch
except ImportError:
    torch = None

# Ultralytics 官方模型下载地址
YOLO_MODEL_URLS = {
    "yolo11n.pt": "https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11n.pt",
    "yolo11s.pt": "https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11s.pt",
    "yolo11m.pt": "https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11m.pt",
    "yolo11l.pt": "https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11l.pt",
    "yolo11x.pt": "https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11x.pt",
    "yolov8n.pt": "https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov8n.pt",
    "yolov8s.pt": "https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov8s.pt",
    "yolov8m.pt": "https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov8m.pt",
    "yolov8l.pt": "https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov8l.pt",
    "yolov8x.pt": "https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov8x.pt",
}


class TrainingManager:
    """训练任务管理器"""
    def __init__(self):
        self.active_trainings: Dict[str, Dict[str, Any]] = {}  # Keep in-memory for fast status checks
        self.train_dir = Path("train")
        self.pretrained_models_dir = self.train_dir / "models"
        self.pretrained_models_dir.mkdir(parents=True, exist_ok=True)
        self.download_progress: Dict[str, Dict[str, Any]] = {}
        
    def get_available_datasets(self) -> List[Dict[str, Any]]:
        """获取所有可用的数据集"""
        datasets = []
        if not DATASET_DIR.exists():
            return datasets
        
        for dataset_dir in DATASET_DIR.iterdir():
            if dataset_dir.is_dir():
                yaml_file = dataset_dir / "train.yaml"
                info_file = dataset_dir / "dataset_info.txt"
                
                if yaml_file.exists():
                    # 读取数据集信息
                    name = dataset_dir.name
                    train_images = 0
                    val_images = 0
                    
                    if info_file.exists():
                        try:
                            with info_file.open('r', encoding='utf-8') as f:
                                content = f.read()
                                for line in content.split('\n'):
                                    if line.startswith('数据集名称:'):
                                        name = line.split(':', 1)[1].strip()
                                    elif line.startswith('训练集图片数量:'):
                                        train_images = int(line.split(':', 1)[1].strip())
                                    elif line.startswith('验证集图片数量:'):
                                        val_images = int(line.split(':', 1)[1].strip())
                        except:
                            pass
                    
                    datasets.append({
                        "identifier": dataset_dir.name,
                        "name": name,
                        "yaml_path": str(yaml_file.absolute()),
                        "train_images": train_images,
                        "val_images": val_images,
                        "total_images": train_images + val_images
                    })
        
        return datasets
    
    def get_available_models(self) -> List[Dict[str, Any]]:
        """获取所有可用的预训练模型（本地+可下载）"""
        models = []
        
        # 获取本地已下载的模型
        local_models = set()
        if self.pretrained_models_dir.exists():
            for model_file in self.pretrained_models_dir.glob("*.pt"):
                local_models.add(model_file.name)
        
        # 合并本地模型和可下载模型
        all_model_names = set(YOLO_MODEL_URLS.keys()) | local_models
        
        for model_name in sorted(all_model_names):
            is_local = model_name in local_models
            is_downloadable = model_name in YOLO_MODEL_URLS
            
            model_info = {
                "name": model_name,
                "is_local": is_local,
                "is_downloadable": is_downloadable,
                "size": self._get_model_size(model_name) if is_local else None
            }
            models.append(model_info)
        
        return models
    
    def _get_model_size(self, model_name: str) -> Optional[str]:
        """获取模型文件大小"""
        try:
            model_path = self.pretrained_models_dir / model_name
            if model_path.exists():
                size_bytes = model_path.stat().st_size
                # 转换为人类可读的格式
                if size_bytes < 1024 * 1024:
                    return f"{size_bytes / 1024:.1f} KB"
                else:
                    return f"{size_bytes / (1024 * 1024):.1f} MB"
        except:
            pass
        return None
    
    async def download_model(self, model_name: str) -> Dict[str, Any]:
        """下载预训练模型
        
        Args:
            model_name: 模型名称
            
        Returns:
            下载结果信息
        """
        if model_name not in YOLO_MODEL_URLS:
            raise ValueError(f"不支持下载的模型: {model_name}")
        
        model_path = self.pretrained_models_dir / model_name
        
        # 如果模型已存在，直接返回
        if model_path.exists():
            return {
                "status": "success",
                "message": "模型已存在",
                "model_name": model_name,
                "path": str(model_path)
            }
        
        # 初始化下载进度
        self.download_progress[model_name] = {
            "progress": 0,
            "downloaded": 0,
            "total": 0,
            "status": "downloading"
        }
        
        try:
            url = YOLO_MODEL_URLS[model_name]
            
            # 下载模型
            async with httpx.AsyncClient(timeout=300.0) as client:
                async with client.stream('GET', url, follow_redirects=True) as response:
                    response.raise_for_status()
                    
                    # 获取文件大小
                    total_size = int(response.headers.get('content-length', 0))
                    self.download_progress[model_name]["total"] = total_size
                    
                    # 写入文件
                    with model_path.open('wb') as f:
                        downloaded = 0
                        async for chunk in response.aiter_bytes(chunk_size=8192):
                            f.write(chunk)
                            downloaded += len(chunk)
                            # 更新进度
                            if total_size > 0:
                                progress = (downloaded / total_size) * 100
                                self.download_progress[model_name]["progress"] = progress
                                self.download_progress[model_name]["downloaded"] = downloaded
            
            # 下载完成
            self.download_progress[model_name]["status"] = "completed"
            self.download_progress[model_name]["progress"] = 100
            
            return {
                "status": "success",
                "message": "模型下载成功",
                "model_name": model_name,
                "path": str(model_path)
            }
            
        except Exception as e:
            # 删除可能的不完整文件
            if model_path.exists():
                model_path.unlink()
            self.download_progress[model_name]["status"] = "failed"
            self.download_progress[model_name]["error"] = str(e)
            raise ValueError(f"下载模型失败: {str(e)}")
    
    def get_download_progress(self, model_name: str) -> Optional[Dict[str, Any]]:
        """获取模型下载进度"""
        return self.download_progress.get(model_name)
    
    async def create_training_task(
        self,
        task_id: str,
        dataset_identifier: str,
        model_name: str,
        epochs: int = 100,
        batch_size: int = 16,
        image_size: int = 640
    ) -> Dict[str, Any]:
        """创建训练任务并持久化到数据库"""
        async with AsyncSessionLocal() as db:
            try:
                # 检查是否已存在相同 task_id 的记录
                result = await db.execute(
                    select(TrainingRecord).where(TrainingRecord.task_id == task_id)
                )
                existing = result.scalar_one_or_none()
                if existing:
                    raise ValueError(f"训练任务ID已存在: {task_id}")

                # 验证数据集和模型（与原逻辑相同）
                dataset_dir = DATASET_DIR / dataset_identifier
                yaml_file = dataset_dir / "train.yaml"
                if not yaml_file.exists():
                    raise ValueError(f"数据集配置文件不存在: {yaml_file}")

                model_path = self.pretrained_models_dir / model_name
                if not model_path.exists():
                    if model_name in YOLO_MODEL_URLS:
                        print(f"模型 {model_name} 不存在，开始自动下载...")
                        await self.download_model(model_name)
                        print(f"模型 {model_name} 下载完成")
                    else:
                        raise ValueError(f"预训练模型不存在: {model_path}")

                # 在数据库中创建记录
                new_record = TrainingRecord(
                    task_id=task_id,
                    dataset_identifier=dataset_identifier,
                    model_name=model_name,
                    epochs=epochs,
                    batch_size=batch_size,
                    image_size=image_size,
                    status="pending",
                    total_epochs=epochs,
                    current_epoch=0,
                    progress=0
                )
                db.add(new_record)
                await db.commit()
                await db.refresh(new_record)

                # 在内存中也保留一份副本，用于快速查询
                task_info = {
                    "id": new_record.id, # Add DB ID
                    "task_id": task_id,
                    "dataset_identifier": dataset_identifier,
                    "dataset_yaml": str(yaml_file.absolute()),
                    "model_name": model_name,
                    "model_path": str(model_path.absolute()),
                    "epochs": epochs,
                    "batch_size": batch_size,
                    "image_size": image_size,
                    "status": "pending",
                    "progress": 0,
                    "current_epoch": 0,
                    "total_epochs": epochs,
                    "created_at": new_record.created_at.isoformat(),
                    "started_at": None,
                    "completed_at": None,
                    "error": None,
                    "results_dir": None,
                    "logs": []
                }
                self.active_trainings[task_id] = task_info
                return task_info

            except Exception:
                await db.rollback()
                raise
    
    async def start_training(self, task_id: str) -> None:
        """开始训练任务"""
        if task_id not in self.active_trainings:
            raise ValueError(f"训练任务不存在: {task_id}")
        
        task_info = self.active_trainings[task_id]
        task_info["status"] = "running"
        task_info["started_at"] = datetime.now().isoformat()

        # Update database status to 'running'
        async with AsyncSessionLocal() as db:
            await db.execute(
                update(TrainingRecord)
                .where(TrainingRecord.task_id == task_id)
                .values(status="running", started_at=datetime.utcnow())
            )
            await db.commit()
        
        # 在后台启动训练进程
        asyncio.create_task(self._run_training(task_id))
    
    def _parse_training_log_line(self, line: str) -> Optional[Dict[str, Any]]:
        """
        解析YOLO训练日志行，提取epoch指标
        YOLO v11/v8 output examples:
        Epoch    GPU_mem   box_loss   cls_loss   dfl_loss  Instances       Size
        1/100    12.8G      0.06012      0.0485      0.0172          2        640
        ...
        Validating...
        ...
                   Class     Images  Instances      Box(P          R      mAP50  mAP50-95): 100% ...
                   all          2          2    0.00505          1      0.237     0.0919
        """
        metrics = {}
        stripped_line = line.strip()
        
        # 1. Parse epoch progress line (e.g., "1/100")
        # Look for lines like "1/100    12.8G      0.06012..."
        epoch_progress_match = re.search(r'^(\d+)\/(\d+)\s+\S+', stripped_line)
        if epoch_progress_match:
            try:
                metrics['epoch'] = int(epoch_progress_match.group(1))
                metrics['total_epochs'] = int(epoch_progress_match.group(2))

                # Extract losses from the same line
                parts = stripped_line.split()
                if len(parts) >= 6:
                    try:
                        metrics['box_loss'] = float(parts[2])
                        metrics['cls_loss'] = float(parts[3])
                        metrics['dfl_loss'] = float(parts[4])
                    except (ValueError, IndexError):
                        pass # Could be non-numeric
            except (ValueError, IndexError):
                pass

        # 2. Parse validation metrics line (the line with "all")
        # Example: "all          2          2    0.00505          1      0.237     0.0919"
        if 'all' in stripped_line and 'mAP50' in stripped_line:
            val_parts = stripped_line.split()
            # Find the numeric part after "all"
            if len(val_parts) >= 7:
                try:
                    # The format can be tricky, let's find numbers
                    nums = []
                    for part in val_parts:
                        try:
                            nums.append(float(part))
                        except ValueError:
                            pass
                    
                    if len(nums) >= 4:
                        # Assume: Images, Instances, Box(P), R, mAP50, mAP50-95
                        # Sometimes Box(P), R, mAP50 are directly after 'all'
                        metrics['precision'] = nums[2]
                        metrics['recall'] = nums[3]
                        if len(nums) >= 5:
                            metrics['map50'] = nums[4]
                        if len(nums) >= 6:
                            metrics['map75'] = nums[5]

                except Exception:
                    pass # Ignore parsing errors for this line

        return metrics if metrics else None

    async def _save_epoch_metrics(self, task_id: str, db_id: int, metrics: Dict[str, Any]):
        """将单轮次的训练指标保存到数据库"""
        async with AsyncSessionLocal() as db:
            try:
                # Avoid saving duplicates for the same epoch
                existing = await db.execute(
                    select(TrainingEpochMetric).where(
                        TrainingEpochMetric.record_id == db_id,
                        TrainingEpochMetric.epoch_number == metrics['epoch']
                    )
                )
                if existing.scalar_one_or_none():
                    return # Already saved

                epoch_metric = TrainingEpochMetric(
                    record_id=db_id,
                    epoch_number=metrics['epoch'],
                    precision=metrics.get('precision'),
                    recall=metrics.get('recall'),
                    map50=metrics.get('map50'),
                    map75=metrics.get('map75'),
                    box_loss=metrics.get('box_loss'),
                    cls_loss=metrics.get('cls_loss'),
                    metrics_json=metrics # Store all parsed metrics as JSON
                )
                db.add(epoch_metric)
                await db.commit()
            except Exception as e:
                print(f"Error saving epoch metrics for {task_id}: {e}")
                await db.rollback()


    async def _run_training(self, task_id: str) -> None:
        """执行训练任务（后台运行）"""
        task_info = self.active_trainings[task_id]
        db_id = task_info["id"]
        
        try:
            # 构建训练命令 - 使用独立的训练脚本
            train_script = Path("train/train.py")
            cmd = [
                "python", str(train_script),
                "--model", task_info['model_path'],
                "--data", task_info['dataset_yaml'],
                "--epochs", str(task_info['epochs']),
                "--batch", str(task_info['batch_size']),
                "--imgsz", str(task_info['image_size']),
                "--project", "train/runs/detect",
                "--name", task_id
            ]
            
            # 执行训练
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(Path.cwd())
            )
            
            # Variables to aggregate metrics for one epoch
            current_epoch_metrics = {}

            # 实时读取输出并更新进度
            async def read_output():
                nonlocal current_epoch_metrics
                if process.stdout:
                    async for line in process.stdout:
                        line_str = line.decode('utf-8', errors='ignore').strip()
                        
                        # 添加到日志
                        if line_str:
                            task_info["logs"].append(line_str)
                            if len(task_info["logs"]) > 100:
                                task_info["logs"] = task_info["logs"][-100:]

                        print(f"[{task_id}] {line_str}")  # 打印训练日志
                        
                        # 解析日志行
                        parsed_metrics = self._parse_training_log_line(line_str)
                        if parsed_metrics:
                            # If it's a new epoch, save the previous one's metrics
                            if 'epoch' in parsed_metrics and parsed_metrics['epoch'] > current_epoch_metrics.get('epoch', 0):
                                if current_epoch_metrics.get('epoch'):
                                    await self._save_epoch_metrics(task_id, db_id, current_epoch_metrics)
                                
                                # Start a new metrics collection
                                current_epoch_metrics = parsed_metrics
                                # Update in-memory progress
                                task_info["current_epoch"] = parsed_metrics['epoch']
                                task_info["progress"] = int((parsed_metrics['epoch'] / parsed_metrics['total_epochs']) * 100)
                                print(f"[{task_id}] Progress: {parsed_metrics['epoch']}/{parsed_metrics['total_epochs']} ({task_info['progress']}%)")
                            else:
                                # Merge metrics into the current epoch's collection
                                current_epoch_metrics.update(parsed_metrics)

            # 启动输出读取任务
            output_task = asyncio.create_task(read_output())
            
            # 等待训练完成
            await process.wait()
            await output_task
            
            # After the process finishes, save the last epoch's metrics
            if current_epoch_metrics.get('epoch'):
                 await self._save_epoch_metrics(task_id, db_id, current_epoch_metrics)
            
            # Determine final status and update in-memory and database
            final_status = "completed" if process.returncode == 0 else "failed"
            error_message = None
            
            if process.returncode != 0:
                stderr_output = ""
                if process.stderr:
                    stderr_output = await process.stderr.read()
                    stderr_output = stderr_output.decode('utf-8', errors='ignore')
                error_message = stderr_output or "训练失败，未知错误"

            task_info["status"] = final_status
            task_info["error"] = error_message
            if final_status == "completed":
                task_info["progress"] = 100
                task_info["current_epoch"] = task_info["total_epochs"]
                task_info["results_dir"] = str(self.train_dir / "runs" / "detect" / task_id)

            # Update final record in the database
            completed_time = datetime.utcnow()
            duration_seconds = None
            if task_info["started_at"]:
                # Use datetime object for accurate calculation
                started_time = datetime.fromisoformat(task_info["started_at"])
                duration_seconds = int((completed_time - started_time).total_seconds())

            async with AsyncSessionLocal() as db:
                try:
                    await db.execute(
                        update(TrainingRecord)
                        .where(TrainingRecord.task_id == task_id)
                        .values(
                            status=final_status,
                            progress=task_info["progress"],
                            current_epoch=task_info["current_epoch"],
                            completed_at=completed_time,
                            duration_seconds=duration_seconds,
                            error_message=error_message,
                            results_dir=task_info.get("results_dir")
                        )
                    )
                    await db.commit()
                except Exception as e:
                    print(f"Error updating final status for {task_id}: {e}")
                    await db.rollback()
            
        except Exception as e:
            task_info["status"] = "failed"
            task_info["error"] = str(e)
        
        finally:
            # 释放训练进程资源
            print(f"[{task_id}] 开始释放训练资源...")
            
            # 强制垃圾回收
            gc.collect()
            print(f"[{task_id}] 已执行垃圾回收")
            
            # 清理GPU内存
            if torch is not None and torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
                print(f"[{task_id}] 已清理GPU内存")
            
            print(f"[{task_id}] 训练资源释放完成")
            
            task_info["completed_at"] = datetime.now().isoformat()
    
    def get_training_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取训练任务状态"""
        return self.active_trainings.get(task_id)
    
    def list_training_tasks(self) -> List[Dict[str, Any]]:
        """列出所有当前活动的训练任务（从内存中快速获取）"""
        return list(self.active_trainings.values())

    async def list_all_training_records(self) -> List[Dict[str, Any]]:
        """从数据库中获取所有训练记录（包括历史记录）"""
        async with AsyncSessionLocal() as db:
            try:
                result = await db.execute(
                    select(TrainingRecord)
                    .order_by(desc(TrainingRecord.created_at))
                )
                records = result.scalars().all()

                all_tasks = []
                for record in records:
                    # Check if it's an active task in memory
                    active_task_info = self.active_trainings.get(record.task_id)
                    
                    task_data = {
                        "task_id": record.task_id,
                        "dataset_identifier": record.dataset_identifier,
                        "model_name": record.model_name,
                        "epochs": record.epochs,
                        "batch_size": record.batch_size,
                        "image_size": record.image_size,
                        "status": record.status,
                        "progress": record.progress,
                        "current_epoch": record.current_epoch,
                        "total_epochs": record.total_epochs,
                        "created_at": record.created_at.isoformat(),
                        "started_at": record.started_at.isoformat() if record.started_at else None,
                        "completed_at": record.completed_at.isoformat() if record.completed_at else None,
                        "duration_seconds": record.duration_seconds,
                        "error": record.error_message,
                        "results_dir": record.results_dir,
                    }

                    # If it's an active task, add logs and other runtime data
                    if active_task_info:
                        task_data["logs"] = active_task_info.get("logs", [])
                    else:
                        task_data["logs"] = []
                    
                    all_tasks.append(task_data)
                
                return all_tasks

            except Exception as e:
                print(f"Error fetching all training records: {e}")
                return []
    
    async def cancel_training(self, task_id: str) -> bool:
        """取消训练任务"""
        if task_id in self.active_trainings:
            task_info = self.active_trainings[task_id]
            if task_info["status"] == "running":
                # Update in-memory status
                task_info["status"] = "cancelled"
                task_info["completed_at"] = datetime.now().isoformat()

                # Update database status
                async with AsyncSessionLocal() as db:
                    try:
                        await db.execute(
                            update(TrainingRecord)
                            .where(TrainingRecord.task_id == task_id)
                            .values(
                                status="cancelled",
                                completed_at=datetime.utcnow()
                            )
                        )
                        await db.commit()
                    except Exception as e:
                        print(f"Error updating cancelled status for {task_id}: {e}")
                        await db.rollback()
                        return False
                
                return True
        return False
    
    async def delete_training_record(self, task_id: str) -> bool:
        """删除训练记录"""
        async with AsyncSessionLocal() as db:
            try:
                # 获取训练记录
                result = await db.execute(
                    select(TrainingRecord).where(TrainingRecord.task_id == task_id)
                )
                record = result.scalar_one_or_none()
                
                if not record:
                    return False
                
                # 只能删除已完成、失败或取消的任务
                if record.status not in ["completed", "failed", "cancelled"]:
                    raise ValueError("只能删除已完成、失败或已取消的训练任务")
                
                # 删除训练结果目录（如果存在）
                if record.results_dir:
                    results_path = Path(record.results_dir)
                    if results_path.exists():
                        import shutil
                        shutil.rmtree(results_path, ignore_errors=True)
                
                # 从数据库中删除记录（级联删除相关的epoch metrics）
                await db.delete(record)
                await db.commit()
                
                # 从内存中移除
                if task_id in self.active_trainings:
                    del self.active_trainings[task_id]
                
                return True
                
            except Exception as e:
                print(f"Error deleting training record {task_id}: {e}")
                await db.rollback()
                raise
    
    async def get_training_results(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取训练结果详情"""
        async with AsyncSessionLocal() as db:
            try:
                # 获取训练记录
                result = await db.execute(
                    select(TrainingRecord).where(TrainingRecord.task_id == task_id)
                )
                record = result.scalar_one_or_none()
                
                if not record:
                    return None
                
                # 获取所有epoch指标
                metrics_result = await db.execute(
                    select(TrainingEpochMetric)
                    .where(TrainingEpochMetric.record_id == record.id)
                    .order_by(TrainingEpochMetric.epoch_number)
                )
                epoch_metrics = metrics_result.scalars().all()
                
                # 组装结果数据
                results = {
                    "task_id": record.task_id,
                    "dataset_identifier": record.dataset_identifier,
                    "model_name": record.model_name,
                    "status": record.status,
                    "epochs": record.epochs,
                    "batch_size": record.batch_size,
                    "image_size": record.image_size,
                    "duration_seconds": record.duration_seconds,
                    "results_dir": record.results_dir,
                    "created_at": record.created_at.isoformat(),
                    "started_at": record.started_at.isoformat() if record.started_at else None,
                    "completed_at": record.completed_at.isoformat() if record.completed_at else None,
                    "epoch_metrics": []
                }
                
                # 添加每个epoch的详细指标
                for metric in epoch_metrics:
                    epoch_data = {
                        "epoch": metric.epoch_number,
                        "precision": metric.precision,
                        "recall": metric.recall,
                        "map50": metric.map50,
                        "map75": metric.map75,
                        "box_loss": metric.box_loss,
                        "cls_loss": metric.cls_loss,
                        "timestamp": metric.timestamp.isoformat()
                    }
                    results["epoch_metrics"].append(epoch_data)
                
                # 检查结果目录中的文件
                if record.results_dir:
                    results_path = Path(record.results_dir)
                    if results_path.exists():
                        # 获取weights目录中的模型文件
                        weights_dir = results_path / "weights"
                        if weights_dir.exists():
                            results["model_files"] = [
                                str(f.relative_to(results_path))
                                for f in weights_dir.glob("*.pt")
                            ]
                        
                        # 获取结果图片
                        results["result_images"] = [
                            str(f.relative_to(results_path))
                            for f in results_path.glob("*.png")
                        ]
                
                return results
                
            except Exception as e:
                print(f"Error getting training results for {task_id}: {e}")
                return None


# 全局训练管理器实例
training_manager = TrainingManager()
