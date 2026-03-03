## Architecture Diagram

The diagram below shows the high-level system structure.  
Click on major components to jump to detailed explanations.

```mermaid
flowchart TB

  classDef net fill:#e1f5fe,stroke:#0288d1,stroke-width:1px;
  classDef gpu fill:#ede7f6,stroke:#5e35b1,stroke-width:1px;
  classDef svc fill:#e8f5e9,stroke:#2e7d32,stroke-width:1px;
  classDef hw fill:#fff8e1,stroke:#f9a825,stroke-width:1px;
  classDef store fill:#f3e5f5,stroke:#8e24aa,stroke-width:1px;

  CAM[RTSP Camera]
  MON[Remote Monitor Client]

  subgraph Jetson Orin Nano

    subgraph GPU DeepStream Pipeline
      SRC[RTSP Ingest]
      MUX[nvstreammux]
      P1[YOLOv8 Detection]
      OSD[Overlay]
      SPLIT{Output Split}
      DISP[Local Display]
      RTSP[RTSP Output 8554]
      META[MQTT Publish ds events]
    end

    subgraph Backend Services
      BRK[MQTT Broker 1883]
      API[API Service]
      CTRL[Decision Logic]
      LOG[(Logs)]
    end

    ACT[Signal Actuator]

  end

  CAM --> SRC --> MUX --> P1 --> OSD --> SPLIT
  SPLIT --> DISP
  SPLIT --> RTSP --> MON
  SPLIT --> META --> BRK --> API
  API --> CTRL --> ACT
  API --> LOG

  class CAM,MON net
  class SRC,MUX,P1,OSD,SPLIT,DISP,RTSP,META gpu
  class BRK,API,CTRL svc
  class ACT hw
  class LOG store

  click SRC "#gpu-deepstream-pipeline"
  click MUX "#gpu-deepstream-pipeline"
  click P1 "#gpu-deepstream-pipeline"
  click OSD "#gpu-deepstream-pipeline"

  click BRK "#backend-services"
  click API "#backend-services"
  click CTRL "#backend-services"

  click ACT "#actuation-layer"