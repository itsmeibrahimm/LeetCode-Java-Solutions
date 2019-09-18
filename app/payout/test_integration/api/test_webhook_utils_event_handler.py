import pytest
from datetime import datetime, timezone
from unittest import mock

from app.commons.database.infra import DB
from app.payout.repository.bankdb.model.stripe_payout_request import (
    StripePayoutRequestCreate,
)
from app.payout.repository.bankdb.stripe_payout_request import (
    StripePayoutRequestRepository,
)
from app.payout.repository.bankdb.payout import PayoutRepository
from app.payout.repository.maindb.transfer import TransferRepository
from app.payout.repository.maindb.stripe_transfer import StripeTransferRepository
from app.payout.repository.bankdb.model.payout import PayoutCreate
from app.payout.repository.maindb.model.transfer import TransferCreate
from app.payout.repository.maindb.model.stripe_transfer import StripeTransferCreate
from app.payout.api.webhook.utils.event_handler import (
    _handle_stripe_instant_transfer_event,
    _handle_stripe_transfer_event,
)
from app.commons.providers.dsj_client import DSJClient
from structlog.stdlib import BoundLogger


class TestWebhookUtilsEventHandler:
    pytestmark = [pytest.mark.asyncio]

    @pytest.fixture
    def stripe_payout_request_repo(
        self, payout_bankdb: DB
    ) -> StripePayoutRequestRepository:
        return StripePayoutRequestRepository(database=payout_bankdb)

    @pytest.fixture
    def payout_repo(self, payout_bankdb: DB) -> PayoutRepository:
        return PayoutRepository(database=payout_bankdb)

    @pytest.fixture
    def transfer_repo(self, payout_maindb: DB) -> TransferRepository:
        return TransferRepository(database=payout_maindb)

    @pytest.fixture
    def stripe_transfer_repo(self, payout_maindb: DB) -> StripeTransferRepository:
        return StripeTransferRepository(database=payout_maindb)

    @pytest.fixture
    def dsj_client(self, mocker) -> DSJClient:
        # return DSJClient(
        #     {
        #         "base_url": app_config.DSJ_API_BASE_URL,
        #         "email": app_config.DSJ_API_USER_EMAIL.value,
        #         "password": app_config.DSJ_API_USER_PASSWORD.value,
        #         "jwt_token_ttl": app_config.DSJ_API_JWT_TOKEN_TTL,
        #     }
        # )

        # mock out DSJ for now until we can run real integration test with test data
        async def _no_op():
            pass

        mock_dsj = mocker.patch("app.commons.providers.dsj_client.DSJClient")
        mock_dsj.post.return_value = _no_op()
        return mock_dsj

    @pytest.fixture
    def log(self) -> BoundLogger:
        from unittest.mock import MagicMock

        bl = BoundLogger(None, None, None)
        bl.info = MagicMock(return_value=None)
        return bl

    @pytest.mark.asyncio
    async def test__handle_stripe_instant_transfer_event(
        self,
        payout_repo: PayoutRepository,
        stripe_payout_request_repo: StripePayoutRequestRepository,
        dsj_client: DSJClient,
    ):
        ts_utc = datetime.now(timezone.utc)
        payout_data = PayoutCreate(
            amount=1000,
            payment_account_id=123,
            status="new",
            currency="USD",
            fee=199,
            type="instant",
            created_at=ts_utc,
            updated_at=ts_utc,
            idempotency_key="payout-idempotency-key-001",
            payout_method_id=1,
            transaction_ids=[1, 2, 3],
            token="payout-test-token",
            fee_transaction_id=10,
            error=None,
        )

        payout_obj = await payout_repo.create_payout(payout_data)
        assert payout_obj.id, "payout is created"

        stripe_payout_request_data = StripePayoutRequestCreate(
            payout_id=payout_obj.id,
            idempotency_key=f"stripe-payout-request-idempotency-key-{payout_obj.id}",
            payout_method_id=1,
            created_at=ts_utc,
            updated_at=ts_utc,
            status="new",
            stripe_payout_id=f"tr_00000000000000_{payout_obj.id}",
            stripe_account_id="cus_xxxx_1",
        )

        stripe_payout_request_obj = await stripe_payout_request_repo.create_stripe_payout_request(
            stripe_payout_request_data
        )
        assert stripe_payout_request_obj.id, "stripe payout request is created"
        assert (
            stripe_payout_request_obj
            == await stripe_payout_request_repo.get_stripe_payout_request_by_payout_id(
                stripe_payout_request_obj.payout_id
            )
        ), "retrieved stripe payout request matches"

        event = {
            "created": 1326853478,
            "id": "evt_00000000000000",
            "type": "transfer.created",
            "object": "event",
            "api_version": "2019-05-16",
            "data": {
                "object": {
                    "id": f"tr_00000000000000_{payout_obj.id}",
                    "status": "pending",
                    "method": "instant",
                }
            },
        }

        await _handle_stripe_instant_transfer_event(
            event,
            "US",
            i_payouts=payout_repo,
            i_stripe_payout_requests=stripe_payout_request_repo,
            dsj_client=dsj_client,
        )

        updated_payout_obj = await payout_repo.get_payout_by_id(payout_obj.id)

        assert updated_payout_obj, "Fetch update payout"
        assert (
            updated_payout_obj.status == "pending"
        ), "Payout status updated via webhook"

        updated_stripe_payout_request_obj = await stripe_payout_request_repo.get_stripe_payout_request_by_payout_id(
            payout_obj.id
        )
        assert updated_stripe_payout_request_obj, "Fetch update stripe payout request"
        assert (
            updated_stripe_payout_request_obj.status == "pending"
        ), "Stripe Payout Request status updated via webhook"

    @pytest.mark.asyncio
    async def test__handle_stripe_transfer_event(
        self,
        transfer_repo: TransferRepository,
        stripe_transfer_repo: StripeTransferRepository,
        dsj_client: DSJClient,
        log: BoundLogger,
    ):
        with mock.patch(
            "app.payout.core.feature_flags.handle_stripe_transfer_event_enabled",
            return_value=True,
        ):
            transfer_data = TransferCreate(
                subtotal=1000, amount=1000, method="stripe", adjustments=""
            )

            transfer_obj = await transfer_repo.create_transfer(transfer_data)
            assert transfer_obj.id, "transfer is created"

            dummy_stripe_id = f"tr_00000000000000_{transfer_obj.id}"

            stripe_transfer_data = StripeTransferCreate(
                transfer_id=transfer_obj.id,
                stripe_status="pending",
                stripe_id=dummy_stripe_id,
            )

            stripe_transfer_obj = await stripe_transfer_repo.create_stripe_transfer(
                stripe_transfer_data
            )
            assert stripe_transfer_obj.id, "stripe transfer is created"
            assert (
                stripe_transfer_obj
                == await stripe_transfer_repo.get_stripe_transfer_by_id(
                    stripe_transfer_obj.id
                )
            ), "retrieved stripe transfer matches"

            event = {
                "created": 1326853478,
                "id": "evt_00000000000000",
                "type": "transfer.paid",
                "object": "event",
                "api_version": "2019-05-16",
                "data": {
                    "object": {
                        "id": dummy_stripe_id,
                        "status": "paid",
                        "method": "standard",
                    }
                },
            }

            await _handle_stripe_transfer_event(
                event,
                "US",
                i_transfers=transfer_repo,
                i_stripe_transfers=stripe_transfer_repo,
                dsj_client=dsj_client,
                log=log,
            )

            updated_stripe_transfer_obj = await stripe_transfer_repo.get_stripe_transfer_by_id(
                stripe_transfer_obj.id
            )

            assert updated_stripe_transfer_obj, "Fetch update stripe transfer"
            assert (
                updated_stripe_transfer_obj.stripe_status == "paid"
            ), "stripe transfer status updated via webhook"

            updated_transfer_obj = await transfer_repo.get_transfer_by_id(
                transfer_obj.id
            )
            assert updated_transfer_obj, "Fetch update transfer"
            assert (
                updated_transfer_obj.status == "paid"
            ), "Transfer status updated via webhook"

        with mock.patch(
            "app.payout.core.feature_flags.handle_stripe_transfer_event_enabled",
            return_value=False,
        ):
            transfer_data = TransferCreate(
                subtotal=1000, amount=1000, method="stripe", adjustments=""
            )
            transfer_obj = await transfer_repo.create_transfer(transfer_data)
            assert transfer_obj.id, "transfer is created"
            dummy_stripe_id = f"tr_00000000000000_{transfer_obj.id}"

            event = {
                "created": 1326853478,
                "id": "evt_00000000000000",
                "type": "transfer.paid",
                "object": "event",
                "api_version": "2019-05-16",
                "data": {
                    "object": {
                        "id": dummy_stripe_id,
                        "status": "paid",
                        "method": "standard",
                    }
                },
            }

            await _handle_stripe_transfer_event(
                event,
                "US",
                i_transfers=transfer_repo,
                i_stripe_transfers=stripe_transfer_repo,
                dsj_client=dsj_client,
                log=log,
            )

            log.info.assert_called_once_with(
                "handle_stripe_transfer_event_enabled is off, skipping..."
            )
