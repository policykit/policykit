from django.test import TestCase

class LinterTests(TestCase):
    def test_init(self):
        code = "pass"
        errors = _error_check(code)
        self.assertEqual(len(errors), 0)

    def test_pylint_works(self):
        code = "print('lambda)"
        errors = _error_check(code)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0], "1:15: E0001: EOL while scanning string literal (<unknown>, line 1) (syntax-error)")

    def test_no_return_outside_function_error(self):
        code = "return"
        errors = _error_check(code)
        self.assertEqual(len(errors), 0)

    def test_no_undefined_predefined_variables_error(self):
        for variable in ['policy', 'action', 'users', 'debug', 'metagov']:
            code = f"x = {variable}"
            errors = _error_check(code)
            self.assertEqual(len(errors), 0)

        for variable in ['boolean_votes', 'number_votes', 'PASSED', 'FAILED', 'PROPOSED']:
            code = f"x = {variable}"
            errors = _error_check(code)
            self.assertEqual(len(errors), 1)

        for variable in ['boolean_votes', 'number_votes', 'PASSED', 'FAILED', 'PROPOSED']:
            code = f"x = {variable}"
            errors = _error_check(code, 'check')
            self.assertEqual(len(errors), 0)
