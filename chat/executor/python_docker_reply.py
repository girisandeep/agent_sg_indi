import docker
import jupyter_client
import time
import os
import json
import tempfile
import shutil
import atexit
import uuid
import signal
import sys
from queue import Empty

# --- Dockerfile Content ---
DOCKERFILE_CONTENT = """
FROM python:3.11-slim
WORKDIR /kernel
# Install ipykernel which is needed to run the kernel
RUN pip install ipykernel
# The command will be provided by the Python script starting the container
CMD []
"""
IMAGE_NAME = "ipykernel-runner:latest"

class PythonRepl:
    """
    Manages a persistent IPython kernel inside a Docker container
    for interactive code execution.
    """
    def __init__(self, image_name=IMAGE_NAME, timeout=60, debug=False):
        """
        Initializes the REPL environment by building the Docker image
        (if necessary) and starting the kernel container.

        Args:
            image_name (str): Name for the Docker image.
            timeout (int): Max seconds to wait for kernel connection file.
            debug (bool): If True, prints debug information.
        """
        self.image_name = image_name
        self.timeout = timeout
        self.debug = debug
        self._log("Initializing PythonRepl...")

        self.docker_client = None
        self.container = None
        self.kernel_client = None
        self.temp_dir = tempfile.mkdtemp(prefix="repl_kernel_") # Temp dir for connection file
        self.connection_file_host = os.path.join(self.temp_dir, "kernel_connection.json")
        self.connection_file_container = "/kernel/kernel_connection.json" # Path inside container

        try:
            self.docker_client = docker.from_env()
            self._log("Docker client initialized.")
            self._build_image_if_needed()
            self._start_kernel_container()
            self._connect_to_kernel()
            # Register cleanup function to be called on script exit
            atexit.register(self.close)
            # Handle signals for graceful shutdown
            signal.signal(signal.SIGTERM, self._signal_handler)
            signal.signal(signal.SIGINT, self._signal_handler)
            self._log("PythonRepl initialized successfully.")

        except Exception as e:
            self._log(f"Initialization failed: {e}", error=True)
            self.close() # Attempt cleanup even on init failure
            raise # Re-raise the exception

    def _log(self, message, error=False):
        if self.debug or error:
            prefix = "DEBUG:" if not error else "ERROR:"
            print(f"{prefix} [PythonRepl] {message}", file=sys.stderr if error else sys.stdout)

    def _signal_handler(self, signum, frame):
        self._log(f"Received signal {signum}, shutting down...", error=True)
        self.close()
        sys.exit(1)

    def _build_image_if_needed(self):
        """Builds the Docker image if it doesn't exist."""
        try:
            self.docker_client.images.get(self.image_name)
            self._log(f"Docker image '{self.image_name}' found.")
        except docker.errors.ImageNotFound:
            self._log(f"Docker image '{self.image_name}' not found. Building...")
            try:
                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='_Dockerfile') as temp_dockerfile:
                    temp_dockerfile.write(DOCKERFILE_CONTENT)
                    dockerfile_path = temp_dockerfile.name
                
                # Use low-level API for more control over build output streaming
                api_client = docker.APIClient(base_url='unix://var/run/docker.sock') # Or appropriate base_url
                build_logs = api_client.build(
                    path='.', # Context path doesn't matter much here as we specify Dockerfile content
                    dockerfile=dockerfile_path, # Provide path to temporary Dockerfile
                    tag=self.image_name,
                    rm=True, # Remove intermediate containers
                    decode=True # Decode JSON stream
                )
                
                for line in build_logs:
                    if 'stream' in line:
                        self._log(f"Build: {line['stream'].strip()}")
                    elif 'error' in line:
                         self._log(f"Build Error: {line['error'].strip()}", error=True)
                         raise docker.errors.BuildError(line['error'], build_logs)
                    elif 'status' in line:
                         self._log(f"Build Status: {line['status']}")

                os.unlink(dockerfile_path) # Clean up temporary Dockerfile
                self._log(f"Docker image '{self.image_name}' built successfully.")

            except docker.errors.BuildError as e:
                self._log(f"Docker build failed: {e}", error=True)
                if os.path.exists(dockerfile_path):
                    os.unlink(dockerfile_path)
                raise
            except Exception as e:
                 self._log(f"An unexpected error occurred during build: {e}", error=True)
                 if 'dockerfile_path' in locals() and os.path.exists(dockerfile_path):
                    os.unlink(dockerfile_path)
                 raise


    def _start_kernel_container(self):
        """Starts the Docker container running the ipykernel."""
        self._log("Starting kernel container...")
        container_name = f"repl_kernel_container_{uuid.uuid4().hex[:8]}"

        # === MODIFICATION: Remove --ip argument ===
        command = [
            "python", "-m", "ipykernel_launcher",
            f"--f={self.connection_file_container}"
            # Removed "--ip='0.0.0.0'"
        ]
        # =========================================

        try:
            self.container = self.docker_client.containers.run(
                self.image_name,
                command=command,
                volumes={self.temp_dir: {'bind': '/kernel', 'mode': 'rw'}},
                detach=True,
                auto_remove=True,
                name=container_name,
            )
            self._log(f"Container '{self.container.name}' started (ID: {self.container.id}).")
            self._log(f"Mounted host directory '{self.temp_dir}' to '/kernel' in container.")
        except docker.errors.APIError as e:
            self._log(f"Failed to start container: {e}", error=True)
            raise

    def _wait_for_connection_file(self):
        """Waits for the kernel connection file to appear on the host."""
        self._log(f"Waiting for connection file '{self.connection_file_host}'...")
        start_time = time.time()
        while not os.path.exists(self.connection_file_host):
            if time.time() - start_time > self.timeout:
                raise TimeoutError(f"Kernel connection file did not appear within {self.timeout} seconds.")
            if self.container:
                try:
                    self.container.reload() # Check container status
                    if self.container.status == 'exited':
                        logs = self.container.logs().decode('utf-8', errors='ignore')
                        raise RuntimeError(f"Container exited unexpectedly before creating connection file. Logs:\n{logs}")
                except docker.errors.NotFound:
                     raise RuntimeError("Container not found unexpectedly while waiting for connection file.")
            time.sleep(0.2)
        self._log("Connection file found.")


    def _connect_to_kernel(self):
        """Waits for the connection file and connects the Jupyter client."""
        self._wait_for_connection_file()
        self._log("Connecting Jupyter client...")

        # Load connection info from the file
        self.kernel_client = jupyter_client.BlockingKernelClient()
        self.kernel_client.load_connection_file(self.connection_file_host)
        self.kernel_client.start_channels()

        # Ensure kernel is ready
        try:
            self.kernel_client.wait_for_ready(timeout=self.timeout)
            self._log("Jupyter client connected and kernel is ready.")
        except RuntimeError as e:
            self._log(f"Kernel did not become ready: {e}", error=True)
            raise TimeoutError(f"Kernel did not become ready within {self.timeout} seconds.") from e


    def run(self, code, timeout=60):
        """
        Executes a block of Python code in the persistent kernel.

        Args:
            code (str): The Python code to execute.
            timeout (int): Max seconds to wait for execution result.

        Returns:
            dict: A dictionary containing 'stdout', 'stderr', and 'result' (if any).
                  Returns None if the client is not connected.
        """
        if not self.kernel_client or not self.kernel_client.is_alive():
            self._log("Cannot run code, kernel client is not connected or alive.", error=True)
            return None # Or raise an exception

        self._log(f"Executing code:\n---\n{code}\n---")
        
        # Clear previous outputs before execution? Maybe not desirable for REPL.
        
        # Execute the code
        msg_id = self.kernel_client.execute(code, store_history=True) # Store history like a REPL

        outputs = []
        stdout_list = []
        stderr_list = []
        result = None

        # Wait for execute_reply message
        try:
            reply = self.kernel_client.get_shell_msg(timeout=timeout)
            if reply['content']['status'] == 'error':
                 error_content = reply['content']
                 stderr_list.append(f"{error_content.get('ename', 'Error')}: {error_content.get('evalue', '')}")
                 stderr_list.extend(error_content.get('traceback', []))


        except Empty:
             self._log(f"Timeout waiting for execution reply for code: {code[:100]}...", error=True)
             raise TimeoutError(f"Timeout waiting for execution reply after {timeout} seconds.")
        except Exception as e:
             self._log(f"Error getting shell message: {e}", error=True)
             # Attempt to fetch IOPub anyway, maybe there's useful info
             
        # Process messages from IOPub channel (stdout, stderr, results) until idle
        while True:
            try:
                # Use a small timeout for IOPub messages after getting the shell reply
                # If the kernel is truly idle, this should time out quickly.
                msg = self.kernel_client.get_iopub_msg(timeout=1.0) 
                msg_type = msg['header']['msg_type']
                content = msg['content']
                
                # Ensure message corresponds to the execution request we sent
                if msg.get('parent_header', {}).get('msg_id') != msg_id:
                    continue

                self._log(f"Received IOPub message: {msg_type}")

                if msg_type == 'stream':
                    if content['name'] == 'stdout':
                        stdout_list.append(content['text'])
                    elif content['name'] == 'stderr':
                        stderr_list.append(content['text'])
                elif msg_type == 'execute_result':
                    result = content['data'].get('text/plain', None)
                    # Could handle other MIME types like 'image/png' if needed
                elif msg_type == 'display_data':
                     # Often used for plots, rich output. Capture text representation.
                     text_repr = content['data'].get('text/plain', '[display_data without text/plain]')
                     stdout_list.append(text_repr) # Add display data to stdout for simplicity
                elif msg_type == 'error':
                    # Errors might also appear on IOPub
                    stderr_list.append(f"{content.get('ename', 'Error')}: {content.get('evalue', '')}")
                    stderr_list.extend(content.get('traceback', []))
                elif msg_type == 'status':
                    if content['execution_state'] == 'idle':
                        break # Kernel is done processing this request

            except Empty:
                # No more messages pending for this execution request
                self._log("IOPub channel idle.")
                break # Exit loop if IOPub is empty for a short while
            except Exception as e:
                self._log(f"Error getting IOPub message: {e}", error=True)
                break # Stop trying if there's an error reading IOPub

        
        output_data = {
            "stdout": "".join(stdout_list),
            "stderr": "\n".join(stderr_list), # Tracebacks often have newlines
            "result": result, # Result of the *last* expression if it wasn't None
        }
        self._log(f"Execution result: {output_data}")
        return output_data


    def close(self):
        """Stops the kernel client and the Docker container."""
        self._log("Closing PythonRepl...")
        # Unregister atexit handler to prevent double close
        atexit.unregister(self.close) 
        # Remove signal handlers
        signal.signal(signal.SIGTERM, signal.SIG_DFL)
        signal.signal(signal.SIGINT, signal.SIG_DFL)

        if self.kernel_client:
            try:
                if self.kernel_client.is_alive():
                    self._log("Stopping kernel client channels...")
                    self.kernel_client.stop_channels()
                    self._log("Kernel client channels stopped.")
            except Exception as e:
                self._log(f"Error stopping kernel client channels: {e}", error=True)
            self.kernel_client = None

        if self.container:
            try:
                self._log(f"Stopping container {self.container.id}...")
                self.container.stop(timeout=5) # Give it a few seconds to stop gracefully
                self._log("Container stopped.")
                # auto_remove should handle removal, but we can try explicitly if needed
                # self.container.remove(force=True) 
            except docker.errors.NotFound:
                 self._log("Container already removed or not found.")
            except docker.errors.APIError as e:
                self._log(f"Error stopping/removing container: {e}", error=True)
                # Try forcing removal if stop failed and it still exists
                try:
                    self.container.reload()
                    self._log(f"Forcing removal of container {self.container.id}...")
                    self.container.remove(force=True)
                except Exception as inner_e:
                     self._log(f"Error force removing container: {inner_e}", error=True)
            except Exception as e: # Catch other potential errors during stop
                self._log(f"An unexpected error occurred during container stop: {e}", error=True)
            self.container = None

        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                self._log(f"Cleaning up temporary directory: {self.temp_dir}")
                shutil.rmtree(self.temp_dir)
                self._log("Temporary directory cleaned up.")
            except Exception as e:
                self._log(f"Error cleaning up temporary directory '{self.temp_dir}': {e}", error=True)
        self.temp_dir = None # Ensure it's not cleaned again

        self._log("PythonRepl closed.")


