"""YOLO模型训练脚本"""
import sys
import argparse
import gc
from pathlib import Path
from ultralytics import YOLO

try:
    import torch
except ImportError:
    torch = None


def train_model(model_path: str, data_yaml: str, epochs: int, batch_size: int,
                image_size: int, project: str, name: str):
    """训练YOLO模型
    
    Args:
        model_path: 预训练模型路径
        data_yaml: 数据集配置文件路径
        epochs: 训练轮数
        batch_size: 批次大小
        image_size: 图片尺寸
        project: 项目目录
        name: 训练任务名称
    """
    model = None
    results = None
    
    try:
        print(f"加载模型: {model_path}")
        model = YOLO(model_path)

        print(f"开始训练...")
        print(f"数据集: {data_yaml}")
        print(f"训练轮数: {epochs}")
        print(f"批次大小: {batch_size}")
        print(f"图片尺寸: {image_size}")

        results = model.train(data=data_yaml,
                              epochs=epochs,
                              imgsz=image_size,
                              batch=batch_size,
                              project=project,
                              name=name,
                              exist_ok=True,
                              verbose=True)

        print('Training completed successfully')
        return 0

    except Exception as e:
        print(f"训练失败: {str(e)}", file=sys.stderr)
        return 1
    
    finally:
        # 释放内存资源
        print("开始释放训练资源...")
        
        # 删除训练结果对象
        if results is not None:
            del results
            print("已释放训练结果对象")
        
        # 删除模型对象
        if model is not None:
            del model
            print("已释放模型对象")
        
        # 强制垃圾回收
        gc.collect()
        print("已执行垃圾回收")
        
        # 清理GPU内存
        if torch is not None and torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
            print("已清理GPU内存")
        
        print("训练资源释放完成")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='YOLO模型训练')
    parser.add_argument('--model', required=True, help='预训练模型路径')
    parser.add_argument('--data', required=True, help='数据集配置文件路径')
    parser.add_argument('--epochs', type=int, required=True, help='训练轮数')
    parser.add_argument('--batch', type=int, required=True, help='批次大小')
    parser.add_argument('--imgsz', type=int, required=True, help='图片尺寸')
    parser.add_argument('--project', required=True, help='项目目录')
    parser.add_argument('--name', required=True, help='训练任务名称')

    args = parser.parse_args()

    exit_code = train_model(model_path=args.model,
                            data_yaml=args.data,
                            epochs=args.epochs,
                            batch_size=args.batch,
                            image_size=args.imgsz,
                            project=args.project,
                            name=args.name)

    sys.exit(exit_code)
