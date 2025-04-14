import serial
import time
import cv2
import torch
import numpy as np
from models.common import DetectMultiBackend
from utils.general import non_max_suppression, scale_boxes
from utils.torch_utils import select_device
from utils.plots import Annotator

# Dahua Camera Configuration
DAHUA_IP = "192.168.188.37"  # Updated camera IP
USERNAME = "admin"  # Camera username
PASSWORD = "ganesh762"  # Camera password
http_url = f"http://{USERNAME}:{PASSWORD}@{DAHUA_IP}/cgi-bin/mjpg/video.cgi?channel=1&subtype=1"  # Use subtype=1 for smoother stream

# Select device ('cpu' for CPU, 'cuda' for GPU if available)
device = select_device('cpu')  

# Path to trained YOLOv5 ONNX model
weights_path = "/home/lain/yolov5/runs_final/YOLO5_1M/weights/best.onnx"

# Model loading
model = DetectMultiBackend(weights_path, device=device)

# Serial communication with Arduino
ser = serial.Serial('/dev/ttyACM0', 9600, timeout=1)  # Adjust port if necessary

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
    
# Logging setup
log_file = "detection_log.txt"

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

def log_detection(label, conf, xyxy):
    """ Log detection details to a file """
    with open(log_file, "a") as f:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"{timestamp}, {label}, {conf:.2f}, {xyxy}\n")

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
CONFIDENCE_THRESHOLD = 0.50  # Lower confidence threshold to detect more objects

# Watchdog Timer for Stream Restart
last_frame_time = time.time()
MAX_TIMEOUT = 5  # Restart stream if no frames in 5 sec

while True:
    for _ in range(2):  # Skip every 2 frames to further reduce lag
        cap.grab()  # Grab frame but don't decode it
    
    ret, frame = cap.read()
    
    if not ret or frame is None or frame.size == 0 or (time.time() - last_frame_time > MAX_TIMEOUT):
        print("Frame error detected! Restarting stream...")
        cap.release()
        time.sleep(2)  # Small delay before reconnecting
        cap = cv2.VideoCapture(http_url)  # Reinitialize HTTP stream
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        cap.set(cv2.CAP_PROP_FPS, 10)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        last_frame_time = time.time()
        continue  # Skip this iteration
    
    last_frame_time = time.time()  # Update last successful frame time
    
    frame_enhanced = preprocess_frame(frame)
    frame_resized = cv2.resize(frame_enhanced, (640, 640))
    img = torch.from_numpy(frame_resized).to(device)
    img = img.permute(2, 0, 1).float() / 255.0  
    img = img.unsqueeze(0)  

    pred = model(img)
    pred = non_max_suppression(pred)

    annotator = Annotator(frame, line_width=2)
    detection_found = False
    
    for det in pred:
        print(f"Detections: {det}")  # Debugging: Print detection results
        if det is not None and len(det):
            det[:, :4] = scale_boxes(img.shape[2:], det[:, :4], frame.shape).round()
            for *xyxy, conf, cls in reversed(det):
                if conf >= CONFIDENCE_THRESHOLD:
                    label = f"{model.names[int(cls)]} {conf:.2f}"
                    annotator.box_label(xyxy, label)
                    detection_found = True
                    log_detection(label, conf, xyxy)
    
    if detection_found:
        print("⚡ Object detected! Activating LED and Buzzer ⚡")
        control_led(True)
        control_buzzer(True)
    else:
        print("❌ No detection. Turning off LED and Buzzer.")
        control_led(False)
        control_buzzer(False)
    
    cv2.imshow("Dahua HTTP Stream - Detections", annotator.result())
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
ser.close()
