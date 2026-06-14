# Building Your First Agent

This document walks you through building a minimal but real AI agent in Python. By the end you will have a working agent that can answer questions, call tools, and handle multi-step tasks.

## Prerequisites

- Python 3.10+
- An OpenAI API key (or any OpenAI-compatible endpoint, e.g. a local Ollama instance)

```bash
pip install openai
```

Set your API key:

```bash
export OPENAI_API_KEY="sk-..."
```

---

## Step 1 — A Simple LLM Call

Before adding any agent logic, confirm that you can call the model:

```python
# agent_hello.py
from openai import OpenAI

client = OpenAI()

response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "user", "content": "What is 2 + 2?"},
    ],
)

print(response.choices[0].message.content)
# → "4"
```

Run it:

```bash
python agent_hello.py
```

---

## Step 2 — Add a Tool

Tools are plain Python functions. We expose them to the model as JSON Schema descriptions.

```python
# tools.py
import json
import datetime


def get_current_time() -> str:
    """Return the current UTC time as an ISO 8601 string."""
    return datetime.datetime.utcnow().isoformat() + "Z"


def calculator(expression: str) -> str:
    """
    Safely evaluate a simple arithmetic expression and return the result.
    Only supports +, -, *, /, **, parentheses, and numbers.
    """
    import ast
    import operator

    _OPS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
    }

    def _eval(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
            return _OPS[type(node.op)](_eval(node.left), _eval(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
            return _OPS[type(node.op)](_eval(node.operand))
        raise ValueError(f"Unsupported expression: {ast.dump(node)}")

    try:
        tree = ast.parse(expression, mode="eval")
        result = _eval(tree.body)
        return str(result)
    except Exception as e:
        return f"Error: {e}"


# Registry maps tool name → callable
TOOLS = {
    "get_current_time": get_current_time,
    "calculator": calculator,
}

# JSON Schema descriptions sent to the model
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "Return the current UTC time.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "Evaluate a simple arithmetic expression, e.g. '(3 + 4) * 2'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Arithmetic expression to evaluate.",
                    }
                },
                "required": ["expression"],
            },
        },
    },
]
```

---

## Step 3 — The Agent Loop

Now wire the loop together:

```python
# agent.py
import json
from openai import OpenAI
from tools import TOOLS, TOOL_SCHEMAS

client = OpenAI()

SYSTEM_PROMPT = """You are a helpful assistant with access to tools.
Think step by step. Use tools whenever they would give a more accurate answer.
When you have a final answer, respond directly to the user."""


def run_agent(user_message: str) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]

    max_iterations = 10

    for iteration in range(max_iterations):
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=TOOL_SCHEMAS,
            tool_choice="auto",
        )

        message = response.choices[0].message

        # Append the assistant's message (may contain tool_calls)
        messages.append(message)

        # If no tool calls, the model has produced its final answer
        if not message.tool_calls:
            return message.content

        # Execute each tool call and feed results back
        for tool_call in message.tool_calls:
            name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)

            print(f"  [tool call] {name}({args})")

            fn = TOOLS.get(name)
            if fn is None:
                result = f"Error: unknown tool '{name}'"
            else:
                result = fn(**args)

            print(f"  [tool result] {result}")

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result,
            })

    return "Agent reached maximum iterations without a final answer."


if __name__ == "__main__":
    questions = [
        "What time is it right now?",
        "What is (137 * 42) + 99?",
        "If a rectangle is 15 m wide and 8 m tall, what is its area?",
    ]
    for q in questions:
        print(f"\nQ: {q}")
        answer = run_agent(q)
        print(f"A: {answer}")
```

Run it:

```bash
python agent.py
```

Expected output (times will differ):

```
Q: What time is it right now?
  [tool call] get_current_time({})
  [tool result] 2026-06-14T10:23:45Z
A: The current UTC time is 10:23:45 on 14 June 2026.

Q: What is (137 * 42) + 99?
  [tool call] calculator({'expression': '(137 * 42) + 99'})
  [tool result] 5853
A: (137 × 42) + 99 = 5,853.

Q: If a rectangle is 15 m wide and 8 m tall, what is its area?
  [tool call] calculator({'expression': '15 * 8'})
  [tool result] 120
A: The area of the rectangle is 120 m².
```

---

## Step 4 — Add a System Prompt and Persona

The system prompt is where you define *who* the agent is and what it can do. A good system prompt:

1. Describes the agent's role clearly
2. Lists what tools are available (the model already sees them via the schema, but a brief mention helps)
3. Sets guardrails ("only answer questions related to X")
4. Specifies the desired output format

```python
SYSTEM_PROMPT = """You are a financial data assistant.
You help analysts look up market data and perform calculations.

Available tools:
- calculator: arithmetic on numbers
- get_current_time: current UTC timestamp

Rules:
- Always show your working before giving a final number.
- If a question is outside your scope, politely say so.
- Respond in plain text; do not use Markdown."""
```

---

## Step 5 — Handle Errors Gracefully

Real tools fail. Wrap every tool call:

```python
try:
    result = fn(**args)
except Exception as e:
    result = f"Tool error: {type(e).__name__}: {e}"
```

You can also give the agent a *retry* instruction in the system prompt:

```
If a tool returns an error, try a different approach or ask the user for clarification.
```

---

## What You Built

| Component | Where it lives |
|-----------|---------------|
| Tool definitions (schema) | `TOOL_SCHEMAS` list |
| Tool implementations | `TOOLS` dict of callables |
| Agent loop | `run_agent()` function |
| Persona / constraints | `SYSTEM_PROMPT` constant |

---

## Next Steps

- [Tools & Function Calling](04-tools-and-function-calling.md) — more advanced tool patterns (parallel calls, chained tools, error recovery)
- [Memory & Context](05-memory-and-context.md) — persist state between agent runs
- [Best Practices](07-best-practices.md) — production-readiness, logging, and safety

---

## Further Reading

- [OpenAI Function Calling Guide](https://platform.openai.com/docs/guides/function-calling)
- [LangChain Agents Quickstart](https://python.langchain.com/docs/how_to/agent_executor/)
- [smolagents by Hugging Face](https://github.com/huggingface/smolagents)
