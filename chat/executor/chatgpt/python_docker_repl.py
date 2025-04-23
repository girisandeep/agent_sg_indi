import pexpect
import json
import ast

class PythonDockerREPL:
    def __init__(self, image_name="blazing-python-ds", timeout=10):
        """
        Initialize a Docker-based Python REPL inside a container.

        :param image_name: Name of the Docker image containing Python.
        :param timeout: Default timeout for REPL responses (in seconds).
        """
        cmd = f"docker run -i --rm {image_name} python3 -i"
        # Spawn the Docker Python REPL
        self.child = pexpect.spawn(cmd, encoding='utf-8', timeout=timeout)
        # Disable input echo so we only capture actual output
        self.child.setecho(False)
        # Wait for the initial Python prompt
        self.child.expect_exact('>>> ')

    def run(self, code: str):
        """
        Execute multiline Python code in the Docker REPL and return the last expression's result.

        :param code: Multiline Python code to execute.
        :return: Evaluated result of the last expression, or None if none.
        """
        # Parse code to separate trailing expression if present
        parsed = ast.parse(code)
        lines = code.splitlines()
        last_expr = None

        if parsed.body and isinstance(parsed.body[-1], ast.Expr):
            node = parsed.body[-1]
            start = node.lineno - 1
            end = getattr(node, 'end_lineno', node.lineno)
            expr_lines = lines[start:end]
            body_lines = lines[:start]
            body_text = "\n".join(body_lines)
            last_expr = "\n".join(expr_lines)
        else:
            body_text = code

        # Build commands: exec body, eval expr, then print sentinel
        commands = []
        if body_text.strip():
            commands.append(f"exec({json.dumps(body_text)})")
        if last_expr:
            commands.append(f"_repl_result = eval({json.dumps(last_expr)})")
        else:
            commands.append("_repl_result = None")
        commands.append("print('__REPL_END__:', repr(_repl_result))")

        # Send each command line into the REPL
        for cmd in commands:
            self.child.sendline(cmd)

        # Wait for our sentinel and capture the result repr
        self.child.expect(r"__REPL_END__:\s*(.*)\r?\n")
        result_repr = self.child.match.group(1).strip()
        # Wait for next prompt
        self.child.expect_exact('>>> ')

        # Convert repr back to Python object
        if result_repr == 'None':
            return None
        try:
            return ast.literal_eval(result_repr)
        except Exception:
            return result_repr

    def close(self):
        """
        Close the REPL and stop the Docker container.
        """
        self.child.sendline('exit()')
        self.child.expect(pexpect.EOF)
        self.child.close()