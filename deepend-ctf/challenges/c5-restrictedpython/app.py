#!/usr/bin/env python3
"""
c5/CVE-2026-76825 — RestrictedPython string.Formatter sandbox escape.

The "report" renderer treats user templates as safe because it only uses
`str.format()` — but Formatter field resolution (`{x.attr[item]}`) walks
attributes and items with plain getattr/getitem, NOT the sandbox's guarded
accessor. So a format field can traverse `__class__ -> __init__ -> __globals__`
and read module globals the sandbox is supposed to hide. (Real CVE reaches
builtins/RCE the same way; here the prize is the hidden FLAG global.)

Isolated training range — do not deploy.
"""
from flask import Flask, request, Response

FLAG = "0DAY{r3str1ct3dpy_f0rmatt3r_gl0bals_3scap3}"   # module global, not in the context


def safer_getattr(obj, name):
    # the sandbox's guarded accessor — blocks dunders on the "normal" path
    if name.startswith("_"):
        raise AttributeError("access to %r is not allowed" % name)
    return getattr(obj, name)


class ReportContext:
    def __init__(self, viewer):
        self.viewer = viewer
        self.title = "Quarterly Report"


app = Flask(__name__)


@app.get("/")
def home():
    return Response("Report renderer. POST a template; fields like {ctx.title} are "
                    "filled from your context.\nExample: curl -d '{ctx.title}' :80/render\n",
                    mimetype="text/plain")


@app.post("/render")
def render():
    tpl = request.get_data().decode("utf-8", "replace")
    ctx = ReportContext(viewer="guest")
    # we consider str.format "safe" (it can't call anything)... so no guard here.
    try:
        out = tpl.format(ctx=ctx)            # <-- Formatter bypasses safer_getattr
    except Exception as e:
        return Response("render error: %s" % e, status=400, mimetype="text/plain")
    return Response(out, mimetype="text/plain")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, threaded=True)
