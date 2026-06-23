# Personal Agentic Assistant System
### Architecture & Requirements Specification
**Version 1.1 | June 2026**

---

## Grilling Session Status

A full grilling session was completed (June 2026). All major design branches have been resolved. The decisions below supersede or extend Version 1.0.

**What was decided:**
- Stack, hosting, agent framework, LLM strategy
- Detailed data model for Tasks / Habits / Reminders
- Notes vault structure and system write boundaries
- Revised build sequence (Tasks first, not Library)
- Web app MVP scope and authentication
- Telegram UX pattern (inline buttons vs. free text)

**What remains for future grilling / planning:**
- LangGraph conversation state persistence design (how context survives between Telegram messages hours apart)
- Connection discovery confidence threshold (concrete definition)
- Exact habit schema fields beyond name, frequency, start date
- Notes tagging taxonomy (which tags to define, naming conventions)
- rclone sync strategy (frequency, conflict resolution)

---

## 1. Overview

This system is a personal agent that helps manage tasks, reminders, and habits, while also giving access to a personal knowledge base built from notes, books, and articles. It is not a single monolithic application — it is composed of independent, focused services, coordinated by an agentic orchestrator that the user interacts with through a Telegram bot and a web application.

The system is built around a simple principle: **each type of personal data is served by the technology suited to it**, rather than forcing tasks, notes, and reference material into a single retrieval pipeline.

---

## 2. Goals

- Track tasks, reminders, and habits, with the assistant proactively checking in — not just responding when asked.
- Maintain a personal vault of self-authored notes that is fast to search and easy to browse.
- Maintain a separate library of full source material (books, articles, PDFs) that can answer deep questions with content grounded in those specific sources — not generic model knowledge or web search.
- Automatically surface connections between topics the user may not have noticed themselves.
- Provide two complementary interfaces: a Telegram bot for quick, on-the-go interaction, and a web app for focused review and editing.

---

## 3. System Architecture

The system consists of three independent microservices and one coordinating orchestrator agent.

```
                    ┌─────────────────────────┐
                    │   Orchestrator Agent     │
                    │  (Telegram bot + Webapp) │
                    └────────────┬─────────────┘
                                 │
        ┌────────────────────────┼────────────────────────┐
        │                        │                         │
┌───────▼────────┐      ┌────────▼─────────┐      ┌────────▼─────────┐
│  Tasks Service  │      │  Notes Service   │      │  Library Service  │
│  (PostgreSQL)   │      │  (Obsidian vault │      │  (ChromaDB RAG)   │
│                 │      │   via rclone)    │      │                   │
│ Tasks           │      │ Self-authored    │      │ Books / PDFs /    │
│ Habits          │      │ notes (owned     │      │ Articles          │
│ Reminders       │      │ by user)         │      │ Full source       │
│                 │      │ /library-mirrors │      │ material,         │
│                 │      │ /connections     │      │ embeddings        │
│                 │      │ (owned by system)│      │                   │
└─────────────────┘      └──────────────────┘      └───────────────────┘
```

**Guiding principle:** each service owns one responsibility, implemented with the technology that fits it. Services do not call each other directly — only the orchestrator is aware of all three and decides, per interaction, which to use.

---

## 4. Technology Stack

| Layer | Technology |
|---|---|
| Backend services | Python + FastAPI |
| Frontend | TypeScript + React |
| Agent framework | LangGraph |
| LLM interface | LiteLLM (provider-agnostic) |
| LLM provider (start) | Groq (free tier) |
| Tasks database | PostgreSQL |
| Library vector store | ChromaDB |
| Notes storage | Obsidian vault on Google Drive, synced to server via rclone |
| Deployment | Docker Compose |
| Web app auth | Google OAuth |
| Proactive scheduling | cron-job.org (external cron pinging the server) |

**LLM strategy:** LiteLLM wraps all LLM calls so the provider (Groq, Claude, OpenAI, etc.) can be swapped by changing a model string and API key. No provider-specific code in business logic.

---

## 5. Hosting

