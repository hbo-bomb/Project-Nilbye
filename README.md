
<img width="1193" height="235" alt="image" src="https://github.com/user-attachments/assets/8c7e69bb-9de1-438a-b563-8b0031fcd8bb" />

# About 

This repository contains all the source code for project Nilbye´s real time object detection and deterrence system and its prototype device. The system uses YOLO where Version 5 and Version 8 were compared extensively. The original Dataset is included with several previously use with the addition of the most important training results and detection tests. A demonstration pre-trained YOLOv8 Model is used on the folder DeepStream-Yolo-master. Other important documents can also be found. 

# Project-Nilbye Prototype

The Project Nilbye first-stage prototype is an experimental device developed by the Werk:Raum team in collaboration with Welthungerhilfe. The prototype uses open-source software and a DeepStream pipeline to deploy both trained and pre-trained YOLO models via RTSP with a PTZ camera, all executed with the versatile and compact NVIDIA Jetson Orin Nano. This pipeline enables real-time object detection, all controlled smoothly via a customizable API that supports a graphical user interface GUI
As for the hardware, many electronic components and devices were procured to set the require solar energy network for field testing and deployment. In addition, electronics were connected to provide proper input for the detected images in the form of ultrasound, activated by signals from the Jetson and communicated via the API via MQTT. The aforementioned energy network is meant to power the devices and components placed on the main case and the PTZ camera. 

### Application Main Code
- [DeepStream applications](./DeepStream%20application/)

### Project Documentation
- [User Manual and other documents](./Project%20Documentation/)

### Dataset
- [Dataset](./Datasets/)

### Test Documentation
- [Test videos and photos](./Test%20documentation/)

### Open CV code
- [Legacy Code](./Legacy%20Code/)

<p align="center">
  <img width="496" height="552" alt="image" src="https://github.com/user-attachments/assets/82dc8c5c-83d3-4426-96ca-6aac1d51cc9e" />
</p>

<p align="center">
  <img width="1826" height="972" alt="Screenshot from 2026-01-28 10-34-39" src="https://github.com/user-attachments/assets/ce23a43d-6d5c-4b0d-b696-56a3ee246afd" />
</p>

<p align="center">
  <img width="1134" height="535" alt="Screenshot from 2025-11-04 10-22-34" src="https://github.com/user-attachments/assets/9df2e2e4-b595-4f8a-a0f0-6df93a86659a" />
</p>

<p align="center">
  <img width="1226" height="758" alt="Screenshot from 2025-09-09 16-19-10" src="https://github.com/user-attachments/assets/fbf4d133-cdf5-4221-92d2-288ae6b21d78" />
</p>

<p align="center">
  <img width="1458" height="623" alt="image" src="https://github.com/user-attachments/assets/3dafeaf1-5b22-4639-ace8-560f9902c0ea" />
</p>


<p align="center">
  <img width="1425" height="646" alt="image" src="https://github.com/user-attachments/assets/e16ccf24-2681-4f8b-be7d-bc7e9ee81723" />
</p>

<p align="center">
  <img width="483" height="643" alt="image" src="https://github.com/user-attachments/assets/3c2bc182-dfdf-415f-81b1-a1548b4c1255" />
</p>

<p align="center">
  <img width="1075" height="634" alt="image" src="https://github.com/user-attachments/assets/afecef0a-d23e-4dcd-8849-3d4d474cfda0" />
