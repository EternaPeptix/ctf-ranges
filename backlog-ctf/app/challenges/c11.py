"""c11 — CVE-2026-68771 : ComfyUI unauth `.pkl` upload fed to pickle.load -> RCE."""
import pickle
from flask import Flask, request, jsonify

FLAG = "FLAG{comfyui_unauth_p1ckl3_rce}"       # written to /flag by serve.py
app = Flask(__name__)

@app.get("/")
def home():
    return jsonify(service="ComfyUI",
                   hint="POST a pickled training dataset to /upload/image (it gets unpickled)")

@app.post("/upload/image")
def upload():
    data = request.get_data()
    try:
        obj = pickle.loads(data)               # BUG: LoadTrainingDataset unpickles untrusted input
    except Exception as e:
        return jsonify(error=str(e)), 400
    return jsonify(loaded=str(obj))
