import json
from uuid import uuid4

import requests
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from unittest.mock import MagicMock

from app.purchasecard.constants import MARQETA_TRANSACTION_EVENT_TRANSACTION_TYPE
from app.purchasecard.marqeta_external.models import MarqetaProviderCard
from app.purchasecard.models.maindb.card_acceptor import CardAcceptor
from app.purchasecard.models.maindb.delivery_funding import DeliveryFunding
from app.purchasecard.models.maindb.marqeta_card_ownership import MarqetaCardOwnership
from app.purchasecard.models.maindb.marqeta_decline_exemption import (
    MarqetaDeclineExemption,
)
from app.purchasecard.models.maindb.marqeta_transaction_event import (
    MarqetaTransactionEvent,
)
from app.purchasecard.models.maindb.store_mastercard_data import StoreMastercardData
from app.purchasecard.repository.card_acceptor import CardAcceptorRepository
from app.purchasecard.repository.delivery_funding import DeliveryFundingRepository
from app.purchasecard.repository.marqeta_card_ownership import (
    MarqetaCardOwnershipRepository,
)
from app.purchasecard.repository.marqeta_decline_exemption import (
    MarqetaDeclineExemptionRepository,
)
from app.purchasecard.repository.marqeta_transaction_event import (
    MarqetaTransactionEventRepository,
)
from app.purchasecard.repository.store_mastercard_data import (
    StoreMastercardDataRepository,
)
from app.testcase_utils import validate_expected_items_in_dict
from app.purchasecard.models.maindb.marqeta_transaction import MarqetaTransaction
from app.purchasecard.repository.marqeta_transaction import MarqetaTransactionRepository


class FakeMarqetaEnvironment:
    TEST_TOKEN: str = "card-test-token"
    TEST_DELIGHT_NUMBER: int = 1234
    TEST_LAST_FOUR: str = "9767"
    TEST_DASHER_ID: int = 1234
    TEST_USER_TOKEN: str = "1234"
    TEST_CARD_PRODUCT_TOKEN = "card-product-test-token"

    def __init__(self, marqeta_client):
        self.marqeta_client = marqeta_client

    def setup_test_card_product(self):
        auth = (self.marqeta_client._username, self.marqeta_client._password)
        url = self.marqeta_client.get_url(
            "cardproducts/{}".format(self.TEST_CARD_PRODUCT_TOKEN)
        )
        response = requests.get(url=url, auth=auth)
        if response.status_code == 200:
            return

        if response.status_code != 404:
            raise Exception(response.content)

        url = self.marqeta_client.get_url("cardproducts")
        data = {
            "token": self.TEST_CARD_PRODUCT_TOKEN,
            "config": {
                "fulfillment": {
                    "shipping": {
                        "recipient_address": {
                            "first_name": "test_first_name",
                            "last_name": "test_last_name",
                            "address1": "150 W Evelyn",
                            "city": "San Francisco",
                            "state": "CA",
                            "zip": "94040",
                            "country": "US",
                        }
                    }
                }
            },
            "name": "test_card_product_name",
            "start_date": "2019-10-30",
        }
        response = requests.post(url=url, auth=auth, json=data)
        assert response.status_code == 201

    def setup_test_card_with_token(self, test_token, user_token):
        self.setup_test_card_product()
        auth = (self.marqeta_client._username, self.marqeta_client._password)
        url = self.marqeta_client.get_url("cards")
        data = {
            "token": test_token,
            "user_token": user_token,
            "card_product_token": self.TEST_CARD_PRODUCT_TOKEN,
        }
        response = requests.post(url=url, auth=auth, json=data)
        assert response.status_code == 201
        return MarqetaProviderCard(**json.loads(response.content))

    def activate_card_with_token(self, test_token):
        auth = (self.marqeta_client._username, self.marqeta_client._password)
        url = self.marqeta_client.get_url("cards/{}/activate".format(test_token))
        response = requests.put(url=url, auth=auth)
        assert response.status_code == 200

    def setup_test_user(self):
        auth = (self.marqeta_client._username, self.marqeta_client._password)
        url = self.marqeta_client.get_url("users")
        test_user_token = str(uuid4())
        data = {
            "token": test_user_token,
            "first_name": "jasmine",
            "last_name": "tea",
            "email": str(uuid4()) + "@doordash.com",
        }
        response = requests.post(url=url, auth=auth, json=data)

        assert response.status_code == 201
        return test_user_token


async def prepare_and_insert_store_mastercard_data(
    store_mastercard_data_repo: StoreMastercardDataRepository,
    store_id: int,
    mid: str,
    mname: str = "",
) -> StoreMastercardData:
    data = {"store_id": store_id, "mid": mid}
    store_mastercard_data = await store_mastercard_data_repo.create_store_mastercard_data(
        store_id=store_id, mid=mid, mname=mname
    )
    assert store_mastercard_data.id, "store mastercard data is created, assigned an ID"
    validate_expected_items_in_dict(expected=data, actual=store_mastercard_data.dict())
    return store_mastercard_data


