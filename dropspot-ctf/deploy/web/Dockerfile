FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends git >/dev/null \
 && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir flask==3.0.3 >/dev/null
WORKDIR /app
COPY app.py ./
COPY public ./public

# Build the exposed .git: commit a secret, then "remove" it — but it lives on in
# history forever (flag 1). `git update-server-info` makes dumb-HTTP clone work.
RUN set -e; cd public; \
    git init -q; git config user.email dev@dropspot.example; git config user.name "dropspot dev"; \
    printf 'JWT_SECRET=s3cr3t\nADMIN_USER=admin\nADMIN_PASS=hunter2\n# found me? DS{g1t_d1r_expos3d_s3cr3ts_l1v3_1n_h1st0ry}\n' > .env; \
    git add -A; git commit -q -m "initial dropspot app + config"; \
    git rm -q .env; printf '.env\n' > .gitignore; git add -A; \
    git commit -q -m "stop committing secrets to the repo (removed .env)"; \
    git update-server-info

EXPOSE 80
CMD ["python", "-u", "app.py"]
