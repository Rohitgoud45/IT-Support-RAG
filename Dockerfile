# --- build the React front end ---
FROM node:20-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# --- python API + built UI ---
FROM python:3.11-slim
WORKDIR /srv
ENV PYTHONUNBUFFERED=1
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Non-root user; /srv must be writable because the index (chroma_db/) is built there at startup
RUN useradd --create-home app && chown app /srv
USER app
# Pre-download the embedding model so the first request isn't slow
RUN python -c "from chromadb.utils.embedding_functions import DefaultEmbeddingFunction as E; E()(['warm up'])"
COPY app ./app
COPY data ./data
COPY eval ./eval
COPY --from=web /web/dist ./frontend/dist
ENV PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
