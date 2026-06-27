# Coding Conventions

## Language & runtime
Python 3.11+.

## Naming
- Variables and functions: `snake_case`, full descriptive names. No single-character
  names, not even in loops (`for habit in habits`, not `for h in habits`).
- Boolean variables and functions: prefix with `is_`, `has_`, or `needs_`.
- Classes: `PascalCase`.
- Request/response schema classes: `<Entity>Create` and `<Entity>Update`.
- Files and modules: `snake_case`.

## Code style
- Formatter: **ruff** (`ruff format .`). Line length: 88.
- Linter: **ruff** (`ruff check .`). Rules: pycodestyle (E), pyflakes (F), isort (I).
- `__init__.py` files are always empty. Use explicit imports everywhere.

## Comments
- Comment only when the WHY is non-obvious: a hidden constraint, a subtle
  invariant, a workaround for a specific bug. Never comment what the code says.
- **Exception — LangGraph tool docstrings are mandatory.** They are the LLM's
  instruction for when and how to call the tool. Every `@tool` function must
  have a clear, specific docstring.

## Testing
- TDD: write tests before implementation for all code.
- Layer split:
  - `domain/` — unit tests, pure Python, no DB, no HTTP.
  - `api/` — integration tests, FastAPI TestClient against a real test Postgres DB.
  - `tools/` — mocked HTTP tests using respx.
- Test files: `test_<component>.py`. Test functions: `test_<what_it_does>`.
- Async tests run automatically via `asyncio_mode = auto` — no decorator needed.
