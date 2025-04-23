
from python_docker_reply import PythonDockerREPL
import unittest
from unittest.mock import patch, MagicMock, PropertyMock
from docker.errors import DockerException, ImageNotFound, APIError, ContainerError
import sys
import io

class TestPythonDockerREPL(unittest.TestCase):

    @patch('docker.from_env')
    def setUp(self, mock_from_env):
        # Mock the Docker client and its methods
        self.mock_client = MagicMock()
        self.mock_containers = MagicMock()
        self.mock_images = MagicMock()

        # Configure mock_from_env to return our mock client
        mock_from_env.return_value = self.mock_client

        # Configure mock client attributes
        self.mock_client.containers = self.mock_containers
        self.mock_client.images = self.mock_images
        self.mock_client.ping.return_value = True # Simulate successful ping

        # Simulate image exists
        self.mock_images.get.return_value = MagicMock()

        # Default mock for successful run returning stdout bytes
        # This is returned when exit code is 0
        self.mock_containers.run.return_value = b"Line 1\nLine 2\nFinal Output"

        # Instantiate the class, docker.from_env will be called here
        self.repl = PythonDockerREPL(image_name="test-image")

        # Reset mock_containers.run for specific test scenarios if needed
        # Important: Reset AFTER instantiation in setUp
        self.mock_containers.run.reset_mock()
        # Re-apply default for tests that don't set a side_effect
        self.mock_containers.run.return_value = b"Line 1\nLine 2\nFinal Output"


    @patch('docker.from_env')
    def test_init_success(self, mock_from_env):
        """Test successful initialization."""
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_client.images.get.return_value = MagicMock() # Image found
        mock_from_env.return_value = mock_client

        repl = PythonDockerREPL(image_name="test-image")
        self.assertEqual(repl.image_name, "test-image")
        self.assertIsNotNone(repl.client)
        mock_client.ping.assert_called_once()
        mock_client.images.get.assert_called_once_with("test-image")

    @patch('docker.from_env')
    def test_init_docker_error(self, mock_from_env):
        """Test initialization failure when Docker is not running."""
        mock_from_env.side_effect = DockerException("Docker daemon not found")
        with self.assertRaisesRegex(RuntimeError, "Failed to initialize Docker client"):
            PythonDockerREPL(image_name="test-image")

    @patch('docker.from_env')
    def test_init_image_not_found_warning(self, mock_from_env):
        """Test initialization warning when image is not found locally."""
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_client.images.get.side_effect = ImageNotFound("Image not found")
        mock_from_env.return_value = mock_client

        # Capture stderr warnings
        with patch('sys.stderr', new_callable=io.StringIO) as mock_stderr:
            repl = PythonDockerREPL(image_name="missing-image")
            self.assertIn("Warning: Image 'missing-image' not found locally", mock_stderr.getvalue())
        self.assertEqual(repl.image_name, "missing-image")

    def test_init_empty_image_name(self):
        """Test initialization with an empty image name."""
        with self.assertRaises(ValueError):
              PythonDockerREPL(image_name="")

    def test_run_simple_print(self):
        """Test running code that produces simple stdout."""
        code = "print('Hello')\nprint('World')"
        expected_output = "World"
        # Configure mock run to return stdout bytes for success case
        self.mock_containers.run.return_value = b"Hello\nWorld"

        result = self.repl.run(code)

        self.assertEqual(result, expected_output)
        # Check arguments passed to run (no stdin_open or input)
        self.mock_containers.run.assert_called_once_with(
            image="test-image",
            command=["python", "-u", "-c", code], # Verify code is passed via command
            stdout=True,
            stderr=True,
            detach=False,
            remove=True,
        )

    def test_run_multiline_last_line(self):
        """Test multiline code where the last line is the desired output."""
        code = "x = 10\ny = 20\nprint(x + y)"
        expected_output = "30"
        self.mock_containers.run.return_value = b"30"

        result = self.repl.run(code)
        self.assertEqual(result, expected_output)
        # Verify command structure again
        self.mock_containers.run.assert_called_once_with(
            image="test-image",
            command=["python", "-u", "-c", code],
            stdout=True, stderr=True, detach=False, remove=True
        )


    def test_run_with_stderr(self):
        """Test running code that produces stderr (simulated via ContainerError)."""
        code = "import sys\nprint('stdout line')\nsys.stderr.write('stderr line')\nsys.exit(1)"
        expected_output = "stderr line" # Last non-empty line overall

        # *** CHANGE: Correctly mock ContainerError ***
        mock_container_obj = MagicMock(id="test_container_id") # Mock container needed for constructor
        mock_error = ContainerError(
            container=mock_container_obj,
            exit_status=1,
            command=["python", "-u", "-c", code], # Command that failed
            image="test-image",
            stderr=b"Some warning\nstderr line" # stderr goes here
        )
        # Manually set the stdout attribute, as it's not part of constructor
        mock_error.stdout = b"stdout line"
        self.mock_containers.run.side_effect = mock_error # Raise this error when run is called

        result = self.repl.run(code)
        self.assertEqual(result, expected_output)
        # Verify run was called with correct args before error was raised
        self.mock_containers.run.assert_called_once_with(
             image="test-image",
             command=["python", "-u", "-c", code],
             stdout=True, stderr=True, detach=False, remove=True
         )

    def test_run_only_stderr(self):
        """Test running code that produces only stderr."""
        code = "import sys; sys.stderr.write('Error occurred'); sys.exit(1)"
        expected_output = "Error occurred"

        # *** CHANGE: Correctly mock ContainerError ***
        mock_container_obj = MagicMock(id="test_container_id_err")
        mock_error = ContainerError(
            container=mock_container_obj,
            exit_status=1,
            command=["python", "-u", "-c", code],
            image="test-image",
            stderr=b"Error occurred"
        )
        mock_error.stdout = b'' # Ensure stdout is empty bytes
        self.mock_containers.run.side_effect = mock_error

        result = self.repl.run(code)
        self.assertEqual(result, expected_output)

    def test_run_no_output(self):
        """Test running code that produces no output and exits successfully."""
        code = "pass"
        expected_output = ""
        # Simulate successful run (exit 0) with no stdout
        self.mock_containers.run.return_value = b""

        result = self.repl.run(code)
        self.assertEqual(result, expected_output)

    def test_run_syntax_error(self):
        """Test running code with a Python syntax error."""
        code = "print 'hello'" # SyntaxError in Python 3
        # The exact error message might vary slightly, focus on the end
        expected_end = "SyntaxError: Missing parentheses in call to 'print'. Did you mean print('hello')?"

        stderr_content = f"""Traceback (most recent call last):
  File "<string>", line 1
    print 'hello'
          ^
{expected_end}""".encode('utf-8')

        # *** CHANGE: Correctly mock ContainerError ***
        mock_container_obj = MagicMock(id="test_container_id_syntax")
        mock_error = ContainerError(
            container=mock_container_obj,
            exit_status=1, # Syntax errors typically exit non-zero
            command=["python", "-u", "-c", code],
            image="test-image",
            stderr=stderr_content
        )
        mock_error.stdout = b'' # Syntax errors usually don't produce stdout
        self.mock_containers.run.side_effect = mock_error

        result = self.repl.run(code)
        self.assertTrue(result.endswith(expected_end), f"Expected end: '{expected_end}', Got: '{result}'")


    def test_run_image_not_found_error(self):
        """Test Docker ImageNotFound error during run."""
        code = "print('test')"
        self.mock_containers.run.side_effect = ImageNotFound("Cannot find image test-image")

        with self.assertRaises(ImageNotFound):
            self.repl.run(code)

    def test_run_api_error(self):
        """Test Docker APIError during run."""
        code = "print('test')"
        self.mock_containers.run.side_effect = APIError("Docker API is sad")

        with self.assertRaisesRegex(RuntimeError, "Docker API error during container run"):
            self.repl.run(code)

    def test_run_non_string_input(self):
        """Test passing non-string input to run."""
        with self.assertRaises(TypeError):
            self.repl.run(123) # type: ignore

    def test_close_method(self):
        """Test the close method."""
        self.repl.close()
        self.mock_client.close.assert_called_once()

    @patch('docker.from_env')
    def test_close_error_handling(self, mock_from_env):
        """Test error handling during close."""
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_client.images.get.return_value = MagicMock()
        mock_client.close.side_effect = Exception("Failed to close")
        mock_from_env.return_value = mock_client

        repl = PythonDockerREPL(image_name="test-image")
        with patch('sys.stderr', new_callable=io.StringIO) as mock_stderr:
            repl.close()
            self.assertIn("Error closing Docker client: Failed to close", mock_stderr.getvalue())


