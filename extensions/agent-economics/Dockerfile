FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir boto3 mcp[cli] fastmcp
COPY server.py .
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD curl -sf http://localhost:8000/mcp || exit 1
ENTRYPOINT ["python", "server.py"]
