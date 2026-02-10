
<img width="1193" height="235" alt="image" src="https://github.com/user-attachments/assets/8c7e69bb-9de1-438a-b563-8b0031fcd8bb" />

# About 

This repository contains all the source code for Project Nilbye´s Real Time Object Detection and Deterrence System and its prototype device. The system uses YOLO where Version 5 and Version 8 were compared extensively. The original Dataset is included with several previously use with the addition of the most important training results and detection tests. A demonstration pre-trained YOLOv8 Model is used on the folder DeepStream-Yolo-master. Other important documents can also be found. 

# Project-Nilbye Prototype

The Project Nilbye first-stage prototype is an experimental device developed by the Werk:Raum team in collaboration with Welthungerhilfe. The prototype uses open-source software and a DeepStream pipeline to deploy both trained and pre-trained YOLO models via RTSP with a PTZ camera, all executed with the versatile and compact NVIDIA Jetson Orin Nano. This pipeline enables real-time object detection, all controlled smoothly via a customizable API that supports a graphical user interface GUI
As for the hardware, many electronic components and devices were procured to set the require solar energy network for field testing and deployment. In addition, electronics were connected to provide proper input for the detected images in the form of ultrasound, activated by signals from the Jetson and communicated via the API via MQTT. The aforementioned energy network is meant to power the devices and components placed on the main case and the PTZ camera. 

<img width="496" height="552" alt="image" src="https://github.com/user-attachments/assets/82dc8c5c-83d3-4426-96ca-6aac1d51cc9e" />

<img width="1826" height="972" alt="Screenshot from 2026-01-28 10-34-39" src="https://github.com/user-attachments/assets/ce23a43d-6d5c-4b0d-b696-56a3ee246afd" />

<img width="1134" height="535" alt="Screenshot from 2025-11-04 10-22-34" src="https://github.com/user-attachments/assets/9df2e2e4-b595-4f8a-a0f0-6df93a86659a" />

<img width="1226" height="758" alt="Screenshot from 2025-09-09 16-19-10" src="https://github.com/user-attachments/assets/fbf4d133-cdf5-4221-92d2-288ae6b21d78" />

<img width="1458" height="623" alt="image" src="https://github.com/user-attachments/assets/3dafeaf1-5b22-4639-ace8-560f9902c0ea" />

Follow the instructions under the User Manual-Project Nilbye Prototype. The mnaual´s emphasis is on the 3 Phase for configuration:

*Developer Mode:
Network connectiviy, camera set up and model testing with API.
*Headless Mode
Headless control and autotstart enablement
*Integration with Energy Network
Integration of main backbone devices and peripheral components with solar energy grid

To learn more about the training process see Back End Development for Project´s Nilbye Prototype Device.





