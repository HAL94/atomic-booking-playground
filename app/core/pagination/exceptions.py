class InvalidDatetimeValue(Exception):
    def __init__(self, message="Type of field is datetime, value has to be in isoformat"):
        super().__init__(message)
        self.message = message


class InvalidOperator(Exception):
    pass
