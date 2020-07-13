class NonWhitelistedCodeError(Exception):
    """Raised when user code is executed which is not in the whitelist"""

    def __init__(self, code, message="Code is not in the whitelist"):
        self.code = code
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return self.code + " -> " + self.message
