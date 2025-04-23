import subprocess
import pexpect

class PythonDockerREPL:
    def __init__(self, image_name="blazing-python-ds", container_name="python-repl"):
        self.container_name = container_name
        # Start the container if not running
        subprocess.run([
            "docker", "run", "-dit", "--name", container_name, image_name, "python"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Connect to Python REPL inside container
        self.child = pexpect.spawn(f"docker exec -it {container_name} python", encoding="utf-8")
        self.child.expect(">>>")  # Wait for REPL prompt

    def run(self, code):
        self.child.sendline(code)
        self.child.expect(">>>")
        output = self.child.before.strip().split("\r\n", 1)[-1]
        return output

    def close(self):
        self.child.sendline("exit()")
        self.child.close()
        subprocess.run(["docker", "rm", "-f", self.container_name])

if __name__ == "__main__":
    # Example usage
    import textwrap

    repl = PythonDockerREPL()
    print(repl.run("x = 10"))
    print(repl.run("x + 5"))
    repl.close()

    repl = PythonDockerREPL()

    code = textwrap.dedent("""def greet(name):
        print(f"Hi {name}!")
        print(f"Hi {name}!")
    """)

    def1 = repl.run(code)
    run1 = repl.run("greet('Sandeep')")

    repl.close()

    print("-----------------")
    print(def1)
    print('--')
    print(run1)