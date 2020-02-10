from app.purchasecard.constants import CARD_ACCEPTOR_NAMES_TO_BE_EXAMINED
from app.purchasecard.core.errors import PurchaseCardInvalidInputError


def enriched_error_parse_int(str_id: str, str_id_name: str) -> int:
    try:
        return int(str_id)
    except ValueError:
        raise PurchaseCardInvalidInputError(id_param=str_id_name)


def should_card_acceptor_be_examined(card_acceptor_name: str) -> bool:
    return any(
        [
            name_trigger.lower() in card_acceptor_name.lower()
            for name_trigger in CARD_ACCEPTOR_NAMES_TO_BE_EXAMINED
        ]
    )
