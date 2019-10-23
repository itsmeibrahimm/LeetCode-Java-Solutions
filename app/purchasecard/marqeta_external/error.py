class MarqetaAPIError(Exception):
    pass


class MarqetaUserAPIError(MarqetaAPIError):
    pass


class MarqetaBadRequest(MarqetaAPIError):
    pass


class MarqetaResourceAlreadyCreated(MarqetaAPIError):
    pass


class DuplicateEmail(MarqetaUserAPIError):
    pass
