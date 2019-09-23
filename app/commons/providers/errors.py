class ServiceProviderException(Exception):
    ...


class InvalidRequestError(ServiceProviderException):
    ...


class StripeCommandoError(ServiceProviderException):
    ...
