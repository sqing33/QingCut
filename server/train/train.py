import os
from pathlib import Path
from ultralytics import YOLO as YOLOModel
from datetime import datetime
import threading
import queue
import re
import json

# 在训练开始前配置matplotlib字体
try:
    import sys
    from pathlib import Path as PathLib

    # 添加项目根目录到Python路径
    project_root = PathLib(__file__).parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    # 导入matplotlib配置
    import utils.matplotlib_config
except ImportError as e:
    print(f"Warning: Failed to import matplotlib config: {e}")


class TrainingCallback:
    """Custom callback to capture training logs"""

    def __init__(self):
        self.logs = []
        self.logs_queue = queue.Queue()
        self.metrics_history = []
        # --- 核心修改 1: 添加我们自己的批次计数器 ---
        self.batch_counter = 0

    def on_train_epoch_start(self, trainer):
        """Called at the start of each training epoch."""
        print(f"DEBUG: Starting Epoch {trainer.epoch + 1}, resetting batch counter.")
        # 重置批次计数器
        self.batch_counter = 0

    def on_train_epoch_end(self, trainer):
        """Called at the end of each training epoch"""
        print(
            f"DEBUG: on_train_epoch_end called for epoch {trainer.epoch + 1}.")
        try:
            if not hasattr(trainer,
                           'loss_items') or trainer.loss_items is None:
                print(
                    "Warning: trainer.loss_items not available in on_train_epoch_end."
                )
                return

            box_loss, cls_loss, dfl_loss = trainer.loss_items
            metrics = {
                "box_loss": box_loss.item(),
                "cls_loss": cls_loss.item(),
                "dfl_loss": dfl_loss.item()
            }

            log_msg = f"Epoch {trainer.epoch + 1}: "
            for key, value in metrics.items():
                log_msg += f"{key}: {value:.4f} "
            print(f"CALLBACK LOG: {log_msg}")

            self.logs.append(log_msg)
            self.logs_queue.put_nowait(log_msg)
            self.metrics_history.append({
                'epoch': trainer.epoch + 1,
                'metrics': metrics
            })
        except queue.Full:
            pass
        except Exception as e:
            print(f"ERROR in on_train_epoch_end callback: {e}")

    # --- 步骤 1: 用于调试的 on_train_batch_end 函数 ---
    def on_train_batch_end(self, trainer):
        """Called at the end of each training batch"""
        try:
            # 增加我们自己的计数器
            self.batch_counter += 1

            if not hasattr(trainer, 'loss_items') or trainer.loss_items is None:
                return

            box_loss, cls_loss, dfl_loss = trainer.loss_items
            
            # 使用 self.batch_counter 作为当前批次
            current_batch = self.batch_counter
            total_batches = len(trainer.train_loader)

            batch_progress_data = {
                'type': 'batch_progress', 
                'epoch': trainer.epoch + 1, 
                'total_epochs': trainer.epochs,
                'batch': current_batch, 
                'total_batches': total_batches,
                'box_loss': box_loss.item(), 
                'cls_loss': cls_loss.item(), 
                'dfl_loss': dfl_loss.item(),
            }
            self.logs_queue.put_nowait(json.dumps(batch_progress_data))

            log_msg = (
                f"Epoch {batch_progress_data['epoch']}/{batch_progress_data['total_epochs']} | "
                f"Batch {batch_progress_data['batch']}/{batch_progress_data['total_batches']} | "
                f"box_loss: {batch_progress_data['box_loss']:.4f}, "
                f"cls_loss: {batch_progress_data['cls_loss']:.4f}, "
                f"dfl_loss: {batch_progress_data['dfl_loss']:.4f}"
            )
            print(f"REAL-TIME LOG: {log_msg}")

        except queue.Full:
            pass
        except Exception as e:
            print(f"ERROR in on_train_batch_end callback: {e}")

    def on_val_end(self, trainer):
        """Called at the end of validation"""
        print("DEBUG: on_val_end is called.")
        try:
            if hasattr(trainer, 'metrics') and hasattr(trainer.metrics,
                                                       'results_dict'):
                metrics_dictionary = trainer.metrics.results_dict
                val_info = {'validation': True, 'metrics': metrics_dictionary}
                json_val_info = json.dumps(val_info)
                print(
                    f"CALLBACK LOG: Validation results found: {json_val_info}")
                self.logs_queue.put_nowait(json_val_info)
            else:
                print(
                    "Warning: trainer.metrics.results_dict not found in on_val_end."
                )
        except queue.Full:
            pass
        except Exception as e:
            print(f"ERROR in on_val_end callback: {e}")

    def on_train_end(self, trainer):
        """Called at the very end of the training process."""
        print("\n" + "=" * 50)
        print("训练完成，最终详细信息如下:")
        print("=" * 50)
        extract_training_params_and_results(trainer)


