import ast
from policyengine.exceptions import NonWhitelistedCodeError

IMPORT_ERROR_MESSAGE = "module cannot be imported because it is not in the list of whitelisted modules."
FUNCTION_ERROR_MESSAGE = "function cannot be called because it is not in the list of whitelisted modules."

whitelisted_modules = [
    "base64",
    "calendar",
    "collections",
    "copy",
    "datetime",
    "datetime.date",
    "datetime.time",
    "datetime.datetime",
    "datetime.timedelta",
    "datetime.tzinfo",
    "datetime.timezone",
    "itertools",
    "json",
    "math",
    "random",
    "re",
    "time",
    "urllib",
    "urllib.request",
    "urllib.error",
    "urllib.parse",
]

whitelisted_functions = [
    # Built-ins
    "abs",
    "all",
    "any",
    "bool",
    "bytes",
    "chr",
    "divmod",
    "enumerate",
    "float",
    "hash",
    "hex",
    "id",
    "int",
    "iter",
    "len",
    "list",
    "map",
    "max",
    "min",
    "next",
    "pow",
    "range",
    "round",
    "set",
    "slice",
    "sorted",
    "str",
    "sum",
    "tuple",
    "zip",

    # Base64 library
    "b64encode",
    "b64decode",
    "standard_b64encode",
    "standard_b64decode",
    "urlsafe_b64encode",
    "urlsafe_b64decode",

    # Calendar library
    "calendar",
    "day_abbr",
    "day_name",
    "firstweekday",
    "isleap",
    "iterweekdays",
    "itermonthdates",
    "itermonthdays",
    "itermonthdays2",
    "itermonthdays3",
    "itermonthdays4",
    "leapdays",
    "month",
    "monthcalendar",
    "monthdatescalendar",
    "monthdays2calendar",
    "monthdayscalendar",
    "monthrange",
    "month_abbr",
    "month_name",
    "setfirstweekday",
    "timegm",
    "weekday",
    "weekheader",
    "yeardatescalendar",
    "yeardays2calendar",
    "yeardayscalendar",

    # Datetime library
    "day",
    "fromisocalendar",
    "fromisoformat",
    "fromordinal",
    "fromtimestamp",
    "hour",
    "max",
    "microsecond",
    "min",
    "minute",
    "month",
    "resolution",
    "second",
    "today",
    "year",

    # Math library
    "acos",
    "asin",
    "atan",
    "ceil",
    "comb",
    "cos",
    "degrees",
    "dist",
    "e",
    "exp",
    "fabs",
    "factorial",
    "floor",
    "fmod",
    "frexp",
    "fsum",
    "gcd",
    "isclose",
    "isfinite",
    "isinf",
    "isnan",
    "log",
    "log2",
    "log10",
    "modf",
    "perm",
    "pi",
    "pow",
    "prod",
    "radians",
    "remainder",
    "sin",
    "sqrt",
    "tan",
    "trunc",

    # Random library
    "betavariate",
    "choice",
    "choices",
    "expovariate",
    "gammavariate",
    "gauss",
    "lognormvariate",
    "normalvariate",
    "paretovariate",
    "randint",
    "random",
    "randrange",
    "sample",
    "seed",
    "shuffle",
    "triangular",
    "uniform",
    "vonmisesvariate",
    "weibullvariate",
]

class Filter(ast.NodeVisitor):
    def visit_Import(self, node):
        for module_alias in node.names:
            if module_alias.name not in whitelisted_modules:
                raise NonWhitelistedCodeError(module_alias.name, IMPORT_ERROR_MESSAGE)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        for module_alias in node.names:
            if module_alias.name not in whitelisted_modules:
                raise NonWhitelistedCodeError(module_alias.name, IMPORT_ERROR_MESSAGE)
        self.generic_visit(node)

    def visit_Call(self, node):
        if node.func.id not in whitelisted_functions:
            raise NonWhitelistedCodeError(node.func.id, FUNCTION_ERROR_MESSAGE)
        self.generic_visit(node)

def filter_code(code):
    tree = ast.parse(code)

    filter = Filter()
    filter.visit(tree)
