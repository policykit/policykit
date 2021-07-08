from pylint.lint import Run
from pylint.reporters.text import TextReporter
import tempfile
import os

def should_keep_error_message(error_message, function_name):
    """
    Checks provided error message and returns whether or not the error message
    should be kept.
    """
    # Don't return lines with error code E0104, which denotes
    # "Return outside function" error. We don't want to return this
    # error because many code cells contain returns because they are
    # inside unseen wrapper functions.
    if error_message.find('E0104') != -1:
        return False

    # Don't return lines which say that a pre-defined local variable in
    # our wrapper function is undefined. check_policy has a few extra
    # pre-defined local variables than the other wrapper functions.
    local_variables = ['policy', 'action', 'users', 'debug', 'metagov']
    if function_name == 'check':
        local_variables.extend(['boolean_votes', 'number_votes', 'PASSED', 'FAILED', 'PROPOSED'])
    for variable in local_variables:
        if error_message.find(f"E0602: Undefined variable '{variable}' (undefined-variable)") != -1:
            return False

    return True

class PylintOutput:
    """
    Used internally to write output / error messages to a list
    from the TextReporter object in _error_check(code).
    """
    def __init__(self):
        self.output = []

    def write(self, line):
        self.output.append(line)

    def read(self):
        return self.output

def _error_check(code, function_name = 'filter'):
    """
    Checks provided Python code for errors. Syntax errors are checked for with
    Pylint. Returns a list of errors from linting.
    """
    # Since Pylint can only be used on files and not strings directly, we must
    # save the code to a temporary file. The file will be deleted after we are
    # finished.
    (fd, filename) = tempfile.mkstemp()
    errors = []
    try:
        tmpfile = os.fdopen(fd, 'w')
        tmpfile.write(code)
        tmpfile.close()

        output = PylintOutput()
        # We disable refactoring (R), convention (C), and warning (W) related checks
        run = Run(["-r", "n", "--disable=R,C,W", filename], reporter=TextReporter(output), do_exit=False)

        for line in output.read():
            # Only return lines that have error messages (lines with colons are error messages)
            sep = line.find(':')
            if sep == -1:
                continue

            if should_keep_error_message(line, function_name):
                errors.append(line[sep + 1:])
    finally:
        os.remove(filename)
    return errors