**Target:** Oracle Cloud Free Tier (2 always-on VMs, no expiry).
**Fallback:** Render or Railway free tier + cron-job.org pinging an endpoint on schedule to work around sleep-on-inactivity.

The system requires always-on hosting because the orchestrator initiates proactive Telegram messages — it cannot wait to be woken by an inbound request.

---

## 6. Tasks / Reminders / Habits Service

### 6.1 Data Model

Three distinct concepts, each with different behavior:

**Habits**
- A recurring behavior tied to a personal goal the user wants to track over time.
- Fields: name, target frequency (N times per week or per day), start date, completion log (timestamped entries).
- Purpose: allow looking back and comparing actual behavior against the stated goal (e.g., "gym 3/4 times this week").

**Tasks**
- A one-off thing to complete and not forget.
- Fields: title, optional due date/time, completion status.
- No recurrence, no goal comparison — just done or not done.

**Reminders**
- A scheduled trigger for thinking about something, not a task itself.
- A reminder fires → the user is notified → the user creates whatever tasks are needed.
- Example: "wife's birthday" fires → user creates "buy flowers" and "write card" as separate tasks.
- **MVP behavior:** notification only. The system sends the reminder message; the user creates tasks manually.
- **Future enhancement:** the reminder opens a conversation — the agent proposes tasks and the user confirms or edits.

### 6.2 Proactive Behavior

Two proactive check-ins per day maximum:

| Time | Message | Format |
|---|---|---|
| Morning | "Do you want to go over your open tasks for today?" | Free text reply |
| End of day | "Did you go to the gym?" (per scheduled habit) | Inline Yes / No buttons |

The data and logic about what *should* have happened lives in this service. The scheduling and message-sending lives in the Orchestrator.

### 6.3 Independence

This service does not automatically query Notes or Library. Cross-referencing with the knowledge base only happens when the user explicitly asks a question that spans both (e.g., "what did I write about the project I have a reminder for tomorrow?").

---

## 7. Notes Service (Obsidian Vault)

### 7.1 Purpose

The primary repository for self-authored notes. The user continues using Obsidian as their primary editor — the Notes service does not replace it.

### 7.2 Technology

- Vault lives in Google Drive; the user accesses it locally via Obsidian.
- The Notes service syncs the vault to the server using **rclone**, operates on local Markdown files, then syncs changes back to Google Drive.
- Full-text / keyword search over Markdown files — not vector-based retrieval.

### 7.3 Vault Structure and Write Boundaries

The system **never modifies notes the user has written**. It writes only to two designated folders:

| Folder | Content | Owner |
|---|---|---|
| `/library-mirrors/` | Auto-generated draft summaries of Library sources | System |
| `/connections/` | MOC-style notes linking related topics discovered by the connection job | System |
| Everything else | User's own notes | User |

**Organization principle:**
- **Tags** answer "what type of note is this?" (e.g., `#explanation`, `#daily-note`, `#MOC`, `#library-mirror`).
- **Links** (wikilinks) answer "how does this connect to other notes?" — they replace folder hierarchy for most organizational purposes.
- **Privacy:** notes tagged `#sensitive` are never sent to any external API or LLM.

### 7.4 Library Mirror

Whenever a new source is ingested into the Library Service, a draft summary note is automatically generated in `/library-mirrors/` (title, topic, key points, tagged `#library-mirror`). The user can leave it as-is or edit it freely in Obsidian.

### 7.5 Connection Discovery

Scans notes — including library mirror notes — and writes MOC-style notes in `/connections/` when meaningful connections between topics are found.

- Never queries Library directly — operates only on notes (fast and lightweight).
- Never modifies user-written notes — all output goes to `/connections/`.

**Implementation plan:**
- **Phase 1 (MVP):** A Claude Code skill (`/find-connections`) run manually or on a schedule against the local Obsidian vault. Claude reads the notes, finds connections, and writes to `/connections/`. Google Drive syncs the results back. No server-side service needed; connection quality is Claude's judgment rather than a tuned threshold.
- **Phase 2 (expansion):** If automation or integration with the orchestrator is needed, replace or supplement the skill with a scheduled Python service on the server.

