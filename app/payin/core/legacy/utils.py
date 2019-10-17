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
        "Country does not exist in LegacyCountryId map; defaulting to US",
        country=country,
    )
    return LegacyCountryId.US


def get_country_code_by_id(legacy_country_id: int) -> CountryCode:
    if legacy_country_id == LegacyCountryId.US:
        return CountryCode.US
    elif legacy_country_id == LegacyCountryId.CA:
        return CountryCode.CA
    elif legacy_country_id == LegacyCountryId.AU:
        return CountryCode.AU

    logger.warn(
        "Country id does not exist in LegacyCountryId map; defaulting to US",
        country_id=legacy_country_id,
    )
    return CountryCode.US
