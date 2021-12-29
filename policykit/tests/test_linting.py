from django.test import TestCase
from policyengine.views import _lint_check


class LinterTests(TestCase):
    def test_init(self):
        code = "pass"
        errors = _lint_check(code)
        self.assertEqual(len(errors), 0)

    def test_pylint_works(self):
        code = "print('lambda)"
        errors = _lint_check(code)
        self.assertEqual(len(errors), 1)
        self.assertEqual(
            errors[0], "1:15: E0001: EOL while scanning string literal (<unknown>, line 1) (syntax-error)"
        )

    def test_no_return_outside_function_error(self):
        code = "return"
        errors = _lint_check(code)
        self.assertEqual(len(errors), 0)

    def test_no_undefined_predefined_variables_error(self):
        for variable in ["policy", "action", "discord", "proposal", "logger", "metagov", "datetime"]:
            code = f"x = {variable}"
            errors = _lint_check(code)
            self.assertEqual(len(errors), 0)

        for variable in ["something_not_defined"]:
            code = f"x = {variable}"
            errors = _lint_check(code)
            self.assertEqual(len(errors), 1)

        for variable in ["PASSED", "FAILED", "PROPOSED"]:
            code = f"x = {variable}"
            errors = _lint_check(code, "check")
            self.assertEqual(len(errors), 0)