def extract_training_params_and_results(trainer):
    """
    从最终的 trainer 对象中提取训练参数和结果
    """
    print("训练参数和结果:")
    print("=" * 50)

    # trainer 对象包含了 .args 属性，里面是所有配置
    args = trainer.args

    # 训练参数
    print("训练参数:")
    print(f"  Epochs: {args.epochs}")
    print(f"  Batch size: {args.batch}")
    print(f"  Image size: {args.imgsz}")
    print(f"  Learning rate: {args.lr0}")
    print(f"  Device: {trainer.device}")
    print()

    # 模型信息
    print("模型信息:")
    print(f"  Model: {args.model}")
    print(f"  Task: {args.task}")
    print()

    # 数据集信息
    print("数据集信息:")
    print(f"  Data: {args.data}")
    print(f"  Project: {args.project}")
    print(f"  Name: {args.name}")
    print()

    # 训练结果 (从 trainer.metrics 获取)
    if hasattr(trainer, 'metrics') and hasattr(trainer.metrics,
                                               'results_dict'):
        print("最终训练指标 (来自验证集):")
        final_metrics = trainer.metrics.results_dict
        for key, value in final_metrics.items():
            print(f"  {key}: {value}")
        print()

    # 保存的文件信息
    if hasattr(trainer, 'best') and trainer.best:
        print("最佳模型路径:")
        print(f"  {trainer.best}")
        print()

    if hasattr(trainer, 'last') and trainer.last:
        print("最后模型路径:")
        print(f"  {trainer.last}")
        print()


def get_training_progress(trainer):
    """
    获取当前训练进度
    """
    if hasattr(trainer, 'epoch') and hasattr(trainer, 'max_epoch'):
        progress = (trainer.epoch + 1) / trainer.max_epoch * 100
        print(
            f"训练进度: {trainer.epoch + 1}/{trainer.max_epoch} ({progress:.1f}%)")

    # 当前损失值
    if hasattr(trainer, 'loss'):
        print(f"当前损失: {trainer.loss}")


def get_validation_results(trainer):
    """
    获取验证结果
    """
    if hasattr(trainer, 'validator') and trainer.validator:
        print("验证结果:")
        # 如果验证已完成，获取验证指标
        if hasattr(trainer.validator, 'metrics') and trainer.validator.metrics:
            metrics = trainer.validator.metrics
            print(f"  mAP50: {metrics.get('metrics/mAP50(B)', 'N/A')}")
            print(f"  mAP50-95: {metrics.get('metrics/mAP50-95(B)', 'N/A')}")
            print(f"  Precision: {metrics.get('metrics/precision(B)', 'N/A')}")
            print(f"  Recall: {metrics.get('metrics/recall(B)', 'N/A')}")


def list_models():
    """List available models in the models directory"""
    import sys
    from pathlib import Path

    # Handle the case when running from the server directory
    models_dir = Path("train/models")
    if models_dir.exists():
        return [
            f.name for f in models_dir.iterdir()
            if f.suffix.lower() in ['.pt', '.onnx', '.engine']
        ]

    # For when running from the parent directory
    models_dir = Path("server/train/models")
    if models_dir.exists():
        return [
            f.name for f in models_dir.iterdir()
            if f.suffix.lower() in ['.pt', '.onnx', '.engine']
        ]

    # Absolute path from the project root
    models_dir = Path(__file__).parent / "models"
    if models_dir.exists():
        return [
            f.name for f in models_dir.iterdir()
            if f.suffix.lower() in ['.pt', '.onnx', '.engine']
        ]

    return []


