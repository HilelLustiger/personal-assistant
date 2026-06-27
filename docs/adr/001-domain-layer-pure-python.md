# ADR 001 — Domain layer stays pure Python, no SQL filtering

**Date:** 2026-06-27
**Status:** Decided

## Context

The `tasks-service/domain/` layer contains functions that operate on lists of ORM
objects already loaded from the DB (e.g. `count_completions_in_range` filters a
pre-loaded list of `HabitLog` rows by date range). The same filtering could be done
in SQL directly, eliminating the need to load rows into memory.

## Decision

Keep the domain layer as pure Python functions that operate on plain Python objects.
Do not push date-range filtering or aggregation into SQL queries inside the routers.

## Reasons

- **Testability**: pure Python functions can be unit-tested with plain object lists —
  no DB, no mock, no test fixtures needed. This is the primary reason the domain layer
  exists.
- **Scale**: this is a single-user personal assistant. The dataset will never grow large
  enough for the in-memory filtering to matter. Hundreds of habit logs, not millions.
- **Logic visibility**: business rules written in Python are explicit and readable.
  The same rules written as SQL WHERE clauses in a router are harder to find and test.

## Consequences

- The API routers are responsible for loading the data; domain functions are responsible
  for computing derived values from it. This boundary must be respected — routers must
  not contain business logic, and domain functions must not contain DB calls.
- If the dataset ever grows significantly (it won't for this use case), revisit by
  replacing domain functions with SQL aggregates and adjusting the test strategy.