# --- Example Usage ---
if __name__ == "__main__":
    repl = None # Initialize outside try block for finally clause
    try:
        print("Initializing Python REPL in Docker...")
        # Enable debug=True for detailed logs
        repl = PythonRepl(debug=True) 
        print("\nREPL Initialized. Running commands...")

        print("\n>>> Defining variable 'a'")
        output1 = repl.run("a = 10")
        print(f"Output:\nSTDOUT:\n{output1['stdout']}\nSTDERR:\n{output1['stderr']}\nRESULT: {output1['result']}")

        print("\n>>> Using variable 'a' and defining 'b'")
        output2 = repl.run("b = a * 2\nprint(f'Variable a is {a}')\nb") # Last expression 'b' becomes result
        print(f"Output:\nSTDOUT:\n{output2['stdout']}\nSTDERR:\n{output2['stderr']}\nRESULT: {output2['result']}")

        print("\n>>> Running a command that produces stderr")
        output3 = repl.run("import sys; sys.stderr.write('This is an error message\\n'); 1/0")
        print(f"Output:\nSTDOUT:\n{output3['stdout']}\nSTDERR:\n{output3['stderr']}\nRESULT: {output3['result']}")
        
        print("\n>>> Running multi-line code")
        multi_line_code = """
import time
print('Starting sleep...')
time.sleep(2)
print('Finished sleep.')
x = a + b
x
        """
        output4 = repl.run(multi_line_code)
        print(f"Output:\nSTDOUT:\n{output4['stdout']}\nSTDERR:\n{output4['stderr']}\nRESULT: {output4['result']}")


    except (docker.errors.DockerException, ConnectionError, TimeoutError, RuntimeError, FileNotFoundError) as e:
        print(f"\n--- An error occurred: {e} ---", file=sys.stderr)
        # repl.close() will be called by atexit or finally

    finally:
        if repl:
             print("\nClosing REPL...")
             repl.close() # Explicit close, atexit is a backup
             print("REPL Closed.")