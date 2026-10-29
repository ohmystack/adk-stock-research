import json
from pathlib import Path
Path("metrics.json").write_text(json.dumps({"example":True,"risk_budget":100,"stop_distance":5,"shares":20}))
print("Created metrics.json; synthetic calculation only")
