# Word Wall

A live, collaborative word wall — submit a word and watch it appear in real-time.

## Quickstart

```bash
# Install dependencies
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run the server
uvicorn app:app --reload
```

Open [http://localhost:8000](http://localhost:8000) in your browser.

Two views:
- **Submit** (default) — enter your name, type a word and send it to the wall.
- **Live wall** (`?mode=admin`) — watch words appear in real-time with author names.

## Configuration

### Custom port (local)

```bash
uvicorn app:app --port 3000
```

### Custom port (Docker)

```bash
docker build -t wordwall .
docker run -p 3000:8000 -e PORT=3000 wordwall
```

### Helm resources

The Helm chart exposes container CPU and memory requests/limits via `resources` in `charts/wordwall/values.yaml`.

```yaml
resources:
  requests:
    cpu: 100m
    memory: 128Mi
  limits:
    cpu: 500m
    memory: 256Mi
```

Override them at install/upgrade time with your own values file or `--set`, for example:

```bash
helm upgrade --install wordwall charts/wordwall \
  --set resources.requests.cpu=200m \
  --set resources.requests.memory=256Mi \
  --set resources.limits.cpu=1 \
  --set resources.limits.memory=512Mi
```

## How it worksq

- **FastAPI** serves the app and manages an in-memory word store.
- **Server-Sent Events** (`/events`) streams new words to the live wall view.
- Heartbeat pings (every 15s) keep the connection alive.
- Each word stores the author's name and server-detected hostname.

## Tech stack

- Python 3.11+
- FastAPI
- Uvicorn
