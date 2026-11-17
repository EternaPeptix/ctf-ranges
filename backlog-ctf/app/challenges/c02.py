"""c02 — CVE-2026-96355 : Drupal Webform field rendered through the template
engine (Twig) -> SSTI. Re-impl with Jinja2 render_template_string."""
from flask import Flask, request, render_template_string

FLAG = "FLAG{drupal_webf0rm_twig_sst1}"   # also written to /flag by serve.py
app = Flask(__name__)
FORM = ('<h3>Contact us</h3><form method="post">'
        '<input name="message" placeholder="your message">'
        '<button>Send</button></form>')

@app.get("/")
@app.get("/form/contact")
def form():
    return FORM

@app.post("/form/contact")
@app.post("/")
def submit():
    msg = request.form.get("message", "")
    # the webform element value is rendered through the template engine (unsafe)
    return render_template_string("Thanks! We received your message: " + msg)
