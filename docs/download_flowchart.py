import base64
import urllib.request

mermaid_code = """flowchart TD
    %% Base Setup
    User(["User Approximates Shelf Area"]) --> Camera["Optical Sensors Capture Video Array"]
    Camera --> Edge["Edge Node (Raspberry Pi / Jetson) Local Ingestion"]

    %% Vision Processing
    Edge --> YOLO["YOLOv8 Edge Vision Engine"]
    YOLO --> BBox["Bounding Box Regression (Hands & Products)"]

    %% Decision Fork
    BBox --> Intersect{"Hand-to-Product Intersection Detected?"}

    %% BRANCH A: INTERACTION PIPELINE
    Intersect -- "Yes" --> CalcIoU["Compute Spatial Overlap (IoU Metric)"]
    CalcIoU --> Classify{"Classify State Machine Event"}

    Classify -- "Take" --> TakeEvent["Target Displaced from Shelf"]
    Classify -- "Return" --> ReturnEvent["Target Re-enters Shelf Coordinate"]
    Classify -- "Touch" --> TouchEvent["Spatial Overlap; No Displacement"]

    TakeEvent --> PayloadAdd["WebSocket Payload: Append to Digital Ledger"]
    ReturnEvent --> PayloadRemove["WebSocket Payload: Remove from Digital Ledger"]
    TouchEvent --> LogWait["Log Event; Await Movement"]

    PayloadAdd --> UICart[/"Real-Time Virtual Shopping Cart UI"/]
    PayloadRemove --> UICart

    %% BRANCH B: PASSIVE PIPELINE
    Intersect -- "No" --> RestState["Execute Dynamic Resting State Algorithm"]
    RestState --> Deviation{"Deviation in Static Coordinates?"}

    Deviation -- "Yes" --> Remap["Autonomously Reconcile Inventory Map"]
    Deviation -- "No" --> Passive["Maintain Passive Spatial Monitoring"]

    %% Styling
    classDef startend fill:#d5e8d4,stroke:#82b366,stroke-width:2px;
    classDef process fill:#dae8fc,stroke:#6c8ebf,stroke-width:2px;
    classDef decision fill:#ffe6cc,stroke:#d79b00,stroke-width:2px;
    classDef data fill:#e1d5e7,stroke:#9673a6,stroke-width:2px;

    class User,UICart startend;
    class Camera,Edge,YOLO,BBox,CalcIoU,TakeEvent,ReturnEvent,TouchEvent,RestState,Remap,Passive process;
    class Intersect,Classify,Deviation decision;
    class PayloadAdd,PayloadRemove,LogWait data;
"""

encoded = base64.b64encode(mermaid_code.encode('utf-8')).decode('ascii')
url = f'https://mermaid.ink/img/{encoded}?type=jpeg'

print(f"Downloading from mermaid.ink...")
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req) as response, open('patent_flowchart.jpg', 'wb') as out_file:
    out_file.write(response.read())
print("Successfully saved patent_flowchart.jpg!")
