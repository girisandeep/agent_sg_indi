import pexpect, uuid
from pathlib import Path

class PythonDockerREPL:
    """
    Persistent Python interpreter running inside a Docker container.

    Example
    -------
    >>> repl = PythonDockerREPL()          # starts the container + interpreter
    >>> repl.run("x = 10")                 # define a variable (no output)
    ''
    >>> repl.run("x * 7")                  # expression -> captured result
    '70'
    >>> repl.close()                       # tear everything down
    """

    def __init__(self,
                 image: str = "blazing-python-ds",
                 prompt: str = "PYREPL> ",
                 timeout: int = 5):
        """
        Start an interactive Python process inside a fresh container.

        Parameters
        ----------
        image   : Docker image that already has Python installed.
        prompt  : Internal prompt used to know when the interpreter is idle.
        timeout : Seconds to wait for Docker / Python to respond.
        """
        self.prompt = prompt
        # -q suppresses the banner; --rm auto-removes the container on exit.
        docker_cmd = f"docker run --rm -it {image} python -q"

        # Spawn the process; echo=False stops pexpect from duplicating our input.
        self.child = pexpect.spawn(docker_cmd,
                                   encoding="utf-8",
                                   echo=False,
                                   timeout=timeout)

        # Replace the interpreter’s default prompts with our unique token.
        self.child.sendline(
            f"import sys; sys.ps1='{prompt}'; sys.ps2='{prompt}'")
        self.child.expect_exact(prompt)      # wait until the prompt is ready
        res = self.run('pass')

    def run(self, code: str) -> str | None:
        """
        Execute *code* inside the running interpreter and return stdout/expr repr.

        Behaviour
        ---------
        * Any print/traceback text is captured.
        * If the last line is an expression, its repr is returned too.
        * A stray empty return ('') simply means nothing was printed/evaluated.
        """
        sentinel = str(uuid.uuid4())         # unique marker so we know where output ends
        wrapped = f"{code}\nprint('{sentinel}')"
        self.child.sendline(wrapped)

        # Read until we see the sentinel we just printed.
        self.child.expect_exact(sentinel)

        # .before holds everything emitted *before* the sentinel.
        output = self.child.before.strip()

        # Clear through to the next prompt so the session is ready.
        self.child.expect_exact(self.prompt)

        # Remove any echoed version of the original code (first line only).
        if output.startswith(code.splitlines()[0]):
            output = output[len(code.splitlines()[0]):].lstrip()

        if len(output) >= 15:
            output = output[:-15]
        return output if output else None

    def close(self):
        """Terminate the interpreter and the container."""
        self.child.sendline("exit()")
        self.child.close(force=True)

if __name__ == '__main__':
    repl = PythonDockerREPL()
    repl.run("import math")
    print(repl.run("math.sqrt(2)"))   # -> '1.4142135623730951'
    repl.close()
