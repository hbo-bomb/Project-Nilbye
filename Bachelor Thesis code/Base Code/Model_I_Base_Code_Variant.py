import cv2
import torch
import numpy as np
from models.common import DetectMultiBackend
from utils.general import non_max_suppression, scale_boxes
from utils.torch_utils import select_device
from utils.plots import Annotator

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
device = select_device('cuda:0' if torch.cuda.is_available() else 'cpu')
weights_path = "C:/yolov5/runs/train/YOLO5_1M/weights/best.pt"
model = DetectMultiBackend(weights_path, device=device)
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
    img = torch.from_numpy(frame_resized).to(device)
    img = img.permute(2, 0, 1).float() / 255.0  
    img = img.unsqueeze(0)  
    pred = model(img)
    pred = non_max_suppression(pred, iou_thres=0.5)
    
    annotator = Annotator(frame_resized, line_width=2)
    for det in pred:
        if det is not None and len(det):
            det[:, :4] = scale_boxes(img.shape[2:], det[:, :4], frame_resized.shape).round() 
            for *xyxy, conf, cls in reversed(det):
                if conf >= 0.80:  
                    detected = True
                    label = f"{model.names[int(cls)]} {conf:.2f}"  
                    annotator.box_label(xyxy, label)

                    
    cv2.imshow("YOLOv5 Detection", annotator.result())
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
cap.release()
cv2.destroyAllWindows()

