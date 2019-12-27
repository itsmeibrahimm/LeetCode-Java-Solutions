from typing import Optional

from app.commons.context.logger import get_logger
from app.commons.types import CountryCode, LegacyCountryId
from app.payin.core.payer.types import PayerType
from app.payin.core.types import PayerIdType, PayerReferenceIdType

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


def payer_id_type_to_payer_reference_id_type(
    payer_id_type: PayerIdType
) -> PayerReferenceIdType:
    if payer_id_type == PayerIdType.PAYER_ID:
        return PayerReferenceIdType.PAYER_ID
    elif payer_id_type == PayerIdType.DD_CONSUMER_ID:
        return PayerReferenceIdType.DD_CONSUMER_ID
    elif payer_id_type == PayerIdType.DD_STRIPE_CUSTOMER_SERIAL_ID:
        return PayerReferenceIdType.DD_STRIPE_CUSTOMER_ID
    elif payer_id_type == PayerIdType.STRIPE_CUSTOMER_ID:
        return PayerReferenceIdType.STRIPE_CUSTOMER_ID

    return PayerReferenceIdType.PAYER_ID


def payer_type_to_payer_reference_id_type(
    payer_type: Optional[PayerType]
) -> PayerReferenceIdType:
    if payer_type == PayerType.MARKETPLACE:
        return PayerReferenceIdType.DD_CONSUMER_ID
    elif payer_type == PayerType.BUSINESS:
        return PayerReferenceIdType.DD_DRIVE_BUSINESS_ID
    elif payer_type == PayerType.STORE:
        return PayerReferenceIdType.DD_DRIVE_STORE_ID
    elif payer_type == PayerType.MERCHANT:
        return PayerReferenceIdType.DD_DRIVE_MERCHANT_ID

    return PayerReferenceIdType.PAYER_ID


def owner_type_to_payer_reference_id_type(owner_type: str) -> PayerReferenceIdType:
    if owner_type == "store":
        return PayerReferenceIdType.DD_DRIVE_STORE_ID
    elif owner_type == "merchant":
        return PayerReferenceIdType.DD_DRIVE_MERCHANT_ID
    elif owner_type == "business":
        return PayerReferenceIdType.DD_DRIVE_BUSINESS_ID

    return PayerReferenceIdType.PAYER_ID
