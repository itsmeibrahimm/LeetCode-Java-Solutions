from app.commons.context.logger import get_logger
from app.commons.types import CountryCode, LegacyCountryId


logger = get_logger()


def get_country_id_by_code(country: str) -> int:
    if country == CountryCode.US.value:
        return LegacyCountryId.US
    elif country == CountryCode.CA.value:
        return LegacyCountryId.CA
    elif country == CountryCode.AU.value:
        return LegacyCountryId.AU

    logger.warn(
        f"country {country} does not exist in LegacyCountryId map; defaulting to US"
    )
    return LegacyCountryId.US
