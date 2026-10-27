# Architecture & System Design — AI Customer Support Coaching Assistant

**Project:** AI Customer Support Coaching Assistant  
**Milestone:** Milestone 1 (Foundation, Session Setup & Knowledge Base RAG)  
**Status:** Live & Production Ready  

---

## 1. System Architecture Overview

The AI Customer Support Coaching Assistant is designed as an interactive coaching platform for frontline support agents. It combines dynamic conversation simulation, dense vector retrieval over enterprise support documents, and an orchestrated multi-agent feedback pipeline.

```
┌────────────────────────────────────────────────────────────────────────┐
│                        USER BROWSER (Streamlit UI)                     │
│                        http://localhost:8502                           │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTP / WebSocket
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        STREAMLIT FRONTEND                              │
│                                                                        │
│   Dashboard (views/setup.py)        ← KB ingestion, retrieval, setup   │
│   Sessions (views/sessions.py)      ← Saved sessions table & inspector │
│   Architecture (views/architecture) ← Architecture, models, notes      │
└───────────────┬──────────────────────────────────────────┬─────────────┘
                │                                          │
                ▼                                          ▼
┌────────────────────────────────┐       ┌───────────────────────────────┐
│       SESSION STORAGE          │       │      KNOWLEDGE BASE (RAG)     │
│       utils/storage.py         │       │      utils/rag_stub.py        │
│                                │       │                               │
│  - JSON files (data/sessions/) │       │  - pypdf text extractor       │
│  - Session data model schema   │       │  - 500-char / 50-overlap      │
│  - List, load, delete sessions │       │  - all-MiniLM-L6-v2 local emb │
│  - Restores state on load      │       │  - ChromaDB (data/chroma/)    │
│                                │       │  - Cosine distance retrieval  │
└───────────────┬────────────────┘       └───────────────┬───────────────┘
                │                                        │
                ▼                                        ▼
┌────────────────────────────────────────────────────────────────────────┐
│                     ORCHESTRATION LAYER                                │
│                     orchestrator/orchestrator.py                       │
│                                                                        │
│  - run_workflow(): coordinates session state, agents, and RAG          │
│  - Strict Pydantic contracts (WorkflowRequest / WorkflowResponse)      │
│  - In Milestone 1: stub returns {"status": "ready", ...}               │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                      SPECIALIZED AGENT ECOSYSTEM                       │
│                                                                        │
│  1. Customer Simulator Agent             (Milestone 2)                 │
│  2. Intent & Sentiment Agent             (Milestone 2)                 │
│  3. Knowledge Recommendation Agent       (Milestone 3)                 │
│  4. Coaching & Response Agent            (Milestone 3)                 │
│  5. Escalation Risk Monitor              (Milestone 3)                 │
│  6. Post-Interaction Summary Agent       (Milestone 4)                 │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Multi-Agent System Roles and Milestone Mapping

The multi-agent architecture divides coaching and conversational logic into modular, specialized agents governed by the orchestrator:

| Agent Name | Primary Responsibility | Input Context | Output Artifact | Milestone |
|---|---|---|---|:---:|
| **Customer Simulator Agent** | Generates realistic, turn-based customer messages based on selected persona, product, and scenario ladder. | Product context, scenario description, customer persona, previous dialogue turns | Simulated customer turn | **M2** |
| **Intent & Sentiment Agent** | Classifies customer intent and scores real-time sentiment, emotional state, and frustration score (0–100%). | Latest customer message, conversation history, product context | Intent category, sentiment tag, frustration score | **M2** |
| **Knowledge Recommendation Agent** | Performs dense semantic vector search over the enterprise support knowledge base for relevant policy chunks. | Customer turn, conversation intent, product context | Top-3 ranked policy passages with page numbers & scores | **M3** |
| **Coaching & Response Agent** | Evaluates agent replies for empathy, tone, conciseness, and generates contextual response guidance. | Agent reply or customer turn, recommended policy chunks, past turn scores | Empathy rating, clarity check, suggested next reply | **M3** |
| **Escalation Risk Monitor** | Tracks customer sentiment trajectories, identifying churn signals, supervisory demands, and SLA risk. | Frustration trend, repeat contact count, churn keywords | Escalation risk percentage (0–100%), warning flags, de-escalation strategy | **M3** |
| **Post-Interaction Summary Agent** | Synthesizes full session performance into resolution metrics, timeline graphs, and personalized coaching takeaways. | Complete session transcript, turn-by-turn scores, risk telemetry | Overall resolution quality (0–100), key strengths, growth areas | **M4** |

---

## 3. Orchestration & Data Flow

In Milestone 1, the orchestration pipeline is initialized with session creation and validation:

1. **Session Configuration:**
   - User configures mode (`Simulator`, `Manual`, `Replay`), product context (3–100 chars), and scenario (20–500 chars).
   - Mode-specific parameters (Persona, turns, or replay script) are selected dynamically.
2. **Pre-flight Validation:**
   - Input fields are validated via `utils/validation.py`.
   - The knowledge base is checked to ensure at least one document chunk is indexed.
3. **Session Instantiation & Persistence:**
   - A `Session` dataclass instance is initialized from `src/customer_support_coach/data_models.py`.
   - The session is saved to `data/sessions/<session_id>.json` via `utils/storage.py`.
4. **Workflow Execution:**
   - `orchestrator.run_workflow()` is invoked, returning a ready status stub confirming orchestration binding.
   - A flash notification confirms session initialization and updates the sidebar session list.

---

## 4. Knowledge Base (RAG) Architecture

The enterprise knowledge retrieval pipeline operates completely offline with local embeddings:

- **Ingestion & Extraction:** Multi-page PDF support documents are parsed using `pypdf`. Files above 20 MB are rejected. Scanned documents without extractable text trigger informative error messages.
- **Chunking Pipeline:** Raw text is divided into 500-character windows with a 50-character sliding overlap. Each chunk preserves source metadata (`doc_name` and `page`).
- **Embedding Pipeline:** Embeddings are generated using the `all-MiniLM-L6-v2` SentenceTransformer model (384-dimensional dense vectors).
- **Persistent Vector Store:** ChromaDB `PersistentClient` manages vector storage under `data/chroma/`, utilizing HNSW indexing configured for cosine distance.
- **Idempotent Upsert Deduplication:** Chunk IDs are generated from the document's SHA-256 hash combined with page and chunk indices (`<hash>_p<page>_c<idx>`). Uploading the same PDF repeatedly updates existing chunks without index bloat or duplicate results.
- **Query Retrieval:** Cosine similarity retrieves top-$k$ chunks ($k=3$), returning document name, page, text snippet, and a normalized similarity score ($1 - \text{distance}$).

---

## 5. Shared Data Models

All components communicate through strictly typed domain models defined in `src/customer_support_coach/data_models.py`:

- **`Session`**: Captures session ID, interaction mode, product context, scenario, customer persona, status, timestamps, and metadata.
- **`ConversationMessage`**: Represents an individual conversation turn, linking session ID, speaker (`customer`, `agent`, `system`), content, turn number, and timestamp.
- **`AgentResult`**: Standardized schema for multi-agent output, containing agent type, result payload, confidence, and timestamps.
- **Enums**: `InteractionMode`, `SessionStatus`, `Speaker`.
