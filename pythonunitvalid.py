import subprocess
import unittest
import os
from flask import Flask, request, render_template, jsonify
from werkzeug.utils import secure_filename
import tempfile
import sys

sys.setrecursionlimit(10000)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'txt', 'py'}

# Function to check if a filename has a valid extension
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def parse_user_code(user_code):
    # Extract function/method definitions from user's code
    functions = []
    lines = user_code.split('\n')
    current_function = ''
    for line in lines:
        if line.strip().startswith("def "):
            if current_function:
                functions.append(current_function)
            current_function = line
        elif current_function:
            current_function += '\n' + line
    if current_function:
        functions.append(current_function)
    return functions

def generate_tests(user_code):
    # Parse user code to get function/method definitions
    functions = parse_user_code(user_code)

    # Create a dynamically generated test suite
    test_suite = unittest.TestSuite()

    # Generate a test case for each function/method
    for i, function_code in enumerate(functions):
        test_name = f'TestFunction_{i}'

        # Define a template for a test case
        test_template = f"""
import unittest

def test_function():
    {function_code}

class {test_name}(unittest.TestCase):
    def test_generated_code(self):
        result = test_function()
        self.assertIsNone(result)

if __name__ == '__main__':
    unittest.main()
"""
        # Create a temporary Python file for the generated test
        test_filename = f'generated_tests_{i}.py'
        with open(test_filename, 'w') as test_file:
            test_file.write(test_template)

        # Add the generated test case to the test suite
        test_suite.addTest(unittest.defaultTestLoader.loadTestsFromName(f'{test_name}.test_generated_code'))

    return test_suite

@app.route('/', methods=['GET', 'POST'])
def upload_and_evaluate():
    if request.method == 'POST':
        # Check if the post request has the file part
        if 'code_file' not in request.files:
            return jsonify({"status": "fail", "error_message": "No file provided"})

        code_file = request.files['code_file']

        # If the user does not select a file, the browser submits an empty part without a filename
        if code_file.filename == '':
            return jsonify({"status": "fail", "error_message": "No file selected"})

        if code_file and allowed_file(code_file.filename):
            user_code = code_file.read().decode('utf-8')

            # Generate the test suite with dynamically generated test cases
            test_suite = generate_tests(user_code)

            # Create a temporary directory to run the test suite
            with tempfile.TemporaryDirectory() as temp_dir:
                os.chdir(temp_dir)

                # Run the test suite and capture the result
                test_result = unittest.TextTestRunner(verbosity=2).run(test_suite)

            # Collect the results, specifically the failed test cases
            failed_tests = [str(test) for test, _ in test_result.failures]

            if test_result.wasSuccessful():
                return jsonify({"status": "pass"})
            else:
                return jsonify({
                    "status": "fail",
                    "failed_tests": failed_tests
                })

    return render_template('upload.html')

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(debug=True)
