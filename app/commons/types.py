from enum import Enum


class CountryCode(str, Enum):
    US = "US"
    CA = "CA"
    AU = "AU"


class LegacyCountryId:
    """
    select shortname, id from maindb.country
    ID	SHORTNAME
    2	CA
    5	AU
    1	US
    """

    US = 1
    CA = 2
    AU = 5


class Currency(str, Enum):
    USD = "usd"
    CAD = "cad"
    AUD = "aud"


class PgpCode(str, Enum):
    """
    Enum definition of supported payment gateway providers.
    """

    STRIPE = "stripe"
