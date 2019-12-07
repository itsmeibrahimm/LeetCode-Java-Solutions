import json
import random
from uuid import uuid4

import pytest
from starlette.status import (
    HTTP_200_OK,
    HTTP_400_BAD_REQUEST,
    HTTP_500_INTERNAL_SERVER_ERROR,
)
from starlette.testclient import TestClient

from app.commons.core.errors import MarqetaCannotActivateCardError
from app.purchasecard.api.card.v0.models import AssociateMarqetaCardRequest
from app.purchasecard.marqeta_external.models import MarqetaProviderCard
from app.purchasecard.test_integration.utils import FakeMarqetaEnvironment, FunctionMock


@pytest.mark.external
class TestAssociateMarqetaCard:
    TEST_TOKEN: int = 1234
    TEST_DELIGHT_NUMBER: int = 1234
    TEST_DASHER_ID: int = 1234

    @pytest.fixture(autouse=True)
    def setup(self, app_context):
        self.test_marqeta_env = FakeMarqetaEnvironment(app_context.marqeta_client)

    def get_fake_dasher_id(self):
        return random.randint(0, 999999)

    def test_associate_marqeta_card_success(self, mocker, client: TestClient):
        user_token = self.test_marqeta_env.setup_test_user()
        test_token = str(uuid4())
        card: MarqetaProviderCard = self.test_marqeta_env.setup_test_card_with_token(
            test_token=test_token, user_token=user_token
        )
        assert card

        mocker.patch(
            "app.purchasecard.core.card.processor.CardProcessor._get_card_token",
            return_value=test_token,
        )

        request_body = AssociateMarqetaCardRequest(
            delight_number=self.TEST_TOKEN,
            last4=card.last_four,
            dasher_id=self.TEST_DASHER_ID,
            user_token=card.user_token,
        )

        response = client.post(
            "/purchasecard/api/v0/marqeta/card/associate_marqeta",
            json=request_body.dict(),
        )

        assert response.status_code == HTTP_200_OK
        cardresp = response.json()
        assert cardresp["num_prev_owners"] == 0
        assert cardresp["old_card_relinquished"] is False

    def test_associate_marqeta_card_failure_retry(self, mocker, client: TestClient):
        # mock failed card transition
        from app.purchasecard.core.card.processor import CardProcessor

        self.transition_card = CardProcessor.transition_card

        CardProcessor.transition_card = FunctionMock(  # type: ignore
            side_effect=MarqetaCannotActivateCardError()
        )
        user_token = self.test_marqeta_env.setup_test_user()
        # issue new card
        test_token = str(uuid4())
        card: MarqetaProviderCard = self.test_marqeta_env.setup_test_card_with_token(
            test_token=test_token, user_token=user_token
        )
        assert card

        mocker.patch(
            "app.purchasecard.core.card.processor.CardProcessor._get_card_token",
            return_value=test_token,
        )
        # first try
        request_body = AssociateMarqetaCardRequest(
            delight_number=self.TEST_TOKEN,
            last4=card.last_four,
            dasher_id=self.get_fake_dasher_id(),
            user_token=card.user_token,
        )

        response = client.post(
            "/purchasecard/api/v0/marqeta/card/associate_marqeta",
            json=request_body.dict(),
        )

        assert response.status_code == HTTP_500_INTERNAL_SERVER_ERROR

        CardProcessor.transition_card = self.transition_card  # type: ignore

        # second try
        response = client.post(
            "/purchasecard/api/v0/marqeta/card/associate_marqeta",
            json=request_body.dict(),
        )

        assert response.status_code == HTTP_200_OK

        cardresp = response.json()
        assert cardresp["num_prev_owners"] == 1
        assert cardresp["old_card_relinquished"] is False

    def test_associate_marqeta_card_old_card_relinquished(
        self, mocker, client: TestClient
    ):
        user_token = self.test_marqeta_env.setup_test_user()
        dasher_id = self.get_fake_dasher_id()
        # old card
        test_token = str(uuid4())
        card: MarqetaProviderCard = self.test_marqeta_env.setup_test_card_with_token(
            test_token=test_token, user_token=user_token
        )
        assert card

        mocker.patch(
            "app.purchasecard.core.card.processor.CardProcessor._get_card_token",
            return_value=test_token,
        )

        request_body = AssociateMarqetaCardRequest(
            delight_number=self.TEST_TOKEN,
            last4=card.last_four,
            dasher_id=dasher_id,
            user_token=card.user_token,
        )

        response = client.post(
            "/purchasecard/api/v0/marqeta/card/associate_marqeta",
            json=request_body.dict(),
        )
        assert response.status_code == HTTP_200_OK

        cardresp = response.json()
        assert cardresp["num_prev_owners"] == 0
        assert cardresp["old_card_relinquished"] is False

        # new card
        new_test_token = str(uuid4())
        new_card: MarqetaProviderCard = self.test_marqeta_env.setup_test_card_with_token(
            test_token=new_test_token, user_token=user_token
        )
        assert new_card

        mocker.patch(
            "app.purchasecard.core.card.processor.CardProcessor._get_card_token",
            return_value=new_test_token,
        )

        request_body = AssociateMarqetaCardRequest(
            delight_number=self.TEST_TOKEN,
            last4=new_card.last_four,
            dasher_id=dasher_id,
            user_token=new_card.user_token,
        )

        response = client.post(
            "/purchasecard/api/v0/marqeta/card/associate_marqeta",
            json=request_body.dict(),
        )

        assert response.status_code == HTTP_200_OK

        cardresp = response.json()
        assert cardresp["num_prev_owners"] == 0
        assert cardresp["old_card_relinquished"] is True

    def test_associate_marqeta_card_cannot_move_card_to_new_cardholder(
        self, mocker, client: TestClient
    ):
        old_user_token = self.test_marqeta_env.setup_test_user()

        # issue new card and activate
        test_token = str(uuid4())
        card: MarqetaProviderCard = self.test_marqeta_env.setup_test_card_with_token(
            test_token=test_token, user_token=old_user_token
        )
        assert card
        self.test_marqeta_env.activate_card_with_token(test_token)

        mocker.patch(
            "app.purchasecard.core.card.processor.CardProcessor._get_card_token",
            return_value=test_token,
        )

        new_user_token = self.test_marqeta_env.setup_test_user()
        request_body = AssociateMarqetaCardRequest(
            delight_number=self.TEST_DELIGHT_NUMBER,
            last4=card.last_four,
            dasher_id=self.TEST_DASHER_ID,
            user_token=new_user_token,
        )

        response = client.post(
            "/purchasecard/api/v0/marqeta/card/associate_marqeta",
            json=request_body.dict(),
        )

        assert response.status_code == HTTP_400_BAD_REQUEST

        from app.commons.core.errors import MarqetaErrorCode

        error_code = json.loads(response.content)["error_code"]
        assert (
            error_code
            == MarqetaErrorCode.MARQETA_CANNOT_MOVE_CARD_TO_NEW_CARDHOLDER_ERROR
        )

    def test_associate_marqeta_card_cannot_assign_card(
        self, mocker, client: TestClient
    ):
        prev_owner = self.get_fake_dasher_id()
        user_token = self.test_marqeta_env.setup_test_user()
        # issue new card
        test_token = str(uuid4())
        card: MarqetaProviderCard = self.test_marqeta_env.setup_test_card_with_token(
            test_token=test_token, user_token=user_token
        )
        assert card

        mocker.patch(
            "app.purchasecard.core.card.processor.CardProcessor._get_card_token",
            return_value=test_token,
        )

        request_body = AssociateMarqetaCardRequest(
            delight_number=self.TEST_DELIGHT_NUMBER,
            last4=card.last_four,
            dasher_id=prev_owner,
            user_token=card.user_token,
        )

        response = client.post(
            "/purchasecard/api/v0/marqeta/card/associate_marqeta",
            json=request_body.dict(),
        )

        assert response.status_code == HTTP_200_OK

        new_owner = self.get_fake_dasher_id()
        while new_owner == prev_owner:
            new_owner = self.get_fake_dasher_id()

        request_body = AssociateMarqetaCardRequest(
            delight_number=self.TEST_DELIGHT_NUMBER,
            last4=card.last_four,
            dasher_id=new_owner,
            user_token=card.user_token,
        )

        response = client.post(
            "/purchasecard/api/v0/marqeta/card/associate_marqeta",
            json=request_body.dict(),
        )

        error_code = json.loads(response.content)["error_code"]
        from app.commons.core.errors import MarqetaErrorCode

        assert error_code == MarqetaErrorCode.MARQETA_CANNOT_ASSIGN_CARD_ERROR
