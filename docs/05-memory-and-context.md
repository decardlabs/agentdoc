# Memory & Context

Memory is how an agent maintains state — across steps within a single task, and across entirely separate sessions. This document explains the three memory tiers, the retrieval-augmented generation (RAG) pattern, and practical implementation guidance.

## The Three Memory Tiers

| Tier | Scope | Storage | Analogy |
|------|-------|---------|---------|
| **In-context** | Current conversation | LLM prompt | Working memory |
| **External / retrieved** | Query-time retrieval | Vector store, DB | Long-term memory |
| **Persistent state** | Cross-session | Database / file | Notebook |

---

## 1. In-Context Memory (Short-Term)

Everything in the current prompt is in-context memory. It includes:

- The system prompt (persona, instructions, available tools)
- The conversation history (user and assistant turns)
- Tool call results

```python
messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "My name is Alice."},
    {"role": "assistant", "content": "Nice to meet you, Alice!"},
    {"role": "user", "content": "What is my name?"},
]
# The model can answer "Alice" because the name is in the conversation history.
```

### Context window limits

Every model has a maximum context window (measured in tokens). When the conversation grows too long, you must summarise or truncate old messages.

**Sliding window** — keep only the last N turns:

```python
MAX_HISTORY = 20  # Keep the last 20 messages

def trim_history(messages: list[dict]) -> list[dict]:
    system = [m for m in messages if m["role"] == "system"]
    non_system = [m for m in messages if m["role"] != "system"]
    return system + non_system[-MAX_HISTORY:]
```

**Summarisation** — use the model itself to compress old turns:

```python
def summarise_history(messages: list[dict], client) -> str:
    old_text = "\n".join(f"{m['role']}: {m['content']}" for m in messages)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": f"Summarise this conversation in 3–5 sentences:\n\n{old_text}"}
        ],
    )
    return response.choices[0].message.content
```

---

## 2. Retrieval-Augmented Generation (RAG)

RAG lets an agent answer questions about a large knowledge base (documentation, emails, codebases) that would be far too large to fit in a single prompt.

### How RAG works

```
┌────────────────────────────────────────────┐
│              Indexing (offline)             │
│                                            │
│  Documents → Chunks → Embeddings → Store   │
└────────────────────────────────────────────┘

┌────────────────────────────────────────────┐
│             Querying (at runtime)           │
│                                            │
│  Question → Embed → Search → Top-k chunks  │
│       → Inject into prompt → Answer        │
└────────────────────────────────────────────┘
```

### Step 1 — Chunk documents

Split large documents into passages of ~200–500 tokens. Overlap adjacent chunks slightly to avoid cutting sentences in half.

```python
def chunk_text(text: str, chunk_size: int = 400, overlap: int = 50) -> list[str]:
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i : i + chunk_size])
        chunks.append(chunk)
        i += chunk_size - overlap
    return chunks
```

### Step 2 — Embed and store

```python
from openai import OpenAI
import chromadb  # pip install chromadb

client = OpenAI()
chroma = chromadb.Client()
collection = chroma.get_or_create_collection("knowledge_base")


def embed(text: str) -> list[float]:
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text,
    )
    return response.data[0].embedding


def index_document(doc_id: str, text: str) -> None:
    chunks = chunk_text(text)
    embeddings = [embed(c) for c in chunks]
    ids = [f"{doc_id}_{i}" for i in range(len(chunks))]
    collection.add(documents=chunks, embeddings=embeddings, ids=ids)
```

### Step 3 — Retrieve at query time

```python
def retrieve(query: str, top_k: int = 5) -> list[str]:
    query_embedding = embed(query)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
    )
    return results["documents"][0]
```

### Step 4 — Inject into the prompt

```python
def answer_with_rag(question: str) -> str:
    passages = retrieve(question)
    context = "\n\n---\n\n".join(passages)

    messages = [
        {
            "role": "system",
            "content": (
                "Answer the question using ONLY the context below. "
                "If the answer is not in the context, say 'I don't know'.\n\n"
                f"Context:\n{context}"
            ),
        },
        {"role": "user", "content": question},
    ]

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
    )
    return response.choices[0].message.content
```

---

## 3. Persistent State (Cross-Session Memory)

For long-running agents or personal assistants, you often need to remember information *between* separate conversations.

### User facts store

Store specific facts about a user that are relevant across sessions:

```python
import json
import pathlib


class UserMemory:
    def __init__(self, user_id: str):
        self.path = pathlib.Path(f"memory/{user_id}.json")
        self.path.parent.mkdir(exist_ok=True)
        self.facts: list[str] = json.loads(self.path.read_text()) if self.path.exists() else []

    def add(self, fact: str) -> None:
        self.facts.append(fact)
        self.path.write_text(json.dumps(self.facts, indent=2))

    def get_all(self) -> list[str]:
        return self.facts

    def as_prompt_text(self) -> str:
        if not self.facts:
            return ""
        return "Known facts about the user:\n" + "\n".join(f"- {f}" for f in self.facts)
```

Usage in the agent:

```python
memory = UserMemory("alice")
memory.add("Prefers metric units.")
memory.add("Works in Tokyo timezone (JST).")

system_prompt = f"""You are a helpful assistant.
{memory.as_prompt_text()}"""
```

### Episodic memory with a vector store

For richer recall, store summaries of past conversations and retrieve relevant ones at the start of each new session:

```python
def save_episode(session_id: str, summary: str) -> None:
    embedding = embed(summary)
    collection.add(
        documents=[summary],
        embeddings=[embedding],
        ids=[session_id],
        metadatas=[{"type": "episode"}],
    )


def recall_relevant_episodes(new_message: str, top_k: int = 3) -> list[str]:
    q_embedding = embed(new_message)
    results = collection.query(
        query_embeddings=[q_embedding],
        n_results=top_k,
        where={"type": "episode"},
    )
    return results["documents"][0]
```

---

## Choosing the Right Memory Strategy

| Scenario | Recommended approach |
|----------|---------------------|
| Short task, single session | In-context only |
| Long task (>20 turns) | In-context + sliding window or summarisation |
| Q&A over large documents | RAG with vector store |
| Personal assistant (multi-session) | Persistent facts + episodic memory |
| High-stakes accuracy requirements | RAG + source citations |

---

## Common Pitfalls

| Pitfall | Mitigation |
|---------|-----------|
| **Context poisoning** — bad info early in context affects the whole run | Summarise and prune regularly |
| **Hallucination in RAG** — model ignores retrieved text | Instruct "Answer ONLY from context"; cite sources |
| **Stale retrieval index** — old documents returned | Schedule re-indexing; add timestamps to metadata |
| **Embedding drift** — re-embedding with a different model changes distances | Re-index everything when changing embedding models |
| **Memory privacy** — storing PII without consent | Apply access controls; respect data-deletion requests |

---

## Further Reading

- [Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks](https://arxiv.org/abs/2005.11401) — Lewis et al., 2020
- [MemGPT: Towards LLMs as Operating Systems](https://arxiv.org/abs/2310.08560) — Packer et al., 2023
- [Chroma Documentation](https://docs.trychroma.com/)
- [pgvector](https://github.com/pgvector/pgvector) — vector search for PostgreSQL
