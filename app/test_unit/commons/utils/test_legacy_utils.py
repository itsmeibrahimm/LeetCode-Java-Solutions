from app.commons.types import LegacyCountryId, CountryCode
from app.commons.utils.legacy_utils import get_country_id_by_code


def test_get_country_id_by_code():
    result = get_country_id_by_code(CountryCode.US)
    assert result == LegacyCountryId.US

    result = get_country_id_by_code(CountryCode.CA)
    assert result == LegacyCountryId.CA

    result = get_country_id_by_code(CountryCode.AU)
    assert result == LegacyCountryId.AU

    # Defaults to US
    result = get_country_id_by_code("MX")
    assert result == LegacyCountryId.US