---

## 8. Library Service

### 8.1 Purpose

An archive of full source material — books, PDFs, articles. Its single responsibility is to answer deep, source-grounded questions on demand.

### 8.2 Technology

ChromaDB (running as a Docker container) for vector storage. Classic RAG: text extraction, semantic chunking, embeddings, retrieval-augmented generation via LiteLLM.

### 8.3 Ingestion Flow

```
New source (PDF / link / book)
        ↓
Text extraction + chunking + embedding into ChromaDB
        ↓
LLM generates a draft summary
        ↓
Draft summary written as new note in /library-mirrors/ (Notes)
        ↓
User optionally edits the note in Obsidian
```

### 8.4 Usage

Queried only when the user asks a question requiring depth or direct grounding in a specific source. Not used for everyday browsing or background search.

---

## 9. Orchestrator Agent

### 9.1 Purpose

The agent the user interacts with directly. It initiates contact based on state and time, not only responds to messages.

Responsibilities:
- Routes everyday requests to the appropriate service (most often Tasks).
- Combines information across services only when the user explicitly asks a cross-cutting question.
- Triggers the Library ingestion flow when a link or source is submitted.
- Runs the Notes connection-discovery job on a scheduled interval.
- Sends proactive check-ins and manages the multi-turn conversations that follow.

### 9.2 Implementation

- **Framework:** LangGraph — handles stateful multi-turn conversations natively, required for proactive check-ins that continue based on the user's response.
- **LLM:** LiteLLM with Groq as the starting provider. Provider is swappable without changing business logic.
- **Tools:** the three services are exposed as tools the agent selects between, rather than static routing logic.

### 9.3 Interfaces

| | **Telegram Bot** | **Web App** |
|---|---|---|
| Context | On the go, quick, spontaneous (phone) | At the desk, focused session |
| Tasks | Create reminders/tasks; proactive check-ins | Dashboard, editing |
| Habits | Inline button check-ins | History, streaks, goal comparison |
| Library | Ingest new links/sources | Ask in-depth questions, browse results |
| Notes | — | Browse (Obsidian remains primary editor) |
| Auth | Telegram identity | Google OAuth |

### 9.4 Telegram UX Pattern

- **Proactive habit check-ins:** inline Yes / No buttons. Fast to respond on a phone; unambiguous for the system to parse.
- **Everything else:** free text. Task creation, questions, Library ingestion, morning task review.

---

## 10. Web App

### 10.1 Authentication

Google OAuth. Single sign-in with no password to manage; consistent with Google Drive already being in the system.

### 10.2 MVP Scope

**Anchor feature: habit history and streaks.** A visual dashboard showing completion history over time (e.g., calendar heatmap) and progress against the stated goal frequency. This is the one thing Telegram cannot provide and the primary reason to open a browser.

Secondary features (post-MVP):
- Task dashboard and editing
- Library question interface and retrieval results browser

---

## 11. Privacy & Security

- Notes tagged `#sensitive` are never sent to any external service and are excluded from all LLM calls.
- API keys, bot tokens, and OAuth credentials are stored in environment configuration files, never committed to source code.
- Each service defines its own policy for what is permitted to leave the local environment.
- Google OAuth restricts web app access to the authenticated user only.

---

## 12. Build Sequence

Built incrementally in an order that maximizes early value and minimizes wasted work if adoption fails:

1. **Tasks Service + Orchestrator** — the daily-use core. Telegram bot with proactive check-ins, habit tracking, task/reminder management. This is what gets used every day and proves whether the system will stick.
2. **Library Service** — ChromaDB RAG, ingestion flow, library mirror note generation. Added once the core habit is established.
3. **Notes Integration** — rclone sync, connection discovery job, `/connections/` MOC generation. Built last because it depends on Library (for mirror notes) and has the most remaining open design questions.
4. **Web App** — built once Tasks and Library APIs are stable. Habit history dashboard first, then task editing and Library browsing.

---

*This document defines the target architecture for implementation planning. Next step: `/architect` to produce an implementation plan for Phase 1 (Tasks Service + Orchestrator).*
