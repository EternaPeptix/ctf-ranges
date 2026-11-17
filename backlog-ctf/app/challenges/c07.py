"""c07 — CVE-2026-54640 : OpenRemote KNX ETS import parses uploaded XML with
external-entity resolution enabled -> XXE file read."""
from flask import Flask, request, Response
from lxml import etree

FLAG = "FLAG{openremote_ets_xxe_f1le_r34d}"    # written to /flag by serve.py
app = Flask(__name__)

@app.get("/")
def home():
    return Response("OpenRemote KNX importer. POST an ETS project (XML) to /asset/import\n",
                    mimetype="text/plain")

@app.post("/asset/import")
def imp():
    data = request.get_data()
    # DTD + external entities enabled (the vulnerability)
    parser = etree.XMLParser(resolve_entities=True, load_dtd=True, no_network=False)
    try:
        root = etree.fromstring(data, parser)
    except Exception as e:
        return Response("import failed: " + str(e), status=400)
    return Response("imported group address: " + (root.text or ""), mimetype="text/plain")
