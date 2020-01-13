from app.purchasecard.core.errors import PurchaseCardInvalidInputError


def enriched_error_parse_int(str_id: str, str_id_name: str) -> int:
    try:
        return int(str_id)
    except ValueError:
        raise PurchaseCardInvalidInputError(id_param=str_id_name)
