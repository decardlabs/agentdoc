# Introduction to AI Agents

## What is an AI Agent?

An **AI agent** is a software system that perceives its environment, reasons about what to do next, and takes actions to achieve a goal — repeatedly, in a loop, until the goal is met or a stopping condition is reached.

Unlike a simple API call to a language model (`prompt → response`), an agent:

1. **Observes** — receives input (user request, tool output, environment state)
2. **Thinks** — uses a language model or other reasoning component to decide what to do
3. **Acts** — calls tools, writes files, queries databases, or responds to the user
4. **Loops** — repeats until the task is complete

```
┌──────────────────────────────────────────┐
│                  Agent Loop               │
│                                          │
│  Observation → Reasoning → Action        │
│       ↑                        │         │
│       └────────────────────────┘         │
└──────────────────────────────────────────┘
```

## Why Agents?

Large language models (LLMs) are powerful, but a single prompt-response cycle has limits:

| Limitation | How agents help |
|------------|----------------|
| Fixed context window | Break tasks into steps; store intermediate results |
| No access to live data | Give the agent tools (web search, database queries) |
| Cannot take actions | Tool calling lets agents write code, send emails, etc. |
| Single-shot reasoning | Multi-step loops allow self-correction and planning |

## A Concrete Example

**Task:** "Research the top three open-source vector databases and summarise their performance benchmarks."

A non-agentic LLM can only answer from its training data (which may be outdated). An agent can:

1. Search the web for recent benchmark reports
2. Fetch and parse the relevant pages
3. Synthesise a summary from the retrieved content
4. Return a grounded, up-to-date answer

## Key Properties of Agents

### Autonomy
The agent decides *how* to achieve the goal, not just *what* to say. The user specifies the objective; the agent plans the steps.

### Tool use
Agents extend their capabilities through tools — functions the agent can call to interact with external systems (see [Tools & Function Calling](04-tools-and-function-calling.md)).

### Memory
Agents maintain state across steps. This can be as simple as passing a conversation history, or as sophisticated as a vector-store retrieval system (see [Memory & Context](05-memory-and-context.md)).

### Goal-directed behaviour
Every action the agent takes is in service of a goal. This differs from a chatbot, which just generates the next token in a conversation.

## Types of Agents

| Type | Description | Example |
|------|-------------|---------|
| **ReAct agent** | Alternates Reasoning and Acting steps | General-purpose task agent |
| **Plan-and-execute** | Generates a full plan, then executes each step | Long-horizon research tasks |
| **Tool-calling agent** | Focused on selecting and invoking the right tool | Customer-support automation |
| **Multi-agent system** | Multiple specialised agents collaborate | Software-development pipeline |
| **Autonomous / long-running** | Operates without human checkpoints | Scheduled data-processing jobs |

## Where Agents Are Used Today

- **Coding assistants** — generate, review, and run code autonomously
- **Customer support** — triage tickets, retrieve knowledge, escalate edge cases
- **Data analysis** — write SQL, run queries, plot results, explain findings
- **Research assistants** — search, summarise, and synthesise information
- **DevOps automation** — monitor alerts, diagnose incidents, apply fixes
- **Personal productivity** — manage calendars, draft emails, book travel

## What's Next?

Move on to [Core Concepts](02-core-concepts.md) to understand the building blocks every agent is made of — LLMs, tools, memory, and planning.

---

## Further Reading

- [ReAct: Synergizing Reasoning and Acting in Language Models](https://arxiv.org/abs/2210.03629) — Yao et al., 2022
- [Toolformer: Language Models Can Teach Themselves to Use Tools](https://arxiv.org/abs/2302.04761) — Schick et al., 2023
- [LLM Powered Autonomous Agents](https://lilianweng.github.io/posts/2023-06-23-agent/) — Lilian Weng's blog post
