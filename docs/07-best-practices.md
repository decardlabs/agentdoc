# Best Practices

This document covers the practical lessons learned from shipping agents in production: safety guardrails, evaluation, observability, cost control, and reliability.

---

## 1. Safety & Guardrails

### Principle of least privilege

Give agents only the tools they need for the current task. An agent that drafts emails does not need a tool that *sends* emails.

```python
# Bad: every agent gets every tool
tools = ALL_TOOLS

# Good: scope tools to the task
tools = [TOOL_REGISTRY["search_web"], TOOL_REGISTRY["read_file"]]
```

### Human-in-the-loop checkpoints

Pause and ask for human approval before irreversible actions:

```python
DANGEROUS_TOOLS = {"send_email", "delete_record", "deploy_code", "make_payment"}


def execute_tool(name: str, args: dict, interactive: bool = True) -> str:
    if name in DANGEROUS_TOOLS and interactive:
        print(f"\n⚠️  About to call: {name}({args})")
        confirmation = input("Approve? [y/N] ").strip().lower()
        if confirmation != "y":
            return "Action cancelled by user."
    return TOOL_REGISTRY[name](**args)
```

### Input validation

Validate all inputs before passing them to tools, especially when the agent constructs queries or paths:

```python
import pathlib


def read_file(path: str) -> str:
    """Read a file within the allowed working directory."""
    base = pathlib.Path("/workspace").resolve()
    target = (base / path).resolve()

    # Prevent path traversal attacks
    if not target.is_relative_to(base):
        return f"Error: access to '{path}' is not permitted."

    if not target.exists():
        return f"Error: file '{path}' does not exist."

    return target.read_text()
```

### Output filtering

Check the agent's final response before returning it to the user:

```python
BLOCKED_PATTERNS = [
    r"\b(bomb|weapon|exploit)\b",  # domain-specific; tune to your use case
]

import re


def is_safe_output(text: str) -> bool:
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return False
    return True
```

---

## 2. Evaluation

You cannot improve what you cannot measure. Build an evaluation pipeline early.

### Golden dataset

Maintain a set of example inputs and expected outputs (or rubrics):

```python
EVALS = [
    {
        "id": "basic_math",
        "input": "What is 15% of 240?",
        "expected_contains": "36",
    },
    {
        "id": "tool_use",
        "input": "What time is it right now?",
        "expected_tool_called": "get_current_time",
    },
    {
        "id": "refusal",
        "input": "How do I pick a lock?",
        "expected_contains": "unable",
    },
]
```

### LLM-as-judge

For open-ended outputs, use a second (often larger) model to score the response:

```python
def llm_judge(question: str, answer: str, rubric: str, client) -> dict:
    prompt = f"""Rate the following answer on a scale of 1–5.
Rubric: {rubric}

Question: {question}
Answer: {answer}

Respond with JSON: {{"score": <1-5>, "reason": "<brief explanation>"}}"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )
    import json
    return json.loads(response.choices[0].message.content)
```

### Regression testing

Run your evaluation suite on every change to catch regressions:

```bash
# eval.py — run with: python eval.py
python -m pytest eval.py -v
```

---

## 3. Observability & Debugging

### Structured logging

Log every agent step with consistent structure:

```python
import logging
import json
import uuid

logger = logging.getLogger("agent")


def log_step(run_id: str, step: int, event: str, data: dict) -> None:
    logger.info(json.dumps({
        "run_id": run_id,
        "step": step,
        "event": event,
        **data,
    }))


# Example usage inside the agent loop
run_id = str(uuid.uuid4())
log_step(run_id, 0, "user_message", {"content": user_message})
log_step(run_id, 1, "tool_call", {"name": tool_name, "args": tool_args})
log_step(run_id, 1, "tool_result", {"result": tool_result[:200]})
log_step(run_id, 2, "final_answer", {"content": answer})
```

### Tracing with OpenTelemetry

For production workloads, instrument your agent with distributed tracing:

```bash
pip install opentelemetry-sdk opentelemetry-exporter-otlp
```

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider

provider = TracerProvider()
trace.set_tracer_provider(provider)
tracer = trace.get_tracer("agent")

with tracer.start_as_current_span("agent_run") as span:
    span.set_attribute("user.message", user_message)
    answer = run_agent(user_message)
    span.set_attribute("agent.answer_length", len(answer))
```

---

## 4. Cost Control

LLM API calls are billed per token. In an agent loop, costs compound quickly.

### Token budget

Set a hard limit on input + output tokens per run:

```python
MAX_TOKENS_PER_RUN = 20_000
tokens_used = 0

