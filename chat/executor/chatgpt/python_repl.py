import subprocess
import pexpect
import uuid

class PythonDockerREPL:
    def __init__(self, image_name="blazing-python-ds", container_name=None):
        self.container_name = container_name or f"pyrepl-{uuid.uuid4().hex[:6]}"
        # Start the container if not running
        subprocess.run([
            "docker", "run", "-dit", "--name", self.container_name, image_name, "python"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Connect to Python REPL inside container
        self.child = pexpect.spawn(f"docker exec -it {self.container_name} python", encoding="utf-8")
        self.child.expect(">>>")  # Wait for REPL prompt

    def run(self, code):
        self.child.sendline("")  # Clear partial input
        self.child.expect(">>>")

        output = ""
        for line in code.strip().split('\n'):
            self.child.sendline(line)
            idx = self.child.expect([">>>", "..."], timeout=5)
            while idx == 1:  # More input expected
                output += self.child.before.strip() + "\n"
                idx = self.child.expect([">>>", "..."], timeout=5)
            output += self.child.before.strip() + "\n"

        return output.strip()

    def close(self):
        self.child.sendline("exit()")
        self.child.expect(pexpect.EOF)
        self.child.close()
        subprocess.run(["docker", "rm", "-f", self.container_name])

# Example usage
repl = PythonDockerREPL()
print(repl.run("x = 10"))
print(repl.run("x + 5"))
print(repl.run("""
def greet(name):
    return f"Hello, {name}!"

greet("Sandeep")
"""))
repl.close()
