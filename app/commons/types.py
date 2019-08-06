from enum import Enum


class CountryCode(str, Enum):
    US = "US"
    CA = "CA"
    AU = "AU"


class CurrencyType(str, Enum):
    USD = "usd"
    CAD = "cad"
    AUD = "aud"
