import os
import re
import shlex
import signal
import textwrap
import uuid
import pexpect


class PythonDockerREPL:
    """
    Persistently run Python code inside a Docker container based on
    the image ``blazing-python-ds`` (or any other you pass in) and
    capture just the output you care about.
    """

    PROMPT_RE = re.compile(r"^(>>> |\.\.\. )")

    def __init__(self, image: str = "blazing-python-ds"):
        self.image = image
        self.container_name = f"pyrepl_{uuid.uuid4().hex[:8]}"
        cmd = (
            f"docker run --name {self.container_name} -it --rm "
            f"{shlex.quote(self.image)} python -u -q"
        )
        self.child = pexpect.spawn(cmd, encoding="utf-8", echo=False)
        self.child.expect(">>> ")

    # ---------- helpers ----------

    def _send(self, code: str) -> tuple[str, str]:
        code = textwrap.dedent(code.rstrip()) + "\n"
        sentinel = f"__END_{uuid.uuid4().hex}__"
        sentinel_cmd = f"print({sentinel!r})"
        self.child.send(code)
        self.child.sendline(sentinel_cmd)
        return sentinel, sentinel_cmd

    def _read_until(self, sentinel: str) -> str:
        self.child.expect(re.escape(sentinel))
        raw = self.child.before
        self.child.expect(">>> ")
        return raw

    @staticmethod
    def _strip_prompts(lines):
        """Remove the '>>> ' or '... ' prompt prefixes if present."""
        return [PythonDockerREPL.PROMPT_RE.sub("", ln) for ln in lines]

    def _clean_output(self, raw: str, code: str, sentinel_cmd: str) -> str:
        echoes = set(textwrap.dedent(code).splitlines())
        lines = raw.splitlines()

        # 1. drop interactive prompts
        lines = self._strip_prompts(lines)

        cleaned = []
        for ln in lines:
            if ln in echoes:                 # original code echo
                continue
            if ln == sentinel_cmd:           # sentinel echo
                continue
            if not ln.strip():               # blank
                continue
            cleaned.append(ln)

        return "\n".join(cleaned).strip()

    # ---------- public API ----------

    def run(self, code: str) -> str:
        sentinel, sentinel_cmd = self._send(code)
        raw = self._read_until(sentinel)
        return self._clean_output(raw, code, sentinel_cmd)

    def close(self):
        if self.child.isalive():
            try:
                self.child.sendline("exit()")
                self.child.expect(pexpect.EOF, timeout=2)
            except pexpect.ExceptionPexpect:
                pass
        os.system(f"docker rm -f {self.container_name} >/dev/null 2>&1")

    def __del__(self):
        self.close()
