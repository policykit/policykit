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
    # Evaluation debug logging
    "debug"
]

whitelisted_modules = {
    "metagov": [
        "start_process",
        "close_process",
        "get_process",
        "perform_action",
    ],
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
        "timedelta",
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

policyengine_functions = [
    'add',
    'count',
    'execute',
    'exists',
    'filter',
    'get',
    'get_yes_votes',
    'get_no_votes',
    'get_all_boolean_votes',
    'get_all_number_votes',
    'get_one_number_votes',
    'notify_action',
    'get_time_elapsed',
    'get_users',
    'genericrole_set.all',
    'remove',
    'set',
    'get_roles',
    'has_role'
]

# Don't whitelist any string functions that allow for format string vulnerabilities
string_functions = [
    'capitalize',
    'casefold',
    'center',
    'count',
    'encode',
    'endswith',
    'expandtabs',
    'find',
    'index',
    'isalnum',
    'isalpha',
    'isdecimal',
    'isdigit',
    'isidentifier',
    'islower',
    'isnumeric',
    'isprintable',
    'isspace',
    'istitle',
    'isupper',
    'join',
    'ljust',
    'lower',
    'lstrip',
    'maketrans',
    'partition',
    'replace',
    'rfind',
    'rindex',
    'rjust',
    'rpartition',
    'rsplit',
    'rstrip',
    'split',
    'splitlines',
    'startswith',
    'strip',
    'swapcase',
    'title',
    'translate',
    'upper',
    'zfill'
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

    def is_function_allowed(self, function_name):
        if function_name in string_functions:
            return True
        if function_name in policyengine_functions:
            return True
        return False

    def visit_Call(self, node):
        lineno = node.lineno

        if isinstance(node.func, ast.Name):
            name = node.func.id
            if name not in whitelisted_builtins:
                self.errors.append({ 'type': 'filter', 'lineno': lineno, 'code': name, 'message': FUNCTION_BUILTIN_ERROR_MESSAGE })
        elif isinstance(node.func, ast.Attribute):
            calling_node = node.func.value
            function_name = node.func.attr
            if isinstance(calling_node, ast.Name):
                calling_name = calling_node.id
                if calling_name in whitelisted_modules:
                    if function_name not in whitelisted_modules[calling_name]:
                        self.errors.append({ 'type': 'filter', 'lineno': lineno, 'code': calling_name + "." + function_name, 'message': FUNCTION_MODULE_ERROR_MESSAGE })
                elif self.is_function_allowed(function_name) == False:
                    self.errors.append({ 'type': 'filter', 'lineno': lineno, 'code': calling_name + "." + function_name, 'message': FUNCTION_MODULE_ERROR_MESSAGE })
            elif isinstance(calling_node, ast.Attribute):
                calling_name = calling_node.attr
                if self.is_function_allowed(function_name) == False:
                    self.errors.append({ 'type': 'filter', 'lineno': lineno, 'code': calling_name + "." + function_name, 'message': FUNCTION_MODULE_ERROR_MESSAGE })

        self.generic_visit(node)

    def getErrors(self):
        return self.errors

def filter_code(code):
    tree = ast.parse(code)

    filter = Filter()
    filter.visit(tree)

    return filter.getErrors()
