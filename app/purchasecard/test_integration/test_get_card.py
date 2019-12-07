import random
from datetime import datetime
from uuid import uuid4

import pytest
from starlette.status import HTTP_200_OK, HTTP_404_NOT_FOUND
from starlette.testclient import TestClient

from app.commons.core.errors import MarqetaErrorCode
from app.purchasecard.api.card.v0.models import (
    AssociateMarqetaCardRequest,
    GetMarqetaCardRequest,
)
from app.purchasecard.marqeta_external.models import MarqetaProviderCard
from app.purchasecard.models.maindb.marqeta_card_ownership import MarqetaCardOwnership
from app.purchasecard.test_integration.utils import FakeMarqetaEnvironment, FunctionMock


@pytest.mark.external
class TestGetMarqetaCard:
    @pytest.fixture(autouse=True)
    def setup(self, app_context, marqeta_card_ownership_repo):
        self.test_marqeta_env = FakeMarqetaEnvironment(app_context.marqeta_client)

    def get_fake_dasher_id(self):
        return random.randint(0, 9999)

    def get_fake_card_ownership(self, dasher_id):
        return MarqetaCardOwnership(
            id=1234,
            created_at=datetime.utcnow(),
            card_id=str(uuid4()),
            dasher_id=dasher_id,
        )

    def setup_test_dasher_and_card_association(self, mocker, client: TestClient):
        test_dasher_id = self.get_fake_dasher_id()
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
            delight_number=1234,
            last4=card.last_four,
            dasher_id=test_dasher_id,
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

        return test_dasher_id, test_token

    def test_get_card_success(self, mocker, client: TestClient):
        test_dasher_id, test_card_token = self.setup_test_dasher_and_card_association(
            mocker, client
        )

        request_body = GetMarqetaCardRequest(dasher_id=test_dasher_id)

        response = client.get(
            "/purchasecard/api/v0/marqeta/card/{}".format(test_dasher_id),
            json=request_body.dict(),
        )

        assert response.status_code == HTTP_200_OK
        cardresp = response.json()
        assert cardresp["token"] == test_card_token

    def test_card_failure_no_ownership(self, client: TestClient):
        # random test dasher ids are generated between 0~9999, hence no id=10000 should exist in db
        test_dasher_id = 10000
        request_body = GetMarqetaCardRequest(dasher_id=test_dasher_id)

        response = client.get(
            "/purchasecard/api/v0/marqeta/card/{}".format(test_dasher_id),
            json=request_body.dict(),
        )

        assert response.status_code == HTTP_404_NOT_FOUND
        error = response.json()
        assert (
            error["error_code"]
            == MarqetaErrorCode.MARQETA_NO_ACTIVE_CARD_OWNERSHIP_DASHER_ERROR.value
        )

    def test_card_failure_card_not_found(self, client: TestClient):
        test_dasher_id = self.get_fake_dasher_id()
        from app.purchasecard.repository.marqeta_card_ownership import (
            MarqetaCardOwnershipRepository,
        )

        self.get_active_card_ownership_by_dasher_id = (
            MarqetaCardOwnershipRepository.get_active_card_ownership_by_dasher_id
        )
        MarqetaCardOwnershipRepository.get_active_card_ownership_by_dasher_id = FunctionMock(  # type: ignore
            return_value=self.get_fake_card_ownership(test_dasher_id)
        )
        request_body = GetMarqetaCardRequest(dasher_id=test_dasher_id)

        response = client.get(
            "/purchasecard/api/v0/marqeta/card/{}".format(test_dasher_id),
            json=request_body.dict(),
        )

        assert response.status_code == HTTP_404_NOT_FOUND
        error = response.json()
        assert (
            error["error_code"]
            == MarqetaErrorCode.MARQETA_NO_CARD_FOUND_FOR_TOKEN_ERROR.value
        )

        MarqetaCardOwnershipRepository.get_active_card_ownership_by_dasher_id = (  # type: ignore
            self.get_active_card_ownership_by_dasher_id
        )
