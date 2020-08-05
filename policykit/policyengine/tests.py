from django.test import TestCase
from policyengine.filter import *

def filter_test(code, shouldPass=True):
    errors = filter_code(code)
    if len(errors) > 0:
        if shouldPass:
            print("FAILED test case: should have passed: " + code + "\n")
    else:
        if shouldPass == False:
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

code = [
# Code 1
"""
action.execute()
""",

# Code 2
"""
if action.initiator.groups.filter(name = "Moderator").exists():
return PASSED
else:
return FAILED
""",

# Code 3
"""
import math

voter_users = users.filter(groups__name__in=['Moderator'])
yes_votes = action.proposal.get_yes_votes(users=voter_users, value=True)
if len(yes_votes) >= math.ceil(voter_users.count()/2):
return PASSED
elif action.proposal.time_elapsed() > datetime.timedelta(days=1):
return FAILED
""",

# Code 4
"""
usernames = [u.username for u in users]
jury = random.sample(usernames, k=3)
action.data.add('jury', jury)
""",

# Code 5
"""
jury = action.data.get('jury')
jury_users = users.filter(username__in=jury)
yes_votes = action.proposal.get_yes_votes(users=jury_users, value=True)
if len(yes_votes) >= 2:
return PASSED
elif action.proposal.time_elapsed() > datetime.timedelta(days=2):
return FAILED
""",
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
            filter_test(code, shouldPass=False)

    def test_dangerous_functions(self):
        print("Testing calling of dangerous functions\n")
        for function in dangerous_functions:
            code = function + "()"
            filter_test(code, shouldPass=False)

    def test_policy_code(self):
        for i in range(len(code)):
            print("Testing policy code " + str(i) + "\n")
            filter_test(code[i])
