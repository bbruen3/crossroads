# Crossroads

FastAPI service sitting between Open WebUI and downstream model services.
Implements an OpenAI-compatible API surface with intent classification,
pipe-based context enrichment, and dynamic model routing.

## Quick start

```bash
cp .env.example .env
# edit .env with your values
docker compose up -d
```

## Architecture

See the GitHub issue for full architecture documentation.

## Adding pipes

Drop a `.py` file implementing `BasePipe` into `./pipes/`.
It will be hot-loaded without a restart.
