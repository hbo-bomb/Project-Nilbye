import cv2
import torch
from ultralytics import YOLO
import numpy as np

def preprocess_frame(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    filtered = cv2.bilateralFilter(frame, 5, 50, 50) 
    lab = cv2.cvtColor(filtered, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(6, 6))  
    l = clahe.apply(l)
    lab = cv2.merge((l, a, b))
    enhanced = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

    sharpen_kernel = np.array([[0, -0.5, 0],
                               [-0.5, 3, -0.5],
                               [0, -0.5, 0]]) 

    sharpened = cv2.filter2D(enhanced, -1, sharpen_kernel)
    gamma = 1.1  
    inv_gamma = 1.0 / gamma
    table = np.array([(i / 255.0) ** inv_gamma * 255 for i in np.arange(0, 256)]).astype("uint8")
    corrected = cv2.LUT(sharpened, table)

    return corrected

model_path = "C:/yolov5/runs/train/YOLO8_1M/weights/best.pt" 
model = YOLO(model_path)

cap = cv2.VideoCapture(0) 

if not cap.isOpened():
    print("Error: Camera not detected.")
    exit()

while True:
    ret, frame = cap.read()
    if not ret:
        print("Error: Could not read frame.")
        break
    
    frame_enhanced = preprocess_frame(frame)

  
    frame_resized = cv2.resize(frame_enhanced, (800, 800))
    results = model(frame_resized)

  
    height, width, _ = frame.shape  
    scale_x = width / 800  
    scale_y = height / 800  

    for result in results:
        for box in result.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])  
            confidence = float(box.conf[0])  
            
            if confidence >= 0.80: 
                class_id = int(box.cls[0])  
                label = f"{model.names[class_id]} {confidence:.2f}"  

                
                x1 = int(x1 * scale_x)
                y1 = int(y1 * scale_y)
                x2 = int(x2 * scale_x)
                y2 = int(y2 * scale_y)

               
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    cv2.imshow("YOLOv8 Detection", frame)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
