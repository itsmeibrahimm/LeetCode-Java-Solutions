from enum import Enum


class CountryCode(str, Enum):
    US = "US"
    CA = "CA"
    AU = "AU"


class LegacyCountryId:
    US = 1
    CA = 2
    AU = 3


class Currency(str, Enum):
    USD = "usd"
    CAD = "cad"
    AUD = "aud"


class PgpCode(str, Enum):
    """
    Enum definition of supported payment gateway providers.
    """

    STRIPE = "stripe"
