from RestrictedPython import safe_builtins, utility_builtins, compile_restricted
from RestrictedPython import RestrictingNodeTransformer
from RestrictedPython.Eval import default_guarded_getitem, default_guarded_getiter


# permitted modules
import datetime
import base64
import itertools
import json


BUILTINS = {
    # see: https://restrictedpython.readthedocs.io/en/latest/usage/policy.html#predefined-builtins
    **safe_builtins,
    # access to standard modules like math, random, string and set.
    **utility_builtins,
    # other permitted modules
    "datetime": datetime,
    "base64": base64,
    "itertools": itertools,
    "json": json,
}

STATIC_GLOBAL_VARIABLES = {
    "PASSED": "passed",
    "PROPOSED": "proposed",
    "FAILED": "failed",
}


class OwnRestrictingNodeTransformer(RestrictingNodeTransformer):
    def visit_Import(self, node):
        self.error(node, "Import statements are not allowed.")

    visit_ImportFrom = visit_Import


def execute_user_code(user_code: str, user_func: str, *args, **kwargs):
    """
    Execute user code in restricted env using RestrictedPython
    Adapted from https://memoryline.github.io/python/django/security/2020/08/01/how-can-i-accept-and-run-users-code-securely.html

    Args:
        user_code(str) - String containing the unsafe code
        user_func(str) - Function inside user_code to execute and return value
        *args, **kwargs - arguments passed to the user function
    Return:
        Return value of the user_func
    """

    def _apply(f, *a, **kw):
        return f(*a, **kw)

    try:
        # This is the variables we allow user code to see. @result will contain return value.
        restricted_locals = {
            "result": None,
            "args": args,
            "kwargs": kwargs,
        }

        restricted_globals = {
            "__builtins__": BUILTINS,
            "_getitem_": default_guarded_getitem,
            "_getiter_": default_guarded_getiter,
            "_getattr_": getattr,
            "_inplacevar_": lambda op, val, expr: val + expr,  # permit +=
            # to access args and kwargs
            "_apply_": _apply,
            **STATIC_GLOBAL_VARIABLES,
        }

        # Add another line to user code that executes @user_func
        user_code += "\nresult = {0}(*args, **kwargs)".format(user_func)

        # Compile the user code
        byte_code = compile_restricted(
            user_code, filename="<user_code>", mode="exec", policy=OwnRestrictingNodeTransformer
        )

        # Run it
        exec(byte_code, restricted_globals, restricted_locals)

        # User code has modified result inside restricted_locals. Return it.
        return restricted_locals["result"]

    except SyntaxError as e:
        # Code that does not compile
        raise
    except Exception as e:
        # The code did something that is not allowed
        raise