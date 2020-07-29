class NonWhitelistedCodeError(Exception):
    """Raised when user code is executed which is not in the whitelist"""

    def __init__(self, code, lineno, message="Code is not in the whitelist"):
        self.code = code
        self.lineno = lineno
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return "Error at line " + str(self.lineno) + ': "' + self.code + '" ' + self.message
