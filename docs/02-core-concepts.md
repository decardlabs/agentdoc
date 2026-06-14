# Core Concepts

Every AI agent is assembled from a small set of building blocks. Understanding these blocks deeply will make every other concept in this guide click into place.

## 1. The Language Model (LLM)

The LLM is the reasoning engine at the heart of an agent. It takes text (the **prompt**) and produces text (the **completion**). Modern chat-optimised LLMs are trained to follow instructions, engage in multi-turn dialogue, and — crucially — decide when and how to call tools.

### Roles in a prompt

Most LLM APIs structure prompts as a list of *messages*, each with a *role*:

| Role | Purpose |
|------|---------|
| `system` | Sets the agent's persona, constraints, and available tools |
| `user` | The human's input or the environment's observation |
| `assistant` | The model's previous responses (conversation history) |
| `tool` / `function` | The result of a tool call (returned to the model) |

### Temperature and sampling

- **Temperature = 0** — deterministic, best for tasks that require precision (code, SQL)
- **Temperature > 0** — more creative variance, better for brainstorming

For agents, a low temperature (0–0.2) is usually preferred because you want consistent, predictable reasoning.

---

## 2. Tools

Tools are functions the agent can invoke to interact with the world. Without tools, the agent can only produce text. With tools, it can browse the web, run code, read databases, send messages, and more.

A tool has three parts:

```python
{
    "name": "get_weather",
    "description": "Return current weather for a given city.",
    "parameters": {
        "city": {"type": "string", "description": "City name, e.g. 'Tokyo'"}
    }
}
```

1. **Name** — the identifier the model uses to invoke the tool
2. **Description** — plain-English explanation so the model knows *when* to use it
3. **Parameters** — the inputs the tool expects (JSON Schema)

The agent workflow with a tool call looks like this:

```
User: "What is the weather in Paris?"

Agent thinks → calls get_weather(city="Paris")
Tool returns → {"temp": "18°C", "condition": "Partly cloudy"}
Agent thinks → "The weather in Paris is 18 °C and partly cloudy."
```

See [Tools & Function Calling](04-tools-and-function-calling.md) for a full walkthrough.

---

## 3. Memory

Memory is how the agent keeps track of what has happened and what it knows.

### 3a. In-context memory (short-term)

The simplest form of memory: everything lives inside the current prompt. Every message, observation, and tool result is appended to the running conversation history and sent to the LLM on each step.

**Pros:** Simple. No external infrastructure.  
**Cons:** Limited by the model's context window; costs tokens on every call.

### 3b. External memory (long-term)

Information stored *outside* the model and retrieved when needed:

| Storage type | When to use | Example |
|-------------|-------------|---------|
| Key-value store | Fast lookup by exact key | Redis, DynamoDB |
| Relational DB | Structured queries | PostgreSQL |
| Vector store | Semantic / similarity search | Pinecone, Chroma, pgvector |
| File system | Large blobs, documents | S3, local disk |

### 3c. Retrieval-Augmented Generation (RAG)

RAG is the most common pattern for giving an agent access to a large knowledge base:

1. Chunk documents into small passages
2. Embed each chunk with an embedding model
3. At query time, embed the question and retrieve the top-k closest chunks
4. Inject the retrieved text into the prompt alongside the question

See [Memory & Context](05-memory-and-context.md) for implementation details.

---

## 4. Planning

Planning is how the agent breaks a complex goal into manageable steps.

### 4a. Chain-of-Thought (CoT)

Prompting the model to "think step by step" before giving a final answer. Improves accuracy on multi-step reasoning tasks with zero additional code.

```
Think step by step.

Problem: If a train travels 300 km in 2.5 hours, what is its average speed?

Step 1: ...
Step 2: ...
Answer: ...
```

### 4b. ReAct (Reason + Act)

Introduced in [Yao et al. (2022)](https://arxiv.org/abs/2210.03629). The model alternates between:

- **Thought** — internal reasoning about the current situation
- **Action** — a tool call or a final response
- **Observation** — the tool's return value

```
Thought: I need to look up the current exchange rate.
Action: search_web(query="USD to EUR exchange rate today")
Observation: 1 USD = 0.92 EUR (as of June 2026)
Thought: I now have the rate. I can answer.
Action: respond("1 USD is approximately 0.92 EUR today.")
```

### 4c. Plan-and-Execute

The agent first generates a complete plan (a numbered list of sub-tasks), then executes each sub-task in order. Useful for long-horizon tasks where you want a human-reviewable plan before execution begins.

### 4d. Reflection and Self-Critique

After completing a step, the agent evaluates its own output:
- "Is this answer correct?"
- "Did I miss anything?"
- "Should I try a different approach?"

This loop allows the agent to catch and fix its own mistakes before returning a final answer.

---

## 5. The Agent Loop

Putting it all together, the canonical agent loop looks like this:

```python
messages = [system_prompt, user_message]

while True:
    response = llm.chat(messages)

    if response.is_final_answer:
        return response.content

    # The model wants to call a tool
    tool_call = response.tool_call
    result = execute_tool(tool_call.name, tool_call.arguments)

    # Feed the result back into the conversation
    messages.append({"role": "assistant", "content": response})
    messages.append({"role": "tool", "content": result})
```

Key design decisions in this loop:

| Decision | Options |
|----------|---------|
| When to stop | Max iterations, confidence threshold, explicit "done" signal |
| Error handling | Retry, fallback tool, ask the user |
| Parallelism | Run independent tool calls concurrently |
| Human-in-the-loop | Pause and ask for approval at checkpoints |

---

## Summary

| Concept | One-line definition |
|---------|---------------------|
| LLM | The reasoning engine; takes text, produces text |
| Tool | A function the agent can call to act on the world |
| Memory | State the agent maintains within and across tasks |
| Planning | How the agent breaks goals into steps |
| Agent loop | The repeated observe → reason → act cycle |

---

## Further Reading

- [Chain-of-Thought Prompting Elicits Reasoning in Large Language Models](https://arxiv.org/abs/2201.11903) — Wei et al., 2022
- [ReAct: Synergizing Reasoning and Acting in Language Models](https://arxiv.org/abs/2210.03629) — Yao et al., 2022
- [Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks](https://arxiv.org/abs/2005.11401) — Lewis et al., 2020