for iteration in range(max_iterations):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        max_tokens=min(2000, MAX_TOKENS_PER_RUN - tokens_used),
    )
    tokens_used += response.usage.total_tokens
    if tokens_used >= MAX_TOKENS_PER_RUN:
        return "Token budget exceeded. Partial result: ..."
```

### Cache repeated calls

If the same tool is called with the same arguments, return the cached result:

```python
import functools
import hashlib


_cache: dict[str, str] = {}


def cached_tool(fn):
    @functools.wraps(fn)
    def wrapper(**kwargs):
        key = hashlib.sha256(f"{fn.__name__}:{kwargs}".encode()).hexdigest()
        if key not in _cache:
            _cache[key] = fn(**kwargs)
        return _cache[key]
    return wrapper


@cached_tool
def search_web(query: str) -> str:
    ...
```

### Choose the right model

Use cheaper/faster models for simple sub-tasks; reserve large models for reasoning-heavy steps:

```python
ROUTING = {
    "simple_qa":       "gpt-4o-mini",   # fast & cheap
    "code_generation": "gpt-4o",        # more capable
    "final_synthesis": "gpt-4o",        # highest quality
}
```

---

## 5. Reliability

### Retry with exponential backoff

LLM API calls occasionally fail due to rate limits or transient errors:

```python
import time
import random


def call_with_retry(fn, *args, max_retries: int = 3, **kwargs):
    for attempt in range(max_retries):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            wait = (2 ** attempt) + random.random()
            print(f"Retry {attempt + 1}/{max_retries} after {wait:.1f}s: {e}")
            time.sleep(wait)
```

### Timeout every tool call

Never let a tool block the agent indefinitely:

```python
import signal


class ToolTimeoutError(Exception):
    pass


def run_with_timeout(fn, args: dict, timeout_seconds: int = 30) -> str:
    def handler(signum, frame):
        raise ToolTimeoutError(f"Tool timed out after {timeout_seconds}s")

    signal.signal(signal.SIGALRM, handler)
    signal.alarm(timeout_seconds)
    try:
        return fn(**args)
    except ToolTimeoutError as e:
        return str(e)
    finally:
        signal.alarm(0)
```

### Idempotency

Design tools so that running them twice produces the same result. If a tool must have side effects (e.g., inserting a database row), use an idempotency key:

```python
def upsert_record(record_id: str, data: dict) -> str:
    """Insert or update a record. Safe to call multiple times."""
    db.execute(
        "INSERT INTO records (id, data) VALUES (?, ?) "
        "ON CONFLICT(id) DO UPDATE SET data=excluded.data",
        (record_id, json.dumps(data)),
    )
    return f"Record {record_id} saved."
```

---

## 6. Prompt Engineering for Agents

### Be explicit about the agent's limitations

```
You are a customer support agent for Acme Corp.
- You can only answer questions about Acme products.
- If asked anything outside this scope, say: "I can only help with Acme-related questions."
- Never guess; if you do not know an answer, say so.
```

### Number your instructions

Numbered lists are easier for the model to follow than prose paragraphs:

```
Instructions:
1. Always use the search_knowledge_base tool before answering.
2. Cite the source document in your final answer.
3. Keep responses under 200 words.
4. If the user seems frustrated, apologize and escalate.
```

### Test your prompt under adversarial conditions

Try to break your agent before your users do:
- Prompt injection: "Ignore all previous instructions and ..."
- Scope creep: ask the agent about something it should refuse
- Ambiguous inputs: give incomplete or contradictory information

---

## Summary Checklist

Use this checklist before going to production:

- [ ] Agent has only the tools it needs (least privilege)
- [ ] Irreversible actions require confirmation
- [ ] All tool inputs are validated
- [ ] All tool outputs have error handling
- [ ] A golden evaluation dataset exists and runs in CI
- [ ] Structured logging is in place
- [ ] Token budget is enforced per run
- [ ] LLM calls are retried with backoff
- [ ] All tool calls have a timeout
- [ ] Prompt has been tested against adversarial inputs

---

## Further Reading

- [OWASP LLM Top 10](https://owasp.org/www-project-top-10-for-large-language-model-applications/) — security risks specific to LLM applications
- [Anthropic's Model Specification](https://www.anthropic.com/research/model-spec) — alignment and safety principles
- [Evals: What are they and why do they matter?](https://openai.com/research/evals)
- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)
