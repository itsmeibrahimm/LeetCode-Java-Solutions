import random
from uuid import uuid4

import pytest
from asynctest import MagicMock
from starlette.status import (
    HTTP_200_OK,
    HTTP_404_NOT_FOUND,
    HTTP_500_INTERNAL_SERVER_ERROR,
)
from starlette.testclient import TestClient

from app.commons.core.errors import MarqetaCannotInactivateCardError
from app.purchasecard.api.card.v0.models import (
    AssociateMarqetaCardRequest,
    UnassociateMarqetaCardRequest,
)
from app.purchasecard.marqeta_external.models import MarqetaProviderCard
from app.purchasecard.test_integration.utils import FakeMarqetaEnvironment


class FunctionMock(MagicMock):
    async def __call__(self, *args, **kwargs):
        return super(FunctionMock, self).__call__(*args, **kwargs)


@pytest.mark.external
class TestUnassociateMarqetaCard:
    @pytest.fixture(autouse=True)
    def setup(self, app_context):
        self.test_marqeta_env = FakeMarqetaEnvironment(app_context.marqeta_client)

    def get_fake_dasher_id(self):
        return random.randint(0, 9999)

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

    def test_unassociate_marqeta_card_success(self, mocker, client: TestClient):
        test_dasher_id, test_card_token = self.setup_test_dasher_and_card_association(
            mocker, client
        )

        request_body = UnassociateMarqetaCardRequest(dasher_id=test_dasher_id)

        response = client.post(
            "/purchasecard/api/v0/marqeta/card/unassociate_marqeta",
            json=request_body.dict(),
        )

        assert response.status_code == HTTP_200_OK

        cardresp = response.json()
        assert cardresp["token"] == test_card_token

    def test_unassociate_marqeta_card_failure_not_found(self, client: TestClient):
        request_body = UnassociateMarqetaCardRequest(dasher_id=10000)

        response = client.post(
            "/purchasecard/api/v0/marqeta/card/unassociate_marqeta",
            json=request_body.dict(),
        )

        assert response.status_code == HTTP_404_NOT_FOUND

    def test_unassociate_marqeta_card_failure_retry(self, mocker, client: TestClient):
        test_dasher_id, test_card_token = self.setup_test_dasher_and_card_association(
            mocker, client
        )
        # mock failed card transition
        from app.purchasecard.core.card.processor import CardProcessor

        self.transition_card = CardProcessor.transition_card

        CardProcessor.transition_card = FunctionMock(  # type: ignore
            side_effect=MarqetaCannotInactivateCardError()
        )

        request_body = UnassociateMarqetaCardRequest(dasher_id=test_dasher_id)

        response = client.post(
            "/purchasecard/api/v0/marqeta/card/unassociate_marqeta",
            json=request_body.dict(),
        )

        assert response.status_code == HTTP_500_INTERNAL_SERVER_ERROR

        CardProcessor.transition_card = self.transition_card  # type: ignore

        response = client.post(
            "/purchasecard/api/v0/marqeta/card/unassociate_marqeta",
            json=request_body.dict(),
        )

        assert response.status_code == HTTP_200_OK

        cardresp = response.json()
        assert cardresp["token"] == test_card_token
