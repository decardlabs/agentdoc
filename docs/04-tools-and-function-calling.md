# Tools & Function Calling

Tools are how agents act on the world. This document covers everything from writing your first tool to advanced patterns like parallel execution, chaining, and error recovery.

## What Is Function Calling?

**Function calling** (also called *tool use*) is a feature of modern LLM APIs that allows the model to request the execution of a function by name and arguments, rather than just returning text.

The flow is always:

```
1. Developer registers tools (JSON Schema) with the model.
2. Model decides to call a tool → returns a structured tool_call object.
3. Developer's code executes the actual function.
4. Result is sent back to the model as a tool message.
5. Model continues reasoning with the new information.
```

The model never directly executes code — it only *requests* execution. Your application remains in control.

---

## Anatomy of a Tool Definition

```python
{
    "type": "function",
    "function": {
        "name": "search_web",                     # Identifier used in the tool_call
        "description": "Search the web and return the top 5 results for a query.",
                                                  # Crucial: tells the model WHEN to use this tool
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query string."
                },
                "num_results": {
                    "type": "integer",
                    "description": "Number of results to return (default 5, max 10).",
                    "default": 5
                }
            },
            "required": ["query"]                 # Only required params go here
        }
    }
}
```

### Writing good descriptions

The description is the most important field. The model uses it to decide *whether* to call the tool and *how* to format the arguments.

| ❌ Weak description | ✅ Strong description |
|--------------------|-----------------------|
| "Get data" | "Fetch the closing stock price for a given ticker symbol on a specific date." |
| "Run code" | "Execute a Python snippet and return stdout. Use for calculations, data processing, or testing logic." |
| "Database tool" | "Query the internal customer database. Returns JSON. Use only for questions about customers, orders, or products." |

---

## Implementing Tools in Python

A tool is any Python callable. Keep tools:

- **Focused** — one responsibility each
- **Idempotent** where possible — safe to retry on failure
- **Well-typed** — use type annotations; they improve schema generation
- **Return strings** (or JSON-serialisable dicts) — the model receives text

```python
import httpx


def search_web(query: str, num_results: int = 5) -> str:
    """Search the web using a public API and return formatted results."""
    response = httpx.get(
        "https://api.search.example.com/search",
        params={"q": query, "n": num_results},
        timeout=10,
    )
    response.raise_for_status()
    data = response.json()
    results = [f"{r['title']}: {r['url']}" for r in data["results"]]
    return "\n".join(results)
```

---

## Tool Choice Modes

Most APIs let you control how aggressively the model calls tools:

| Mode | Behaviour | When to use |
|------|-----------|-------------|
| `auto` | Model decides whether to call a tool | Default; good for most cases |
| `required` | Model must call a tool (any tool) | When you always want structured output |
| `{"type": "function", "function": {"name": "..."}}` | Model must call a specific tool | Structured data extraction |
| `none` | Model cannot call tools | When you want a plain text response |

```python
# Force the model to always extract structured data
response = client.chat.completions.create(
    model="gpt-4o",
    messages=messages,
    tools=TOOL_SCHEMAS,
    tool_choice={"type": "function", "function": {"name": "extract_entity"}},
)
```

---

## Parallel Tool Calls

The model may request multiple tool calls in a single response. Modern LLMs support this natively — always handle it as a list:

```python
message = response.choices[0].message

if message.tool_calls:
    # Execute all tool calls (potentially in parallel)
    import concurrent.futures

    def execute_one(tool_call):
        name = tool_call.function.name
        args = json.loads(tool_call.function.arguments)
        result = TOOLS[name](**args)
        return {
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": result,
        }

    with concurrent.futures.ThreadPoolExecutor() as executor:
        tool_results = list(executor.map(execute_one, message.tool_calls))

    messages.append(message)
    messages.extend(tool_results)
```

> **Note:** Only parallelise tools that are safe to run concurrently. Tools with side effects (writing to a database, sending emails) may need sequential execution.

---

## Chaining Tools

Some tasks require the output of one tool to feed into another:

```
User: "Summarise the README of the most-starred Python project on GitHub."

Step 1: search_github(query="language:python sort:stars", limit=1)
         → {"name": "public-apis", "url": "https://github.com/..."}

Step 2: fetch_url(url="https://raw.githubusercontent.com/.../README.md")
         → "# Public APIs\nA collective list of free APIs..."

Step 3: summarise(text="...") [or just let the model do this in plain text]
         → "Public APIs is a collaborative list of free APIs..."
```

The agent loop handles this automatically: each tool result is fed back into the conversation, and the model decides what to do next.

---

## Error Recovery

Tools fail. Design your tools to return descriptive error strings rather than raising exceptions that crash the agent:

```python
def fetch_url(url: str) -> str:
    """Fetch the text content of a URL."""
    try:
        response = httpx.get(url, timeout=15, follow_redirects=True)
        response.raise_for_status()
        return response.text[:8000]  # Truncate to avoid flooding the context
    except httpx.TimeoutException:
        return f"Error: request to {url} timed out after 15 seconds."
    except httpx.HTTPStatusError as e:
        return f"Error: {url} returned HTTP {e.response.status_code}."
    except Exception as e:
        return f"Error: {type(e).__name__}: {e}"
```

Add a retry instruction to your system prompt:

```
If a tool returns an error, try at most one alternative approach.
If that also fails, tell the user what went wrong.
```

---

## Dangerous Tools: Require Confirmation

Some tools are irreversible — deleting records, sending emails, making payments. Apply a **human-in-the-loop** checkpoint before executing them:

```python
REQUIRES_CONFIRMATION = {"send_email", "delete_record", "make_payment"}


def execute_tool(tool_call, auto_confirm: bool = False):
    name = tool_call.function.name
    args = json.loads(tool_call.function.arguments)

    if name in REQUIRES_CONFIRMATION and not auto_confirm:
        print(f"\n⚠️  Agent wants to call: {name}({args})")
        if input("Allow? [y/N] ").strip().lower() != "y":
            return "Tool call cancelled by user."

    return TOOLS[name](**args)
```

---

## Tool Schemas from Type Annotations

Maintaining tool schemas by hand is tedious. Libraries like [Pydantic](https://docs.pydantic.dev/) can generate them automatically:

```python
from pydantic import BaseModel, Field
import json


class SearchArgs(BaseModel):
    query: str = Field(description="Search query string")
    num_results: int = Field(default=5, description="Number of results (max 10)")


def make_tool_schema(name: str, description: str, model: type[BaseModel]) -> dict:
    schema = model.model_json_schema()
    # Remove JSON Schema keys the API doesn't expect
    schema.pop("title", None)
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": schema,
        },
    }


search_schema = make_tool_schema(
    "search_web",
    "Search the web and return the top results.",
    SearchArgs,
)
```

---

## Summary

| Topic | Key takeaway |
|-------|--------------|
| Tool definition | Name + description + JSON Schema; description is the most important field |
| Tool choice | Use `auto` by default; force a specific tool for structured extraction |
| Parallel calls | Always handle `tool_calls` as a list; parallelise where safe |
| Error handling | Return error strings; never crash the agent on a tool failure |
| Dangerous tools | Gate irreversible actions behind human confirmation |
| Schema generation | Use Pydantic or similar to avoid hand-writing JSON Schema |

---

## Further Reading

- [OpenAI Function Calling Docs](https://platform.openai.com/docs/guides/function-calling)
- [Anthropic Tool Use Guide](https://docs.anthropic.com/en/docs/tool-use)
- [Pydantic Documentation](https://docs.pydantic.dev/)
