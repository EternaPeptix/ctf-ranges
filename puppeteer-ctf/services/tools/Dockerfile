FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir flask==3.0.3 >/dev/null

# Stage-3 loot: the flag the RCE reads, and operator notes that reveal the
# admin RAG collection (stage 4 target).
RUN printf '%s\n' 'PUP{fl0w1se_mcp_std10_c0mmand_1nj3ct10n}' > /flag && \
    mkdir -p /srv && printf '%s\n' \
      '# Helm tool-host notes (ops only)' \
      'The admin agent keeps its private knowledge base in the vector store:' \
      '  collection: kb_7f3a_admin' \
      '  tenant:     tenant_admin' \
      'Reach it via the kb_search tool. The store addresses collections by name.' \
      '' \
      'Model loader: POST http://models/load {"repo":"<url>"} -> from_pretrained(),' \
      'which instantiates the class named in the repo config.json.' \
      > /srv/agent-notes.txt

COPY app.py ./
EXPOSE 80
CMD ["python", "-u", "app.py"]
