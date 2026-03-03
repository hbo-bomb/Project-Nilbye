# Nilbye System Architecture

This document describes the system architecture of the Nilbye prototype device running on NVIDIA Jetson Orin Nano.

The system processes real-time RTSP video, performs YOLOv8-based object detection using NVIDIA DeepStream, publishes structured detection metadata via MQTT, and activates a signal actuator based on backend decision logic.

---

# High-Level Architecture

The diagram below shows the overall system structure.

```mermaid
flowchart TB

  %% ===== White / Black / Orange Theme =====
  classDef ext fill:#ffffff,stroke:#000000,stroke-width:1.5px,color:#000000;
  classDef core fill:#ffe5cc,stroke:#ff6600,stroke-width:2px,color:#000000;
  classDef backend fill:#f2f2f2,stroke:#000000,stroke-width:1.5px,color:#000000;
  classDef hw fill:#ff6600,stroke:#000000,stroke-width:2px,color:#ffffff;

  CAM[RTSP Camera]
  GPU[GPU DeepStream Pipeline]
  BE[Backend Services]
  ACT[Actuation Layer]
  MON[Remote Monitor]

  CAM --> GPU --> BE --> ACT
  GPU --> MON

  class CAM,MON ext
  class GPU core
  class BE backend
  class ACT hw
```

---

## GPU DeepStream Pipeline

```mermaid
flowchart TB

  classDef core fill:#ffe5cc,stroke:#ff6600,stroke-width:2px,color:#000000;

  SRC[RTSP Ingest]
  MUX[nvstreammux batch resize 1280]
  INF[YOLOv8 Detection Primary GIE]
  OSD[OSD Overlay Bounding Boxes]
  SPLIT{Output Split}
  DISP[Local Display]
  RTSP[RTSP Output 8554]
  META[MQTT Events ds events]

  SRC --> MUX --> INF --> OSD --> SPLIT
  SPLIT --> DISP
  SPLIT --> RTSP
  SPLIT --> META

  class SRC,MUX,INF,OSD,SPLIT,DISP,RTSP,META core
```

### Responsibilities

- Ingest RTSP video stream  
- Resize and batch frames for GPU inference  
- Run YOLOv8 object detection  
- Generate structured detection metadata  
- Render bounding boxes on output frames  
- Publish detection events to MQTT topic ds events  

---

## Backend Services

```mermaid
flowchart TB

  classDef backend fill:#f2f2f2,stroke:#000000,stroke-width:1.5px,color:#000000;

  META[MQTT Events ds events]
  BRK[MQTT Broker 1883]
  API[API Service MQTT Subscriber]
  CTRL[Decision Logic]
  LOG[Logs]

  META --> BRK --> API --> CTRL
  API --> LOG

  class META,BRK,API,CTRL,LOG backend
```

### Responsibilities

- Receive detection events from DeepStream  
- Parse structured payload data  
- Apply decision rules  
- Trigger actuation logic  
- Log results for monitoring and analysis  

---

## Actuation Layer

```mermaid
flowchart TB

  classDef hw fill:#ff6600,stroke:#000000,stroke-width:2px,color:#ffffff;

  CTRL[Decision Logic]
  ACT[Signal Actuator]
  HW[Physical Output Buzzer LED Relay]

  CTRL --> ACT --> HW

  class CTRL,ACT,HW hw
```

### Responsibilities

- Convert software decisions into physical signals  
- Activate deterrence mechanisms  
- Provide real-world system response  

---

## System Design Philosophy

The Nilbye architecture separates responsibilities into distinct layers:

- **Perception Layer** – Real-time GPU-based computer vision  
- **Communication Layer** – MQTT-based event distribution  
- **Decision Layer** – Backend rule evaluation  
- **Actuation Layer** – Physical system response  

This modular separation improves:

- Maintainability  
- Scalability  
- Debugging clarity  
- Deployment flexibility  

The entire system runs locally on the NVIDIA Jetson Orin Nano, enabling fully embedded, real-time operation.