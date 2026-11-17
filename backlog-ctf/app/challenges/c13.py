"""c13 — CVE-2026-84202 : ModelScope parses a model's configuration.yaml with
yaml.Loader -> `!!python/object/apply` runs code at model-load time."""
import yaml
from flask import Flask, request, jsonify

FLAG = "FLAG{modelscope_yaml_l0ader_rce}"       # written to /flag by serve.py
app = Flask(__name__)

@app.get("/")
def home():
    return jsonify(service="ModelScope hub",
                   hint="POST a model configuration.yaml to /models/load")

@app.post("/models/load")
def load():
    cfg = request.get_data()
    try:
        obj = yaml.load(cfg, Loader=yaml.Loader)   # BUG: full (unsafe) Loader on untrusted config
    except Exception as e:
        return jsonify(error=str(e)), 400
    return jsonify(config=str(obj))
