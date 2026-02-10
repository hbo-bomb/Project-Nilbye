# Project-Nilbye 

This repository contains all the source code for Project Nilbye´s Real Time Object Detection and Deterrence System and its prototype device. The system uses YOLO where Version 5 and Version 8 were compared extensively. The original Dataset is included with several previously use with the addition of the most important training results and detection tests. A demonstration pre-trained YOLOv8 Model is used on the folder DeepStream-Yolo-master. Other important documents can also be found. 

The Project Nilbye first-stage prototype is an experimental device developed by the Werk:Raum team in collaboration with Welthungerhilfe. The prototype uses open-source software and a DeepStream pipeline to deploy both trained and pre-trained YOLO models via RTSP with a PTZ camera, all executed with the versatile and compact NVIDIA Jetson Orin Nano. This pipeline enables real-time object detection, all controlled smoothly via a customizable API that supports a graphical user interface GUI
As for the hardware, many electronic components and devices were procured to set the require solar energy network for field testing and deployment. In addition, electronics were connected to provide proper input for the detected images in the form of ultrasound, activated by signals from the Jetson and communicated via the API via MQTT. The aforementioned energy network is meant to power the devices and components placed on the main case and the PTZ camera. 

<img width="496" height="552" alt="image" src="https://github.com/user-attachments/assets/82dc8c5c-83d3-4426-96ca-6aac1d51cc9e" />

Follow the instructions under the User Manual-Project Nilbye Prototype. The mnaual´s emphasis is on the 3 Phase for configuration:

*Developer Mode:
Network connectiviy, camera set up and model testing with API.
*Headless Mode
Headless control and autotstart enablement
*Integration with Energy Network
Integration of main backbone devices and peripheral components with solar energy grid

<img width="703" height="218" alt="image" src="https://github.com/user-attachments/assets/24997fc5-5bb4-4e86-b887-d8ac4fb213e6" />

<img width="914" height="247" alt="image" src="https://github.com/user-attachments/assets/44e70f91-dc75-4e0a-8c9d-c8f2b8664950" />


