from django.test import TestCase
from policyengine.filter import *
from policyengine.exceptions import NonWhitelistedCodeError

def filter_test(code, shouldPass=True):
    try:
        filter_code(code)
        if shouldPass == False:
            print("FAILED test case: should have passed: " + code + "\n")
    except NonWhitelistedCodeError:
        if shouldPass:
            print("FAILED test case: should NOT have passed: " + code + "\n")

dangerous_modules = [
    "os",
    "string", # NOTE: dangerous for now until can figure out how to avoid format string vulnerabilities
    "sys",
]

dangerous_functions = [
    "compile",
    "dir",
    "exec",
    "execfile",
    "eval",
    "file",
    "globals",
    "input",
    "locals",
    "open",
    "raw_input",
    "vars",
]

# Create your tests here.
class FilterTests(TestCase):
    def test_import_whitelisted_modules(self):
        print("Testing importing of whitelisted modules\n")
        for module in whitelisted_modules:
            code = "import " + module
            filter_test(code)

    def test_dangerous_modules(self):
        print("Testing importing of dangerous modules\n")
        for module in dangerous_modules:
            code = "import " + module
            filter_test(code)

    def test_dangerous_functions(self):
        print("Testing calling of dangerous functions\n")
        for function in dangerous_functions:
            code = function + "()"
            filter_test(code)
