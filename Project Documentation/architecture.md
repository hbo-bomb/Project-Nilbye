# Nilbye System Architecture

This document describes the system architecture of the Nilbye prototype device running on NVIDIA Jetson Orin Nano.

The system processes real-time RTSP video, performs YOLOv8-based object detection using NVIDIA DeepStream, publishes structured detection metadata via MQTT, and activates a signal actuator based on backend decision logic.

---

# High-Level Architecture

The diagram below shows the overall system structure.

```mermaid
flowchart TB

  classDef ext fill:#e3f2fd,stroke:#1e88e5,stroke-width:1px;
  classDef core fill:#ede7f6,stroke:#5e35b1,stroke-width:1px;
  classDef backend fill:#e8f5e9,stroke:#2e7d32,stroke-width:1px;
  classDef hw fill:#fff8e1,stroke:#f9a825,stroke-width:1px;

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

  flowchart TB

  SRC[RTSP Ingest]
  MUX[nvstreammux\n(batch + resize 1280)]
  INF[YOLOv8 Detection\n(Primary GIE)]
  OSD[OSD Overlay\n(Bounding Boxes)]
  SPLIT{Output Split}
  DISP[Local Display]
  RTSP[RTSP Output 8554]
  META[MQTT Events\n(ds/events)]

  SRC --> MUX --> INF --> OSD --> SPLIT
  SPLIT --> DISP
  SPLIT --> RTSP
  SPLIT --> META

  flowchart TB

  META[MQTT Events ds/events]
  BRK[MQTT Broker 1883]
  API[API Service\n(MQTT Subscriber)]
  CTRL[Decision Logic]
  LOG[(Logs)]

  META --> BRK --> API --> CTRL
  API --> LOG

  flowchart TB

  CTRL[Decision Logic]
  ACT[Signal Actuator]
  HW[Physical Output\n(Buzzer / LED / Relay)]

  CTRL --> ACT --> HW