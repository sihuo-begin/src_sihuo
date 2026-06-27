import os

BASE_DIR = os.path.dirname(__file__)

CONFIG = {
    "spec": {
        "USL": 10,
        "LSL": 5,
        "TARGET": 7
    },
    "paths": {
        "template": os.path.join(BASE_DIR, "assets/FA_Template.xlsx"),
        "output": os.path.join(BASE_DIR, "output"),
        "reports": os.path.join(BASE_DIR, "output/reports"),
        "images": os.path.join(BASE_DIR, "output/images"),
        "logs": os.path.join(BASE_DIR, "logs"),
    }
}