def list_datasets():
    """List available datasets in the dataset directory"""
    import sys
    from pathlib import Path

    # Handle the case when running from the server directory
    dataset_dir = Path("dataset")
    if dataset_dir.exists():
        return [f.name for f in dataset_dir.iterdir() if f.is_dir()]

    # For when running from the parent directory
    dataset_dir = Path("server/dataset")
    if dataset_dir.exists():
        return [f.name for f in dataset_dir.iterdir() if f.is_dir()]

    # Absolute path from the project root
    dataset_dir = Path(__file__).parent.parent / "dataset"
    if dataset_dir.exists():
        return [f.name for f in dataset_dir.iterdir() if f.is_dir()]

    return []


def train_model(model_path,
                dataset_path,
                epochs=100,
                imgsz=640,
                batch_size=16):
    """
    Train a model with the given parameters
    """
    # Ensure paths are absolute
    model_path = os.path.abspath(model_path)
    dataset_path = os.path.abspath(dataset_path)

    # Initialize the model
    model = YOLOModel(model_path)

    # Create callback instance to capture logs
    callback = TrainingCallback()

    # --- 核心修改 4: 注册新的回调函数 ---
    model.add_callback('on_train_epoch_start', callback.on_train_epoch_start) # <-- 必须添加这一行！
    model.add_callback('on_train_epoch_end', callback.on_train_epoch_end)
    model.add_callback('on_train_batch_end', callback.on_train_batch_end)
    model.add_callback('on_val_end', callback.on_val_end)  # <-- 注册新的回调
    model.add_callback('on_train_end', callback.on_train_end)  # <-- 注册新的回调

    # Define the project directory for saving training results
    project_dir = Path(__file__).parent / "runs"
    project_dir.mkdir(exist_ok=True)

    # Start training with the dataset
    # 我们不再需要接收 results 变量了，因为摘要打印已自动化
    model.train(
        data=dataset_path,
        epochs=epochs,
        imgsz=imgsz,
        batch=batch_size,
        verbose=True,
        project=str(project_dir),  # 指定训练结果保存路径
        name="train"  # 保存在train子目录下
    )

    # Additional logs after training
    final_log = f"Training completed."
    callback.logs.append(final_log)
    try:
        callback.logs_queue.put_nowait(final_log)
    except queue.Full:
        pass
    print(final_log)  # Also print for standard output

    return callback


def start_training_job(model_name,
                       dataset_name,
                       epochs=100,
                       imgsz=640,
                       batch_size=16):
    """
    Start a training job with the specified model and dataset
    """
    import os

    # Check if running from server directory first
    model_path = f"train/models/{model_name}"
    dataset_path = f"dataset/{dataset_name}/train.yaml"

    # If not found, try the full server path
    if not os.path.exists(model_path):
        model_path = f"server/train/models/{model_name}"
    if not os.path.exists(dataset_path):
        dataset_path = f"server/dataset/{dataset_name}/train.yaml"

    # If still not found, use absolute paths from the project root
    if not os.path.exists(model_path):
        model_path = str(Path(__file__).parent / "models" / model_name)
    if not os.path.exists(dataset_path):
        dataset_path = str(
            Path(__file__).parent.parent / "dataset" / dataset_name /
            "train.yaml")

    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model file not found: {model_path}")

    if not os.path.exists(dataset_path):
        raise FileNotFoundError(
            f"Dataset config file not found: {dataset_path}")

    # Start training in a separate thread to allow real-time log access
    callback = train_model(model_path, dataset_path, epochs, imgsz, batch_size)

    return callback


if __name__ == "__main__":
    # Example usage
    models = list_models()
    print("Available models:", models)

    datasets = list_datasets()
    print("Available datasets:", datasets)

    # Example training (uncomment to run)
    # callback = start_training_job("yolov8n.pt", "ye_ren", epochs=3)
    # print("Training logs:", callback.logs)
