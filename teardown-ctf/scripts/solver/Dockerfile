FROM python:3.12-slim
RUN pip install --no-cache-dir pwntools==4.13.1 >/dev/null
WORKDIR /s
COPY solve.py ./
COPY bins ./bins
CMD ["python3", "-u", "solve.py"]
