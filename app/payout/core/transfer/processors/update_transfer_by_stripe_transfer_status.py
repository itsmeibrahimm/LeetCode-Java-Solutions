from doordash_python_stats.ddstats import doorstats_global
from stripe.error import StripeError

from app.commons.api.models import DEFAULT_INTERNAL_EXCEPTION, PaymentException
from structlog.stdlib import BoundLogger
from typing import Union, Optional
from app.commons.core.processor import (
    AsyncOperation,
    OperationRequest,
    OperationResponse,
)
from app.commons.providers.stripe.stripe_client import StripeAsyncClient
from app.commons.providers.stripe.stripe_models import StripeRetrievePayoutRequest
from app.payout.constants import UPDATED_INCORRECT_STRIPE_TRANSFER_STATUS
from app.payout.models import TransferStatusCodeType, TransferId
from app.payout.repository.maindb.model.stripe_transfer import (
    StripeTransfer,
    StripeTransferUpdate,
)
from app.payout.repository.maindb.model.transfer import (
    TransferStatus,
    Transfer,
    TransferUpdate,
)
from app.payout.repository.maindb.stripe_transfer import (
    StripeTransferRepositoryInterface,
)
from app.payout.repository.maindb.transfer import TransferRepositoryInterface
from app.commons.providers.stripe import stripe_models as models


class UpdateTransferByStripeTransferStatusResponse(OperationResponse):
    pass


class UpdateTransferByStripeTransferStatusRequest(OperationRequest):
    transfer_id: TransferId


