# Nilbye System Architecture

This document describes the system architecture of the Nilbye prototype device running on NVIDIA Jetson Orin Nano.

The system processes real-time RTSP video, performs YOLOv8-based object detection using DeepStream, publishes structured detection metadata via MQTT, and activates a signal actuator based on backend decision logic.

---

## Architecture Diagram

The diagram below shows the high-level system structure.

```mermaid
flowchart TB

  classDef ext fill:#e3f2fd,stroke:#1e88e5,stroke-width:1px;
  classDef gpu fill:#ede7f6,stroke:#5e35b1,stroke-width:1px;
  classDef svc fill:#e8f5e9,stroke:#2e7d32,stroke-width:1px;
  classDef hw fill:#fff8e1,stroke:#f9a825,stroke-width:1px;
  classDef store fill:#f3e5f5,stroke:#8e24aa,stroke-width:1px;

  CAM[RTSP Camera]
  MON[Remote Monitor]

  subgraph Jetson Orin Nano

    subgraph GPU DeepStream Pipeline
      SRC[RTSP Ingest]
      MUX[nvstreammux]
      INF[YOLOv8 Detection]
      OSD[Overlay]
      SPLIT{Output Split}
      DISP[Local Display]
      RTSP[RTSP Output 8554]
      META[MQTT Publish ds events]
    end

    subgraph Backend Services
      BROKER[MQTT Broker 1883]
      API[API Service]
      CTRL[Decision Logic]
      LOG[(Logs)]
    end

    ACT[Signal Actuator]

  end

  CAM --> SRC --> MUX --> INF --> OSD --> SPLIT
  SPLIT --> DISP
  SPLIT --> RTSP --> MON
  SPLIT --> META --> BROKER --> API
  API --> CTRL --> ACT
  API --> LOG

  class CAM,MON ext
  class SRC,MUX,INF,OSD,SPLIT,DISP,RTSP,META gpu
  class BROKER,API,CTRL svc
  class ACT hw
  class LOG store