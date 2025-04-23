import contextlib
import io
import matplotlib
matplotlib.use('Agg')  # For headless environments
import matplotlib.pyplot as plt
import os

def execute_code(code):
    buffer = io.StringIO()
    try:
        with contextlib.redirect_stdout(buffer):
            exec_globals = {}
            exec(code, exec_globals)

            # Auto-save figures if matplotlib is used
            if plt.get_fignums():
                plt.savefig("output.png")
                plt.close()

        return buffer.getvalue()
    except Exception as e:
        return f"[Execution Error] {e}"
