import ast

IMPORT_ERROR_MESSAGE = "module cannot be imported because it is not in the list of whitelisted modules."
FUNCTION_BUILTIN_ERROR_MESSAGE = "function cannot be called because it is not in the list of whitelisted builtins."
FUNCTION_MODULE_ERROR_MESSAGE = "function cannot be called because it is not in the list of whitelisted module functions."
DISALLOW_FROM_IMPORT_ERROR_MESSAGE = "using from import syntax is disallowed."

whitelisted_builtins = [
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
]

whitelisted_modules = {
    "base64": [
        "a85encode",
        "a85decode",
        "b16encode",
        "b16decode",
        "b32encode",
        "b32decode",
        "b64encode",
        "b64decode",
        "b85encode",
        "b85decode",
        "standard_b64encode",
        "standard_b64decode",
        "urlsafe_b64encode",
        "urlsafe_b64decode",
    ],
    "calendar": [
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
    ],
    "copy": [
        "copy",
        "deepcopy",
    ],
    "datetime": [
        "MINYEAR",
        "MAXYEAR",
    ],
    "datetime.date": [
        "ctime",
        "day",
        "fromisocalendar",
        "fromisoformat",
        "fromordinal",
        "fromtimestamp",
        "isocalendar",
        "isoformat",
        "isoweekday",
        "max",
        "min",
        "month",
        "replace",
        "resolution",
        "timetuple",
        "today",
        "toordinal",
        "weekday",
        "year",
    ],
    "datetime.time": [
        "dst",
        "fold",
        "fromisoformat",
        "hour",
        "isoformat",
        "max",
        "microsecond",
        "min",
        "minute",
        "replace",
        "resolution",
        "second",
        "tzinfo",
        "tzname",
        "utcoffset",
    ],
    "datetime.datetime": [
        "astimezone",
        "combine",
        "ctime",
        "date",
        "day",
        "dst",
        "fold",
        "fromisocalendar",
        "fromisoformat",
        "fromordinal",
        "fromtimestamp",
        "hour",
        "isocalendar",
        "isoformat",
        "isoweekday",
        "max",
        "microsecond",
        "min",
        "minute",
        "month",
        "now",
        "replace",
        "resolution",
        "second",
        "time",
        "timestamp",
        "timetuple",
        "timetz",
        "today",
        "toordinal",
        "tzinfo",
        "tzname",
        "utcfromtimestamp",
        "utcnow",
        "utcoffset",
        "utctimetuple",
        "weekday",
        "year",
    ],
    "datetime.timedelta": [
        "max",
        "min",
        "resolution",
        "total_seconds",
    ],
    "datetime.tzinfo": [
    ],
    "datetime.timezone": [
        "dst",
        "fromutc",
        "tzname",
        "utc",
        "utcoffset",
    ],
    "itertools": [
        "accumulate",
        "chain",
        "combinations",
        "combinations_with_replacement",
        "compress",
        "count",
        "cycle",
        "dropwhile",
        "filterfalse",
        "groupby",
        "islice",
        "permutations",
        "product",
        "repeat",
        "starmap",
        "takewhile",
        "tee",
        "zip_longest",
    ],
    "math": [
        "acos",
        "acosh",
        "asin",
        "asinh",
        "atan",
        "atanh",
        "atan2",
        "ceil",
        "comb",
        "copysign",
        "cos",
        "cosh",
        "degrees",
        "dist",
        "e",
        "erf",
        "erfc",
        "exp",
        "expm1",
        "fabs",
        "factorial",
        "floor",
        "fmod",
        "frexp",
        "fsum",
        "gamma",
        "gcd",
        "hypot",
        "inf",
        "isclose",
        "isfinite",
        "isinf",
        "isnan",
        "isqrt",
        "ldexp",
        "lgamma",
        "log",
        "log1p",
        "log2",
        "log10",
        "modf",
        "nan",
        "perm",
        "pi",
        "pow",
        "prod",
        "radians",
        "remainder",
        "sin",
        "sinh",
        "sqrt",
        "tan",
        "tanh",
        "tau",
        "trunc",
    ],
    "random": [
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
    ],
    "re": [
    ],
    "time": [
    ],
    "urllib": [
    ],
    "urllib.request": [
    ],
    "urllib.error": [
    ],
    "urllib.parse": [
    ],
}

policyengine_modules = [
    'action',
    'policies',
    'policy',
    'users',
    'roles',
    'votes',
]

class Filter(ast.NodeVisitor):

    def __init__(self):
        self.errors = []

    def visit_Import(self, node):
        for module_alias in node.names:
            if module_alias.name not in whitelisted_modules:
                self.errors.append({ 'type': 'filter', 'lineno': node.lineno, 'code': module_alias.name, 'message': IMPORT_ERROR_MESSAGE })
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        self.errors.append({ 'type': 'filter', 'lineno': node.lineno, 'code': module_alias.names[0].name, 'message': DISALLOW_FROM_IMPORT_ERROR_MESSAGE })

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name):
            function_name = node.func.id
            if function_name not in whitelisted_builtins:
                self.errors.append({ 'type': 'filter', 'lineno': node.lineno, 'code': function_name, 'message': FUNCTION_BUILTIN_ERROR_MESSAGE })
        elif isinstance(node.func, ast.Attribute):
            module_name = node.func.value.id
            function_name = node.func.attr
            if module_name not in policyengine_modules:
                if module_name not in whitelisted_modules:
                    self.errors.append({ 'type': 'filter', 'lineno': node.lineno, 'code': module_name + "." + function_name, 'message': FUNCTION_MODULE_ERROR_MESSAGE })
                if function_name not in whitelisted_modules[module_name]:
                    self.errors.append({ 'type': 'filter', 'lineno': node.lineno, 'code': module_name + "." + function_name, 'message': FUNCTION_MODULE_ERROR_MESSAGE })
        self.generic_visit(node)

    def getErrors(self):
        return self.errors

def filter_code(code):
    tree = ast.parse(code)

    filter = Filter()
    filter.visit(tree)

    return filter.getErrors()
