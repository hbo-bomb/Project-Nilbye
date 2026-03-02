import serial
import time
import cv2
import torch
from ultralytics import YOLO
import numpy as np

# Dahua Camera Configuration
DAHUA_IP = "192.168.188.37"  # Updated camera IP
USERNAME = "admin"  # Camera username
PASSWORD = "ganesh762"  # Camera password
http_url = f"http://{USERNAME}:{PASSWORD}@{DAHUA_IP}/cgi-bin/mjpg/video.cgi?channel=1&subtype=1"  # Use subtype=1 for smoother stream

# Serial communication with Arduino
ser = serial.Serial('/dev/ttyACM0', 9600, timeout=1)  # Adjust port if necessary

# Load YOLOv8 Model
model_path = "/home/lain/yolov5/runs_final/YOLO8_1M/weights/best.pt" 
model = YOLO(model_path)

# Camera Initialization
cap = cv2.VideoCapture(http_url)  # Use HTTP instead of RTSP
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Reduce buffer size for lower latency
cap.set(cv2.CAP_PROP_FPS, 10)  # Lower FPS to prevent lag
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)  # Reduce resolution for stability
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

if not cap.isOpened():
    print("Error: Cannot open HTTP stream.")
    exit()
else:
    print("HTTP Stream is working with subtype=1!")

# Image Processing Function
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

# LED and Buzzer Control
def control_led(state):
    if ser.is_open:
        command = b'1' if state else b'0'
        ser.write(command)
        print(f"🟢 LED {'ON' if state else 'OFF'} sent to Arduino ({command})")
    else:
        print("⚠️ Error: Serial port is not open!")

def control_buzzer(state):
    if ser.is_open:
        command = b'1' if state else b'0'
        ser.write(command)
        print(f"🔊 Buzzer {'ON' if state else 'OFF'} sent to Arduino ({command})")
    else:
        print("⚠️ Error: Serial port is not open!")

previous_detection_led = False
previous_detection_buzzer = False
CONFIDENCE_THRESHOLD = 0.80  # Lower confidence threshold to detect more objects

# Detection Loop
while True:
    for _ in range(3):  # Skip every 3 frames to reduce lag
        cap.grab()  # Grab frame but don't decode it
    
    ret, frame = cap.read()
    
    if not ret or frame is None or frame.size == 0:
        print("Frame error detected! Skipping...")
        continue
    
    last_frame_time = time.time()  # Track frame time to monitor lag
    frame_enhanced = preprocess_frame(frame)
    frame_resized = cv2.resize(frame_enhanced, (640, 640))
    
    results = model(frame_resized, verbose=False, device='cpu')  # Ensure it runs on CPU without excessive load
    
    detection_found = False
    
    for result in results:
        for box in result.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])  
            confidence = float(box.conf[0])  
            
            if confidence >= CONFIDENCE_THRESHOLD: 
                class_id = int(box.cls[0])  
                label = f"{model.names[class_id]} {confidence:.2f}"  
                
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                
                detection_found = True
    
    if detection_found:
        print("⚡ Object detected! Activating LED and Buzzer ⚡")
        control_led(True)
        control_buzzer(True)
    else:
        print("❌ No detection. Turning off LED and Buzzer.")
        control_led(False)
        control_buzzer(False)
    
    cv2.imshow("YOLOv8 Detection - Dahua", frame)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
ser.close()

