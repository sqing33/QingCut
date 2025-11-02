from ultralytics import YOLO  # type: ignore

model = YOLO('yolo11n.pt')

results = model.train(data='dataset\\data.yaml',
                      epochs=100,
                      imgsz=640,
                      batch=8)