async def prepare_and_insert_marqeta_transaction_data(
    marqeta_tx_repo: MarqetaTransactionRepository,
    token: str,
    amount: int,
    delivery_id: int,
    card_acceptor: str,
    timed_out: Optional[bool] = None,
    swiped_at: Optional[datetime] = None,
) -> MarqetaTransaction:
    swiped_at = swiped_at if swiped_at else datetime.now(timezone.utc)
    data = {
        "token": token,
        "amount": amount,
        "swiped_at": swiped_at,
        "delivery_id": delivery_id,
        "card_acceptor": card_acceptor,
        "timed_out": timed_out,
    }
    marqeta_transaction_data = await marqeta_tx_repo.create_marqeta_transaction(
        token=token,
        amount=amount,
        swiped_at=swiped_at,
        delivery_id=delivery_id,
        card_acceptor=card_acceptor,
        timed_out=timed_out,
    )
    assert marqeta_transaction_data.id
    validate_expected_items_in_dict(
        expected=data, actual=marqeta_transaction_data.dict()
    )
    return marqeta_transaction_data


async def prepare_and_insert_delivery_funding_data(
    delivery_funding_repo: DeliveryFundingRepository,
    creator_id: int,
    delivery_id: int,
    swipe_amount: int,
) -> DeliveryFunding:
    data = {
        "created_by_id": creator_id,
        "delivery_id": delivery_id,
        "amount": swipe_amount,
    }
    delivery_funding = await delivery_funding_repo.create(
        creator_id=creator_id, delivery_id=delivery_id, swipe_amount=swipe_amount
    )
    assert delivery_funding.id
    validate_expected_items_in_dict(expected=data, actual=delivery_funding.dict())
    return delivery_funding


async def prepare_and_insert_marqeta_decline_exemption(
    marqeta_decline_exemption_repo: MarqetaDeclineExemptionRepository,
    delivery_id: int,
    creator_id: int,
    amount: int,
    dasher_id: int,
    mid: str,
) -> MarqetaDeclineExemption:
    data = {
        "created_by_id": creator_id,
        "delivery_id": delivery_id,
        "amount": amount,
        "dasher_id": dasher_id,
        "mid": mid,
    }
    decline_exemption = await marqeta_decline_exemption_repo.create(
        creator_id=creator_id,
        delivery_id=delivery_id,
        amount=amount,
        dasher_id=dasher_id,
        mid=mid,
    )
    assert decline_exemption.id
    validate_expected_items_in_dict(expected=data, actual=decline_exemption.dict())
    return decline_exemption


async def prepare_and_insert_card_ownership(
    marqeta_card_ownership_repo: MarqetaCardOwnershipRepository,
    dasher_id: int,
    card_id: str,
) -> MarqetaCardOwnership:
    data = {"card_id": card_id, "dasher_id": dasher_id}
    card_ownership = await marqeta_card_ownership_repo.create_card_ownership(
        dasher_id=dasher_id, card_id=card_id
    )
    assert card_ownership.id
    validate_expected_items_in_dict(expected=data, actual=card_ownership.dict())
    return card_ownership


async def prepare_and_insert_card_acceptor(
    card_acceptor_repo: CardAcceptorRepository,
    mid: str,
    name: str,
    city: str,
    zip_code: str,
    state: str,
    should_be_examined: Optional[bool] = False,
) -> CardAcceptor:
    data = {
        "mid": mid,
        "name": name,
        "city": city,
        "state": state,
        "zip_code": zip_code,
        "is_blacklisted": False,
        "should_be_examined": should_be_examined,
    }
    card_acceptor = await card_acceptor_repo.create_card_acceptor(
        mid=mid,
        name=name,
        city=city,
        zip_code=zip_code,
        state=state,
        should_be_examined=should_be_examined,
    )
    assert card_acceptor.id
    validate_expected_items_in_dict(expected=data, actual=card_acceptor.dict())
    return card_acceptor


async def prepare_and_insert_marqeta_transaction_event(
    transaction_event_repo: MarqetaTransactionEventRepository,
    token: str,
    amount: int,
    metadata: Dict[str, Any],
    raw_type: str,
    ownership_id: int,
    shift_id: Optional[int] = None,
    card_acceptor_id: Optional[int] = None,
) -> MarqetaTransactionEvent:
    data = {
        "token": token,
        "metadata": json.dumps(metadata),
        "raw_type": raw_type,
        "ownership_id": ownership_id,
        "transaction_type": MARQETA_TRANSACTION_EVENT_TRANSACTION_TYPE,
        "shift_id": shift_id,
        "card_acceptor_id": card_acceptor_id,
        "amount": amount,
    }
    transaction_event = await transaction_event_repo.create_transaction_event(
        token=token,
        metadata=metadata,
        raw_type=raw_type,
        ownership_id=ownership_id,
        shift_id=shift_id,
        card_acceptor_id=card_acceptor_id,
        amount=amount,
    )
    assert transaction_event.id
    validate_expected_items_in_dict(expected=data, actual=transaction_event.dict())
    return transaction_event


class FunctionMock(MagicMock):
    async def __call__(self, *args, **kwargs):
        return super(FunctionMock, self).__call__(*args, **kwargs)
