# PyYAML 5.3.1 is the last release vulnerable to CVE-2020-14343; use a Python
# base old enough to have a prebuilt wheel for it.
FROM python:3.9-slim
WORKDIR /app
RUN pip install --no-cache-dir flask==2.2.5 'PyYAML==5.3.1' >/dev/null
COPY app.py ./
EXPOSE 80
CMD ["python", "-u", "app.py"]
