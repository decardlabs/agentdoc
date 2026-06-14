# Multi-Agent Systems

Single agents are powerful, but some tasks benefit from multiple agents working together. This document explains when and how to build multi-agent systems.

## Why Multiple Agents?

| Problem | Multi-agent solution |
|---------|---------------------|
| Context window overflow | Split work across agents; each sees only its relevant context |
| Specialisation | Each agent is an expert in one domain |
| Parallelism | Independent sub-tasks run concurrently |
| Verification | A second agent reviews the first agent's work |
| Long-horizon tasks | Break across agents to manage state and cost |

---

## Core Patterns

### 1. Orchestrator–Worker

An **orchestrator** agent breaks down the goal and delegates sub-tasks to specialised **worker** agents.

```
                 ┌─────────────────┐
    User ──────► │  Orchestrator   │
                 └───────┬─────────┘
                         │ delegates tasks
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
   ┌──────────┐   ┌──────────┐   ┌──────────┐
   │ Research │   │  Coder   │   │ Reviewer │
   │  Agent   │   │  Agent   │   │  Agent   │
   └──────────┘   └──────────┘   └──────────┘
```

```python
class OrchestratorAgent:
    def __init__(self, workers: dict[str, "WorkerAgent"]):
        self.workers = workers  # {"research": ..., "coder": ..., "reviewer": ...}

    def run(self, task: str) -> str:
        plan = self._plan(task)          # Break into sub-tasks
        results = {}
        for step in plan:
            worker = self.workers[step["agent"]]
            results[step["id"]] = worker.run(step["instruction"])
        return self._synthesise(task, results)

    def _plan(self, task: str) -> list[dict]:
        # Use the LLM to produce a structured plan
        ...

    def _synthesise(self, task: str, results: dict) -> str:
        # Use the LLM to combine results into a final answer
        ...
```

### 2. Pipeline

Agents form a linear chain; each agent's output becomes the next agent's input.

```
User input → Agent A → Agent B → Agent C → Final output
```

Example: a content-generation pipeline.

```python
def content_pipeline(topic: str) -> str:
    outline = outline_agent.run(f"Create an outline for: {topic}")
    draft   = writing_agent.run(f"Write an article from this outline:\n{outline}")
    edited  = editing_agent.run(f"Edit this article for clarity and grammar:\n{draft}")
    return edited
```

### 3. Debate / Critique

Two agents challenge each other's answers, producing a higher-quality final result.

```python
def debate(question: str, rounds: int = 2) -> str:
    answer_a = agent_a.run(question)
    answer_b = agent_b.run(f"Critique and improve this answer:\n{answer_a}")
    for _ in range(rounds - 1):
        answer_a = agent_a.run(f"Respond to this critique:\n{answer_b}")
        answer_b = agent_b.run(f"Evaluate and improve:\n{answer_a}")
    return answer_b
```

### 4. Parallel Fan-Out / Fan-In

Independent sub-tasks run in parallel; results are aggregated.

```python
import concurrent.futures


def parallel_research(topics: list[str]) -> str:
    with concurrent.futures.ThreadPoolExecutor() as executor:
        findings = list(executor.map(research_agent.run, topics))

    combined = "\n\n".join(f"**{t}**\n{f}" for t, f in zip(topics, findings))
    return synthesiser_agent.run(f"Synthesise these research findings:\n{combined}")
```

### 5. Supervisor / Safety Check

A supervisor agent monitors another agent's actions and can veto or modify them before execution.

```python
def supervised_action(agent, task: str, supervisor) -> str:
    proposed_action = agent.plan(task)         # Agent proposes but does not act
    approved = supervisor.review(proposed_action)

    if approved["safe"]:
        return agent.execute(proposed_action)
    else:
        return f"Action blocked: {approved['reason']}"
```

---

## Communication Between Agents

Agents communicate through **shared message passing**. Each agent is, at its core, just a function: `(input: str) -> str`.

For more complex coordination, use a structured **task object**:

```python
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Task:
    id: str
    instruction: str
    context: dict[str, Any] = field(default_factory=dict)
    result: str | None = None
    status: str = "pending"  # pending | running | done | failed
```

---

## Shared Memory

Agents in a multi-agent system often need a shared working memory — a place to read and write intermediate results.

```python
class SharedMemory:
    def __init__(self):
        self._store: dict[str, str] = {}

    def write(self, key: str, value: str) -> None:
        self._store[key] = value

    def read(self, key: str) -> str | None:
        return self._store.get(key)

    def keys(self) -> list[str]:
        return list(self._store.keys())
```

Expose `SharedMemory` as a tool so agents can read/write to it within the standard tool-calling loop:

```python
memory = SharedMemory()

def memory_write(key: str, value: str) -> str:
    memory.write(key, value)
    return f"Stored '{key}'."

def memory_read(key: str) -> str:
    result = memory.read(key)
    return result if result is not None else f"No value found for '{key}'."
```

---

## Handoff Protocol

When one agent passes work to another, use a consistent handoff message format:

```python
def handoff(from_agent: str, to_agent: str, task: str, context: str) -> str:
    return (
        f"[Handoff from {from_agent}]\n"
        f"Task: {task}\n"
        f"Context so far:\n{context}\n"
        f"Please continue from here."
    )
```

---

## Practical Example: Software Development Agent

```
User: "Build a Python CLI tool that converts CSV to JSON."

Orchestrator
  ├─► Architect Agent  →  design doc (data flow, CLI interface)
  ├─► Coder Agent      →  implementation (csv_to_json.py)
  ├─► Test Agent       →  unit tests (test_csv_to_json.py)
  └─► Reviewer Agent   →  code review + suggested fixes
```

```python
def software_agent_demo(feature_request: str) -> dict[str, str]:
    design  = architect_agent.run(f"Design a solution for: {feature_request}")
    code    = coder_agent.run(f"Implement this design:\n{design}")
    tests   = test_agent.run(f"Write unit tests for:\n{code}")
    review  = reviewer_agent.run(f"Review this code and tests:\n{code}\n\nTests:\n{tests}")

    return {
        "design":  design,
        "code":    code,
        "tests":   tests,
        "review":  review,
    }
```

---

## Frameworks for Multi-Agent Systems

You do not need to build the orchestration layer from scratch. Established frameworks:

| Framework | Language | Key strength |
|-----------|----------|-------------|
| [LangGraph](https://github.com/langchain-ai/langgraph) | Python | Stateful graph-based workflows |
| [AutoGen](https://github.com/microsoft/autogen) | Python | Conversational multi-agent patterns |
| [CrewAI](https://github.com/crewAIInc/crewAI) | Python | Role-based agent teams |
| [smolagents](https://github.com/huggingface/smolagents) | Python | Lightweight, code-first agents |
| [Mastra](https://mastra.ai) | TypeScript | Agent workflows with observability |

---

## Common Pitfalls

| Pitfall | Mitigation |
|---------|-----------|
| **Agent loops** — agents keep handing off to each other | Set a maximum hop count; detect cycles |
| **Context loss between handoffs** | Include full context in every handoff message |
| **Cascading failures** — one agent fails, everything stops | Implement fallback paths; surface partial results |
| **Cost explosion** — many agents × many tokens | Set per-agent token budgets; cache intermediate results |
| **Inconsistent outputs** — agents contradict each other | Use a single orchestrator to reconcile conflicting answers |

---

## Further Reading

- [AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation](https://arxiv.org/abs/2308.08155) — Wu et al., 2023
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [CrewAI Documentation](https://docs.crewai.com/)
- [Agents Toward Alignment and Safety](https://arxiv.org/abs/2401.05566)
