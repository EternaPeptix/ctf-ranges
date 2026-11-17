FROM python:3.12-slim
WORKDIR /s
RUN pip install --no-cache-dir \
      "psycopg2-binary==2.9.9" "PyMySQL==1.1.1" "paramiko==3.4.1" "requests==2.32.3" >/dev/null
COPY solve.py ./
CMD ["python", "-u", "solve.py"]
