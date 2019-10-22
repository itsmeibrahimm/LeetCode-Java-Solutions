from datetime import datetime, timezone
import pytest
from app.commons.database.infra import DB
from app.payout.core.transfer.utils import (
    determine_transfer_status_from_latest_submission,
)
from app.payout.repository.maindb.payment_account import PaymentAccountRepository
from app.payout.repository.maindb.stripe_transfer import StripeTransferRepository
from app.payout.repository.maindb.transfer import TransferRepository
from app.payout.test_integration.utils import (
    prepare_and_insert_transfer,
    prepare_and_insert_stripe_transfer,
)
from app.payout.models import TransferStatusType, TransferMethodType


class TestTransferUtils:
    pytestmark = [pytest.mark.asyncio]

    @pytest.fixture(autouse=True)
    def setup(
        self,
        stripe_transfer_repo: StripeTransferRepository,
        transfer_repo: TransferRepository,
    ):
        self.stripe_transfer_repo = stripe_transfer_repo
        self.transfer_repo = transfer_repo

    @pytest.fixture
    def payment_account_repository(self, payout_maindb: DB) -> PaymentAccountRepository:
        return PaymentAccountRepository(database=payout_maindb)

    @pytest.fixture
    def transfer_repo(self, payout_maindb: DB) -> TransferRepository:
        return TransferRepository(database=payout_maindb)

    @pytest.fixture
    def stripe_transfer_repo(self, payout_maindb: DB) -> StripeTransferRepository:
        return StripeTransferRepository(database=payout_maindb)

    async def test_determine_transfer_status_from_latest_submission_transfer_deleted(
        self
    ):
        transfer = await prepare_and_insert_transfer(
            transfer_repo=self.transfer_repo, deleted_at=datetime.now(timezone.utc)
        )
        status = await determine_transfer_status_from_latest_submission(
            transfer=transfer, stripe_transfer_repo=self.stripe_transfer_repo
        )
        assert status == TransferStatusType.DELETED

    async def test_determine_transfer_status_from_latest_submission_new_transfer(self):
        transfer = await prepare_and_insert_transfer(
            transfer_repo=self.transfer_repo, method=""
        )
        status = await determine_transfer_status_from_latest_submission(
            transfer=transfer, stripe_transfer_repo=self.stripe_transfer_repo
        )
        assert status == TransferStatusType.NEW

    async def test_determine_transfer_status_from_latest_submission_transfer_paid_doordash_pay(
        self
    ):
        transfer = await prepare_and_insert_transfer(
            transfer_repo=self.transfer_repo,
            method=TransferMethodType.DOORDASH_PAY,
            submitted_at=datetime.now(timezone.utc),
        )
        status = await determine_transfer_status_from_latest_submission(
            transfer=transfer, stripe_transfer_repo=self.stripe_transfer_repo
        )
        assert status == TransferStatusType.PAID

    async def test_determine_transfer_status_from_latest_submission_transfer_paid_zero_amount(
        self
    ):
        transfer = await prepare_and_insert_transfer(
            transfer_repo=self.transfer_repo,
            amount=0,
            submitted_at=datetime.now(timezone.utc),
        )
        status = await determine_transfer_status_from_latest_submission(
            transfer=transfer, stripe_transfer_repo=self.stripe_transfer_repo
        )
        assert status == TransferStatusType.PAID

    async def test_determine_transfer_status_from_latest_submission_transfer_paid_non_stripe_method_and_submitted(
        self
    ):
        transfer = await prepare_and_insert_transfer(
            transfer_repo=self.transfer_repo,
            method=TransferMethodType.CHECK,
            submitted_at=datetime.now(timezone.utc),
        )
        status = await determine_transfer_status_from_latest_submission(
            transfer=transfer, stripe_transfer_repo=self.stripe_transfer_repo
        )
        assert status == TransferStatusType.PAID

    async def test_determine_transfer_status_from_latest_submission_transfer_paid_non_stripe_method_not_submitted(
        self
    ):
        transfer = await prepare_and_insert_transfer(
            transfer_repo=self.transfer_repo, method=TransferMethodType.CHECK
        )
        status = await determine_transfer_status_from_latest_submission(
            transfer=transfer, stripe_transfer_repo=self.stripe_transfer_repo
        )
        assert status == TransferStatusType.NEW

    async def test_determine_transfer_status_from_latest_submission_no_stripe_transfer(
        self
    ):
        transfer = await prepare_and_insert_transfer(transfer_repo=self.transfer_repo)
        status = await determine_transfer_status_from_latest_submission(
            transfer=transfer, stripe_transfer_repo=self.stripe_transfer_repo
        )
        assert status == TransferStatusType.NEW

    async def test_determine_transfer_status_from_latest_submission_pending_stripe_transfer(
        self
    ):
        transfer = await prepare_and_insert_transfer(transfer_repo=self.transfer_repo)
        await prepare_and_insert_stripe_transfer(
            stripe_transfer_repo=self.stripe_transfer_repo,
            transfer_id=transfer.id,
            stripe_status="pending",
        )
        status = await determine_transfer_status_from_latest_submission(
            transfer=transfer, stripe_transfer_repo=self.stripe_transfer_repo
        )
        assert status == TransferStatusType.PENDING

    async def test_determine_transfer_status_from_latest_submission_invalid_status_stripe_transfer(
        self
    ):
        transfer = await prepare_and_insert_transfer(transfer_repo=self.transfer_repo)
        await prepare_and_insert_stripe_transfer(
            stripe_transfer_repo=self.stripe_transfer_repo,
            transfer_id=transfer.id,
            stripe_status="yay",
        )
        assert not await determine_transfer_status_from_latest_submission(
            transfer=transfer, stripe_transfer_repo=self.stripe_transfer_repo
        )
