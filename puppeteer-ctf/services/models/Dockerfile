FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir flask==3.0.3 requests==2.32.3 >/dev/null

# Stage-5 loot: the flag the RCE reads, and the owner's memory credentials
# (the finale's stage-6 target) kept on the model host.
RUN printf '%s\n' 'PUP{l3r0b0t_from_pr3train3d_c0nf1g_cl4ss_rc3}' > /flag && \
    mkdir -p /srv && printf '%s\n' \
      '# Memory access notes (model host — do not distribute)' \
      'owner_user:            a11ce' \
      'owner_memory_id:       mem_a11ce      # the owner private memory (finale target)' \
      'agent_service_token:   mem-svc-7c2a9d # the Helm agent low-scope memory token' \
      'endpoint:  GET http://memory/api/memories?collection_id=mem_a11ce' \
      '           header X-Memory-Token: <agent_service_token>' \
      'warning:   the memory API does not bind collection_id to the token scope,' \
      '           so the agent service token can read the owner collection by id.' \
      > /srv/owner.txt

COPY app.py ./
EXPOSE 80
CMD ["python", "-u", "app.py"]
