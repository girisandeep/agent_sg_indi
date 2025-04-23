import unittest
from python_docker_repl import PythonDockerREPL

class TestPythonDockerREPL(unittest.TestCase):
    def setUp(self):
        # Use a lightweight public image for testing
        self.repl = PythonDockerREPL(image_name="python:3.11-slim", timeout=20)

    def tearDown(self):
        self.repl.close()

    def test_simple_expression(self):
        self.assertEqual(self.repl.run("1 + 2"), 3)

    def test_multiline_expression(self):
        code = '''\
# define two variables
x = 7
y = 8
# last line is expression
x * y
'''  
        self.assertEqual(self.repl.run(code), 56)

    def test_state_persistence(self):
        self.repl.run("counter = 10")
        self.assertEqual(self.repl.run("counter + 5"), 15)

    def test_no_expression(self):
        # Assignment only, no trailing expression
        self.assertIsNone(self.repl.run("z = 42"))

    def test_string_expression(self):
        self.assertEqual(self.repl.run("'hello'.upper()"), "HELLO")

if __name__ == '__main__':
    unittest.main()