# --- Main execution for tests and example ---

if __name__ == '__main__':
    # Example Usage (requires Docker running and 'python:3.9-alpine' or your target image pulled)
    print("--- Example Usage ---")
    try:
        # Use a readily available small python image for example, if blazing-python-ds isn't public
        # Replace 'python:3.9-alpine' with 'blazing-python-ds' if you have it
        repl_instance = PythonDockerREPL(image_name='python:3.9-alpine') # Or your actual image

        code1 = "print('Hello from Docker')\nx=5\ny=10\nprint(f'The sum is: {x+y}')"
        print(f"Running code:\n---\n{code1}\n---")
        output1 = repl_instance.run(code1)
        print(f"Last output line: '{output1}'\n") # Should be 'The sum is: 15'

        code2 = "a = [1, 2, 3]\nprint(a[-1])"
        print(f"Running code:\n---\n{code2}\n---")
        output2 = repl_instance.run(code2)
        print(f"Last output line: '{output2}'\n") # Should be '3'

        # Code producing stdout and stderr but exiting successfully (exit 0)
        code3 = "import sys\nprint('Info')\nsys.stderr.write('Warning line 1\\n')\nsys.stderr.write('Error line 2')\nsys.exit(0)"
        print(f"Running code (exit 0 with stderr):\n---\n{code3}\n---")
        output3 = repl_instance.run(code3)
        # NOTE: With exit 0, run() only returns stdout bytes. stderr might be lost unless Docker daemon logs are checked.
        # The class currently captures stderr primarily via ContainerError (non-zero exit).
        print(f"Last output line (likely stdout only for exit 0): '{output3}'\n") # Expect 'Info'

        # Code producing only stderr and exiting with error (exit 1)
        code4 = "import sys\nsys.stderr.write('This is an error message')\nsys.exit(1)"
        print(f"Running code (exit 1 with stderr):\n---\n{code4}\n---")
        output4 = repl_instance.run(code4)
        print(f"Last output line: '{output4}'\n") # Should be 'This is an error message'

        # Code with a syntax error
        code5 = "print 'hello'"
        print(f"Running code (syntax error):\n---\n{code5}\n---")
        output5 = repl_instance.run(code5)
        print(f"Last output line (stderr): '{output5}'\n") # Should be the SyntaxError message line

        repl_instance.close()

    except (RuntimeError, ImageNotFound, APIError, ValueError) as e:
        print(f"Error during example usage: {e}", file=sys.stderr)
    except Exception as e:
        print(f"An unexpected error occurred during example usage: {e}", file=sys.stderr)


    print("\n--- Running Unit Tests ---")
    # Run tests using unittest's discovery or by directly running the script
    # Comment out the example usage if you want *only* test output
    # To run tests directly: comment out example usage, uncomment unittest.main()
    # Using TestLoader is preferred over makeSuite for newer Python versions
    # unittest.main(argv=['first-arg-is-ignored'], exit=False) # Deprecated makeSuite call removed
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestPythonDockerREPL)
    runner = unittest.TextTestRunner()
    runner.run(suite)