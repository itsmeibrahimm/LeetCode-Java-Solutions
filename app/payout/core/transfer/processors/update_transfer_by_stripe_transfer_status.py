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
from app.payout.core.transfer.utils import (
    determine_transfer_status_from_latest_submission,
)
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
            previous_stripe_status = stripe_transfer.stripe_status
            new_transfer_status = TransferStatus.stripe_status_to_transfer_status(
                stripe_transfer.stripe_status
            )
            if (
                await self.sync_stripe_status(stripe_transfer=stripe_transfer)
                or transfer.status != new_transfer_status
            ):
                self.logger.warning(
                    "[monitor_stripe_transfer_status_for_transfer_id_v1] updating incorrect stripe transfer status for transfer",
                    transfer_id=transfer.id,
                    transfer_status=transfer.status,
                    previous_stripe_status=previous_stripe_status,
                    new_transfer_status=new_transfer_status,
                    new_stripe_transfer_status=stripe_transfer.stripe_status,
                )
                await self.update_transfer_status_from_latest_submission(
                    transfer=transfer
                )
        except Exception:
            self.logger.exception(
                "[monitor_stripe_transfer_status_for_transfer_id_v1] Error checking stripe status for transfer",
                transfer_id=transfer.id,
            )
        # todo: investigate on how to do doorstats.incr here
        self.logger.info(
            "[monitor_stripe_transfer_status_for_transfer_id_v1] Completed checking chunk"
        )
        return UpdateTransferByStripeTransferStatusResponse()

    def _handle_exception(
        self, dep_exec: BaseException
    ) -> Union[PaymentException, UpdateTransferByStripeTransferStatusResponse]:
        raise DEFAULT_INTERNAL_EXCEPTION

    async def sync_stripe_status(self, stripe_transfer: StripeTransfer) -> bool:
        """
        Retrieve latest Stripe Transfer and sync up the status
        """
        transfer_of_stripe = await self.get_stripe_transfer(stripe_transfer)
        if transfer_of_stripe is None:
            return False
        is_changed = await self._sync_with_stripe_transfer(
            stripe_transfer, transfer_of_stripe
        )
        return is_changed

    async def get_stripe_transfer(
        self, stripe_transfer: StripeTransfer
    ) -> Optional[models.Payout]:
        """
        Get Stripe payout by stripe id
        :return: None if stripe transfer doesn't have stripe id; else Stripe payout from Stripe
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
            return transfer_of_stripe
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

    async def _sync_with_stripe_transfer(
        self, stripe_transfer: StripeTransfer, transfer_of_stripe: models.Payout
    ) -> bool:
        is_changed = stripe_transfer.stripe_status != transfer_of_stripe.status
        update_request = StripeTransferUpdate(stripe_status=transfer_of_stripe.status)
        await self.stripe_transfer_repo.update_stripe_transfer_by_id(
            stripe_transfer_id=stripe_transfer.id, data=update_request
        )
        return is_changed

    async def update_transfer_status_from_latest_submission(self, transfer: Transfer):
        """
        Syncs transfer status with that of gateway specific status and saves if necessary
        :return: updated object
        """
        updated_status = await determine_transfer_status_from_latest_submission(
            transfer=transfer, stripe_transfer_repo=self.stripe_transfer_repo
        )
        if updated_status != transfer.status:
            status_code_to_update = None
            if transfer.method == "stripe" and updated_status == TransferStatus.FAILED:
                status_code_to_update = (
                    TransferStatusCodeType.ERROR_GATEWAY_ACCOUNT_SETUP
                )
            update_request = TransferUpdate(
                status=updated_status, status_code=status_code_to_update
            )
            await self.transfer_repo.update_transfer_by_id(
                transfer_id=transfer.id, data=update_request
            )