class UpdateTransferByStripeTransferStatus(
    AsyncOperation[
        UpdateTransferByStripeTransferStatusRequest,
        UpdateTransferByStripeTransferStatusResponse,
    ]
):
    """
    Processor to update transfer by stripe_transfer status
    """

    transfer_repo: TransferRepositoryInterface
    stripe_transfer_repo: StripeTransferRepositoryInterface

    def __init__(
        self,
        request: UpdateTransferByStripeTransferStatusRequest,
        *,
        transfer_repo: TransferRepositoryInterface,
        stripe_transfer_repo: StripeTransferRepositoryInterface,
        stripe: StripeAsyncClient,
        logger: BoundLogger = None,
    ):
        super().__init__(request, logger)
        self.request = request
        self.transfer_repo = transfer_repo
        self.stripe_transfer_repo = stripe_transfer_repo
        self.stripe = stripe

    async def _execute(self) -> UpdateTransferByStripeTransferStatusResponse:
        self.logger.info(
            "[monitor_stripe_transfer_status_for_transfer_id_v1] Checking transfer_id",
            transfer_id=self.request.transfer_id,
        )
        transfer = await self.transfer_repo.get_transfer_by_id(
            transfer_id=self.request.transfer_id
        )
        assert transfer, "transfer must be valid with given transfer_id"
        try:
            stripe_transfer = await self.stripe_transfer_repo.get_latest_stripe_transfer_by_transfer_id(
                transfer_id=transfer.id
            )
            if not stripe_transfer:
                return UpdateTransferByStripeTransferStatusResponse()
            updated_stripe_transfer = await self.check_and_sync_stripe_transfer_status(
                stripe_transfer=stripe_transfer
            )
            if updated_stripe_transfer:
                updated_transfer = await self.check_and_sync_transfer_status_with_stripe_transfer(
                    transfer=transfer, stripe_transfer=updated_stripe_transfer
                )
                doorstats_global.incr(UPDATED_INCORRECT_STRIPE_TRANSFER_STATUS)
                self.logger.info(
                    "[monitor_stripe_transfer_status_for_transfer_id_v1] Updated transfer status",
                    transfer_id=updated_transfer.id,
                    previous_transfer_status=transfer.status,
                    updated_transfer_status=updated_transfer.status,
                )
            else:
                # transfer should be in status 'new' right now
                self.logger.info(
                    "[monitor_stripe_transfer_status_for_transfer_id_v1] Transfer stuck in new",
                    transfer_id=transfer.id,
                    transfer_status=transfer.status,
                )
        except Exception:
            self.logger.exception(
                "[monitor_stripe_transfer_status_for_transfer_id_v1] Error checking stripe status for transfer",
                transfer_id=transfer.id,
            )
        self.logger.info(
            "[monitor_stripe_transfer_status_for_transfer_id_v1] Completed syncing transfer status. "
        )
        return UpdateTransferByStripeTransferStatusResponse()

    def _handle_exception(
        self, dep_exec: BaseException
    ) -> Union[PaymentException, UpdateTransferByStripeTransferStatusResponse]:
        raise DEFAULT_INTERNAL_EXCEPTION

    async def check_and_sync_stripe_transfer_status(
        self, stripe_transfer: StripeTransfer
    ) -> Optional[StripeTransfer]:
        """
        Get Stripe payout by stripe id
        :return: Return updated StripeTransfer
        If there is no stripe_id on stripe_transfer, return None to represent that as synced already
        in order to skip further sync the status of transfer
        """

        if not stripe_transfer.stripe_id:
            return None

        try:
            request = StripeRetrievePayoutRequest(
                id=stripe_transfer.stripe_id,
                stripe_account=stripe_transfer.stripe_account_id,
            )
            transfer_of_stripe = await self.stripe.retrieve_payout(
                request=request,
                country=models.CountryCode(stripe_transfer.country_shortname),
            )
            if not transfer_of_stripe.status == stripe_transfer.stripe_status:
                update_request = StripeTransferUpdate(
                    stripe_status=transfer_of_stripe.status
                )
                updated_stripe_transfer = await self.stripe_transfer_repo.update_stripe_transfer_by_id(
                    stripe_transfer_id=stripe_transfer.id, data=update_request
                )
                assert updated_stripe_transfer, "stripe_transfer must exists"
                self.logger.info(
                    "[monitor_stripe_transfer_status_for_transfer_id_v1] Updated stripe_transfer stripe_status",
                    stripe_transfer_id=stripe_transfer.id,
                    previous_stripe_status=stripe_transfer.stripe_status,
                    updated_stripe_status=updated_stripe_transfer.stripe_status,
                )
                return updated_stripe_transfer
            return stripe_transfer
        except StripeError as e:
            error_info = e.json_body.get("error", {})
            stripe_error_message = error_info.get("message")
            stripe_error_type = error_info.get("type")
            stripe_error_code = error_info.get("code")
            self.logger.exception(
                "Error retrieve stripe transfer",
                stripe_id=stripe_transfer.stripe_id,
                stripe_error_message=stripe_error_message,
                stripe_error_code=stripe_error_code,
                stripe_error_type=stripe_error_type,
            )
            raise

    async def check_and_sync_transfer_status_with_stripe_transfer(
        self, transfer: Transfer, stripe_transfer: StripeTransfer
    ) -> Transfer:
        """
        Syncs transfer status with that of gateway specific status and saves if necessary
        :return: updated object
        """
        updated_status = self.determine_transfer_status_with_stripe_transfer(
            transfer=transfer, stripe_transfer=stripe_transfer
        )
        if updated_status != transfer.status:
            status_code_to_update = None
            if updated_status == TransferStatus.FAILED:
                status_code_to_update = (
                    TransferStatusCodeType.ERROR_GATEWAY_ACCOUNT_SETUP
                )
            update_request = TransferUpdate(
                status=updated_status, status_code=status_code_to_update
            )
            updated_transfer = await self.transfer_repo.update_transfer_by_id(
                transfer_id=transfer.id, data=update_request
            )
            assert updated_transfer, "failed to update existing transfer status"
            return updated_transfer
        return transfer

    def determine_transfer_status_with_stripe_transfer(
        self, transfer: Transfer, stripe_transfer: StripeTransfer
    ) -> TransferStatus:
        if transfer.deleted_at:
            return TransferStatus.DELETED

        if transfer.amount == 0 and transfer.submitted_at:
            return TransferStatus.PAID

        return TransferStatus.stripe_status_to_transfer_status(
            stripe_transfer.stripe_status
        )
