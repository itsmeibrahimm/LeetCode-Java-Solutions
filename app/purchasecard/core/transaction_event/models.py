import json
from datetime import datetime
from typing import Optional, Any, Dict

from pydantic import BaseModel

from app.purchasecard.constants import (
    MarqetaResponseCodes,
    MARQETA_TRANSACTION_EVENT_AUTHORIZATION_TYPE,
)
from app.purchasecard.models.maindb.card_acceptor import CardAcceptor
from app.purchasecard.models.maindb.marqeta_transaction_event import (
    MarqetaTransactionEvent,
)


class InternalMarqetaTransactionEvent(BaseModel):
    created_at: datetime
    token: str
    amount: int
    transaction_type: str
    shift_id: int
    card_acceptor_name: Optional[str]
    card_inactive: bool
    insufficient_funds: bool
    is_unsuccessful_payment: bool
    raw_type: str
    available_balance: float


def generate_internal_marqeta_transaction_event(
    transaction_event: MarqetaTransactionEvent,
    card_acceptor: Optional[CardAcceptor] = None,
) -> InternalMarqetaTransactionEvent:
    try:
        metadata = json.loads(transaction_event.metadata)
    except (KeyError, AttributeError):
        metadata = {}
    return InternalMarqetaTransactionEvent(
        created_at=transaction_event.created_at,
        token=transaction_event.token,
        amount=transaction_event.amount,
        transaction_type=transaction_event.transaction_type,
        shift_id=transaction_event.shift_id,
        card_acceptor_name=get_card_acceptor_name(
            transaction_event_metadata=metadata, card_acceptor=card_acceptor
        ),
        card_inactive=is_card_inactive(transaction_event_metadata=metadata),
        insufficient_funds=has_insufficient_funds(transaction_event_metadata=metadata),
        is_unsuccessful_payment=is_unsuccessful_payment(
            transaction_event_metadata=metadata
        ),
        raw_type=transaction_event.raw_type,
        available_balance=get_available_balance(transaction_event_metadata=metadata),
    )


def get_card_acceptor_name(
    transaction_event_metadata: Dict[str, Any],
    card_acceptor: Optional[CardAcceptor] = None,
) -> Optional[str]:
    try:
        if card_acceptor:
            card_acceptor_name = card_acceptor.name
        else:
            card_acceptor_metadata = transaction_event_metadata["card_acceptor"]
            card_acceptor_name = (
                card_acceptor_metadata["name"] if card_acceptor_metadata else None
            )
        return card_acceptor_name
    except KeyError:
        return None


def has_insufficient_funds(transaction_event_metadata: Dict[str, Any]) -> bool:
    try:
        response = transaction_event_metadata["response"]
        response_code = response["code"] if response else []
        if response_code:
            return response_code in [
                MarqetaResponseCodes.INSUFFICIENT_FUNDS_1,
                MarqetaResponseCodes.INSUFFICIENT_FUNDS_2,
            ]
        return False
    except KeyError:
        return False


def is_card_inactive(transaction_event_metadata: Dict[str, Any]) -> bool:
    try:
        response = transaction_event_metadata["response"]
        response_code = response["code"] if response else []
        if response_code is not None:
            return response_code in [
                MarqetaResponseCodes.CARD_NOT_ACTIVE,
                MarqetaResponseCodes.CARD_SUSPENDED,
            ]
        return False
    except KeyError:
        return False


def is_unsuccessful_payment(transaction_event_metadata: Dict[str, Any]) -> bool:
    try:
        is_authorization = (
            transaction_event_metadata["type"]
            == MARQETA_TRANSACTION_EVENT_AUTHORIZATION_TYPE
        )
        return is_authorization and has_insufficient_funds(transaction_event_metadata)
    except KeyError:
        return False


def get_available_balance(transaction_event_metadata: Dict[str, Any]) -> float:
    try:
        gpa = transaction_event_metadata["gpa"]
        if gpa and gpa["available_balance"]:
            return gpa["available_balance"]
        return 0.0
    except KeyError:
        return 0.0
