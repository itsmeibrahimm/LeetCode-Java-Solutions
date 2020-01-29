from typing import Dict

from app.commons.types import Currency
from app.payin.core.exceptions import PayinError, PayinErrorCode

MINIMUM_CHARGEABLE_AMOUNT_CONFIG: Dict[Currency, int] = {
    Currency.USD: 50,
    Currency.AUD: 50,
    Currency.CAD: 50,
}


def validate_min_amount(currency: Currency, amount: int):
    if amount < MINIMUM_CHARGEABLE_AMOUNT_CONFIG.get(currency, 0):
        raise PayinError(error_code=PayinErrorCode.CART_PAYMENT_AMOUNT_INVALID)