</p>


  ![IMG_4315](https://github.com/user-attachments/assets/dffb2090-102d-44a5-9bd1-92365b957e16)



  ![IMG_4314](https://github.com/user-attachments/assets/27c57e95-f888-48e5-844c-e460bab925c8)



  ![IMG_4313](https://github.com/user-attachments/assets/193206ec-eed7-4f23-af02-2aab033f236f)



  ![IMG_4312](https://github.com/user-attachments/assets/47e4812f-b9ec-4269-be00-3c38e234ad84)



  ![IMG_4311](https://github.com/user-attachments/assets/9bced7b1-af5e-4088-bcd2-7220a524f135)



  ![IMG_4310](https://github.com/user-attachments/assets/63501aa3-97ca-4a9f-b5aa-acfe296b319b)



  ![IMG_4309](https://github.com/user-attachments/assets/3c9d6357-2669-4cca-9e5d-5cc17e24fba5)



  ![IMG_4308](https://github.com/user-attachments/assets/e7a1917e-5827-42dd-954a-e9a00695133f)
</p>


  ![IMG_4307](https://github.com/user-attachments/assets/8633fa50-e81a-423c-8784-9e50c98ffe8d)
</p>


  ![IMG_4306](https://github.com/user-attachments/assets/0b90c685-f27b-42a0-9bff-64a428e5bfb3)



  ![IMG_4305](https://github.com/user-attachments/assets/bb1a93f7-79f5-41fe-85bc-bd499357b735)


  ![IMG_4304](https://github.com/user-attachments/assets/1a929953-bacd-4dc7-ae61-f393e0cc0eed)



  ![IMG_4303](https://github.com/user-attachments/assets/7f053a07-537a-4e48-bd4a-b27db23baf8b)



  ![IMG_4302](https://github.com/user-attachments/assets/a8c46538-9c8c-419b-b5f5-8b24a691c7ac)



  ![IMG_4301](https://github.com/user-attachments/assets/39494fb7-a4fa-47eb-aa9c-743a8c06960b)



  ![IMG_4300](https://github.com/user-attachments/assets/d6c29fba-53c0-4ddd-87d0-859402bf5d6b)



  ![Demo_1](https://github.com/user-attachments/assets/d05e909c-569f-46d3-b860-83ece19768f1)


  https://github.com/user-attachments/assets/5671d38b-ff99-40e3-aee1-07827341f0e2



  https://github.com/user-attachments/assets/2d7acaa1-1d51-4a65-bccd-d81acc694c2c


Follow the instructions under the User Manual-Project Nilbye Prototype. The mnaual´s emphasis is on the 3 Phase for configuration:

*Developer Mode:
Network connectiviy, camera set up and model testing with API.

*Headless Mode
Headless control and autotstart enablement.

*Integration with Energy Network
Integration of main backbone devices and peripheral components with solar energy grid

To learn more about the training process see Back End Development for Project´s Nilbye Prototype Device.

### Open-Source Frameworks and Dependencies

### NVIDIA DeepStream SDK
Used for real-time inference acceleration and video pipeline deployment on NVIDIA Jetson hardware.

### NVIDIA Corporation.
DeepStream SDK.
https://developer.nvidia.com/deepstream-sdk

### DeepStream-YOLO Integration
Community implementation enabling YOLO models to run within DeepStream pipelines.

### Marcos Lucianops.
DeepStream-Yolo.
https://github.com/marcoslucianops/DeepStream-Yolo
Ultralytics YOLOv8
Used for training, exporting, and evaluating YOLO-based object detection models.

### Ultralytics.
Ultralytics YOLOv8.
https://github.com/ultralytics/ultralytics
ONNX (Open Neural Network Exchange)
Used for exporting trained models into interoperable format for DeepStream deployment.

### ONNX Community.
Open Neural Network Exchange (ONNX).
https://github.com/onnx/onnx
FastAPI
Used to implement the REST API for system control and monitoring.

### Sebastián Ramírez.
FastAPI.
https://github.com/fastapi/fastapi
Uvicorn
ASGI server used to run the FastAPI application.

### Uvicorn.
https://github.com/encode/uvicorn
Eclipse Paho MQTT Client
Used for MQTT-based detection event communication.

### Eclipse Foundation.
Paho MQTT Python Client.
https://github.com/eclipse/paho.mqtt.python
Jetson.GPIO
Used for hardware-level GPIO control on NVIDIA Jetson platforms.

### Jetson.GPIO.
https://github.com/NVIDIA/jetson-gpio
Tailscale
Used for secure remote networking and headless device management.

### Tailscale Inc.
Tailscale.
https://github.com/tailscale/tailscale
HLS.js
Used for browser-based HTTP Live Streaming playback.

### Video Dev Community.
HLS.js.
https://github.com/video-dev/hls.js

### Disclaimer
This project integrates and adapts open-source components. All original rights remain with their respective authors. Project Nilbye focuses on system integration, deployment architecture, and applied embedded AI development.


For any question please write to horacioserrano1989@gmail.com





