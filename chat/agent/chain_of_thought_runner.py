from chat.llms import get_llm_client
from chat.executor.chatgpt.code_executor import execute_code
from chat.executor.chatgpt.python_docker_repl import PythonDockerREPL
import re

CHAIN_OF_THOUGHT_PROMPT = '''You are a highly intelligent and autonomous AI programming agent that solves data science tasks step-by-step with precision and clarity.

---

### Goal

Solve the user's task by reasoning transparently and executing Python code one step at a time. Use `pandas`, `matplotlib`, and standard Python libraries. Prioritize clarity, correctness, and safety.

- If text explanation suffices, explain.
- If code is required, use a `python` code block.
- If visualization is needed, save the output to `output.png`.

---

### Capabilities

- Execute Python code in a Jupyter-like environment
- Read and process provided files in /workspace/uploads folder
- Query SQL databases using the `terno` module
- Generate summaries, plots, and insights in a clean, readable format
- Refactor or optimize previous code when needed

---

### SQL Library

Use the `terno` module for database operations:

```python

# List available databases with descriptions
# Returns a dictionary where key is the name of database and value is its description
list_databases() -> dict[str, str]

# List available tables with descriptions
# returns a dictionary where key is the name of table and value is its description
list_tables(database_name: str) -> dict[str, str]

# Run SQL and return result as a pandas DataFrame
execute_sql(database_name: str, sql: str) -> pd.DataFrame
```
---

### Constraints

- No randomness unless explicitly instructed
- No external internet access
- Output must be human-readable
- Avoid speculation—derive only what the data supports

---

### Reasoning Loop

You will work in the following loop:

1. Thought: Describe the next step.
2. Code: Provide Python code in a `python` block.
3. Verify: Check and interpret the output.
4. Repeat: Continue until the task is complete.
5. Terminate: Clearly indicate when the task is done.

Always respond using markdown blocks:

- Thought: Your reasoning
- Code: ```python (Your code) ```
- Terminate: State that the task is complete

---

### Begin

Your current task is: {task}

Start by stating your understanding of the task and outlining your plan of action.
'''

dbs = {
    'cxl': 'E-learning data (users, payments, course progress',
    'google_ads': 'Google Ads campaign data',
    'google_analytics': 'Website behavior data'
    }

def extract_block(label, text):
    # First try matching ```python ... ```
    match = re.search(rf"```{label.lower()}[\r\n]+(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    # Fallback: match any generic triple-backtick block
    fallback = re.search(r"```[\r\n]*(.*?)```", text, re.DOTALL)
    if fallback:
        return fallback.group(1).strip()
    return None

# def extract_block(label, text):
#     match = re.search(rf"```{label.lower()}\\n(.*?)```", text, re.DOTALL | re.IGNORECASE)
#     return match.group(1).strip() if match else None

def run_chain_of_thought_loop(question, chat_history=None, repl=None):
    llm = get_llm_client("openai")
    content = CHAIN_OF_THOUGHT_PROMPT.replace('{task}', question).replace('{dbs}', str(dbs))

    if chat_history is None:
        chat_history = [{"role": "user", "content": content}]
    else:
        chat_history.append({"role": "user", "content": question})

    if repl is None:
        repl = PythonDockerREPL()

    while True:
        response = ""

        def capture_stream(chunk):
            nonlocal response
            response += chunk

        llm.chat(chat_history, stream_callback=capture_stream)
        chat_history.append({"role": "assistant", "content": response})

        if "Terminate" in response:
            yield "\n[Terminated by LLM]\n"
            break

        code = extract_block("python", response)
        if code:
            print("===== Code To Execute =====")
            print(code)
            print("===== / Code Executed =====")
            output = repl.run(code)
            print("===== Output =====")
            print(output)
            print("===== /Output =====")
            yield f"\n>>> Python Output:\n{output}\n"
            chat_history.append({"role": "user", "content": f"Output:\n{output}"})
        else:
            yield "\n[No code found. Ending.]\n"
            break

    yield "__STATE__", chat_history, repl
