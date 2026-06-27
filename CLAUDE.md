## Local development

### Prerequisites
- Python 3.11+
- Docker (for Postgres only)
- ruff: `pip install ruff`

### Setup

```bash
# Start Postgres
docker compose up db -d

# tasks-service
cd tasks-service
pip install -r requirements.txt
alembic upgrade head
uvicorn main:app --reload --port 8001

# orchestrator (separate terminal)
cd orchestrator
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Run tests

```bash
cd tasks-service && pytest
cd orchestrator && pytest
```

### Lint and format

```bash
ruff check .
ruff format .
```

---

## Agent skills

### Dev-team flow

`/frame` → `/architect` → `/challenger` → `/code-designer` →
`/sequencer` → `/coder` + `/devops` → `/reviewer` → `/document`

### Key files

| File | Written by | Read by |
|---|---|---|
| `CLAUDE/agreement.md` | architect | challenger, code-designer, sequencer |
| `CLAUDE/work-order.md` | sequencer | coder, devops, reviewer |
| `CLAUDE/status.md` | all skills | all skills |
| `docs/conventions.md` | setup | coder, reviewer, code-designer |
| `docs/context.md` | setup, document | architect |
| `docs/adr/` | document | architect |
| `docs/api/` | document | coder, reviewer |
