from RestrictedPython import safe_builtins, utility_builtins, compile_restricted
from RestrictedPython import RestrictingNodeTransformer
from RestrictedPython.Eval import default_guarded_getitem, default_guarded_getiter
from RestrictedPython.Guards import safer_getattr, guarded_unpack_sequence, guarded_iter_unpack_sequence


# permitted modules
import datetime
import base64
import itertools
import json
import logging
logger = logging.getLogger(__name__)

policykit_builtins = {
    # see: https://restrictedpython.readthedocs.io/en/latest/usage/policy.html#predefined-builtins
    **safe_builtins,
    # standard modules like math, random, string and set.
    **utility_builtins,
    # other modules that are permitted in policies, like datetime and json
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
        raise SyntaxError("Import statements are not allowed.", ("<user_code>", node.lineno, node.col_offset, ""))

    visit_ImportFrom = visit_Import


def _hook_writable(obj):
    """Only allow writing to lists and dicts."""
    # if obj.__class__.__name__ == "MY_CLASS_NAME":
    #     return obj
    if isinstance(obj, dict):
        return obj
    if isinstance(obj, list):
        return obj
    raise SyntaxError("Restricted, Cannot write outside restricted defined class/objects")


def _guarded_import(mname, globals=None, locals=None, fromlist=None, level=None):
    """
    Special case to allow builting import for time module. For some reason this is invoked from datetime.strftime()
    Fixes https://github.com/amyxzhang/policykit/issues/534
    """
    if mname == "time":
        return __import__(mname, globals or {}, locals or {}, fromlist or ())
    raise SyntaxError(f"Restricted, cannot import '{mname}'")

def _guarded_getattr(obj, attr):
    """ not to raise exception AttributeError"""
    try:
        return safer_getattr(obj, attr)
    except AttributeError:
        return None
    except Exception as e:
        raise e

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
            "__builtins__": {
                **policykit_builtins,
                # special case guard to fix strftime bug
                "__import__": _guarded_import,
            },
            "_getitem_": default_guarded_getitem,
            "_getiter_": default_guarded_getiter,
            "_unpack_sequence_": guarded_unpack_sequence,
            "_iter_unpack_sequence_": guarded_iter_unpack_sequence,
            "_getattr_": _guarded_getattr,
            "_inplacevar_": lambda op, val, expr: val + expr,  # permit +=
            "_write_": _hook_writable,
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
        logging.debug(f"User code failed with exception: {e}")
        raise