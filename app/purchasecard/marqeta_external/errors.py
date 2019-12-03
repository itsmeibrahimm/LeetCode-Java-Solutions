class MarqetaAPIError(Exception):
    pass


class MarqetaUserAPIError(MarqetaAPIError):
    pass


class MarqetaBadRequest(MarqetaAPIError):
    pass


class MarqetaResourceAlreadyCreated(MarqetaAPIError):
    pass


class MarqetaResourceNotFound(MarqetaAPIError):
    pass


class MarqetaTimeoutError(MarqetaAPIError):
    pass


class MarqetaCannotMoveCardToNewCardHolderError(MarqetaAPIError):
    pass


class DuplicateEmail(MarqetaUserAPIError):
    pass
