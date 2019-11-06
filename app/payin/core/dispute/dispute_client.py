from datetime import datetime
from typing import Optional, List

from fastapi import Depends
from stripe.error import StripeError
from structlog.stdlib import BoundLogger

from app.commons import tracing
from app.commons.context.app_context import AppContext, get_global_app_context
from app.commons.context.req_context import (
    get_logger_from_req,
    get_stripe_async_client_from_req,
)
from app.commons.core.errors import DBDataError
from app.commons.providers.stripe.stripe_client import StripeAsyncClient
from app.commons.providers.stripe.stripe_models import StripeUpdateDisputeRequest
from app.commons.types import CountryCode
from app.payin.core.dispute.model import Dispute, DisputeChargeMetadata, Evidence
from app.payin.core.dispute.types import DisputeIdType, ReasonType
from app.payin.core.exceptions import DisputeReadError, PayinErrorCode
from app.payin.core.exceptions import DisputeUpdateError
from app.payin.core.payer.payer_client import PayerClient
from app.payin.core.payment_method.model import RawPaymentMethod
from app.payin.core.payment_method.processor import PaymentMethodClient
from app.payin.core.types import PaymentMethodIdType
from app.payin.repository.dispute_repo import (
    DisputeRepository,
    GetStripeDisputeByIdInput,
    GetAllStripeDisputesByPaymentMethodIdInput,
    StripeDisputeDbEntity,
    GetDisputeChargeMetadataInput,
    ConsumerChargeDbEntity,
    GetCumulativeAmountInput,
    GetCumulativeCountInput,
)
from app.payin.repository.dispute_repo import (
    UpdateStripeDisputeWhereInput,
    UpdateStripeDisputeSetInput,
)


@tracing.track_breadcrumb(processor_name="disputes")
class DisputeClient:
    """
    Dispute client wrapper that provides utilities to dispute.
    """

    def __init__(
        self,
        app_ctxt: AppContext = Depends(get_global_app_context),
        log: BoundLogger = Depends(get_logger_from_req),
        dispute_repo: DisputeRepository = Depends(DisputeRepository.get_repository),
        payer_client: PayerClient = Depends(PayerClient),
        payment_method_client: PaymentMethodClient = Depends(PaymentMethodClient),
        stripe_async_client: StripeAsyncClient = Depends(
            get_stripe_async_client_from_req
        ),
    ):
        self.app_ctxt = app_ctxt
        self.log = log
        self.dispute_repo = dispute_repo
        self.payer_client = payer_client
        self.payment_method_client = payment_method_client
        self.VALID_REASONS = [key.value for key in ReasonType]
        self.stripe_async_client = stripe_async_client

    async def get_raw_dispute(
        self, dispute_id: str, dispute_id_type: DisputeIdType
    ) -> Dispute:
        try:
            dispute_entity = await self.dispute_repo.get_dispute_by_dispute_id(
                dispute_input=GetStripeDisputeByIdInput(
                    stripe_dispute_id=dispute_id, dispute_id_type=dispute_id_type
                )
            )
        except DBDataError:
            self.log.exception(
                "[get_raw_dispute] DBDataError while reading db.", dispute_id=dispute_id
            )
            raise DisputeReadError(
                error_code=PayinErrorCode.DISPUTE_READ_DB_ERROR, retryable=False
            )
        if dispute_entity is None:
            self.log.error("[get_raw_dispute] Dispute not found", dispute_id=dispute_id)
            raise DisputeReadError(
                error_code=PayinErrorCode.DISPUTE_NOT_FOUND, retryable=False
            )
        return dispute_entity.to_stripe_dispute()

    async def pgp_submit_dispute_evidence(
        self, dispute_id: str, evidence: Evidence, country: CountryCode
    ):
        try:
            request = StripeUpdateDisputeRequest(sid=dispute_id, evidence=evidence)
            response = await self.stripe_async_client.update_dispute(
                country=country, request=request
            )
        except StripeError:
            self.log.exception("Error updating the stripe dispute")
            raise DisputeUpdateError(
                error_code=PayinErrorCode.DISPUTE_UPDATE_STRIPE_ERROR, retryable=False
            )
        return response

    async def update_raw_dispute_submitted_time(
        self, dd_stripe_dispute_id: str, submitted_at: datetime
    ) -> Dispute:
        try:
            updated_time: datetime = datetime.utcnow()
            updated_dispute_db_entity = await self.dispute_repo.update_dispute_details(
                request_set=UpdateStripeDisputeSetInput(
                    evidence_submitted_at=submitted_at, updated_at=updated_time
                ),
                request_where=UpdateStripeDisputeWhereInput(id=dd_stripe_dispute_id),
            )
        except DBDataError:
            self.log.exception(
                "[update_raw_dispute_submitted_time] DBDataError while reading db.",
                dd_stripe_dispute_id=dd_stripe_dispute_id,
            )
            raise DisputeReadError(
                error_code=PayinErrorCode.DISPUTE_UPDATE_DB_ERROR, retryable=True
            )
        if not updated_dispute_db_entity:
            self.log.warn(
                "[update_raw_dispute_submitted_time] empty data returned from DB after update submitted_at",
                dd_stripe_dispute_id=dd_stripe_dispute_id,
            )
            raise DisputeReadError(
                error_code=PayinErrorCode.DISPUTE_UPDATE_DB_ERROR, retryable=True
            )
        return updated_dispute_db_entity.to_stripe_dispute()

    def validate_reasons(self, reasons):
        invalid_reasons = [
            reason for reason in reasons if reason not in self.VALID_REASONS
        ]
        if len(invalid_reasons) > 0:
            self.log.error(
                "[get_cumulative_count] invalid reasons provided",
                dd_stripe_dispute_id=id,
                invalid_reasons=invalid_reasons,
            )
            raise DisputeReadError(
                error_code=PayinErrorCode.DISPUTE_READ_INVALID_DATA, retryable=False
            )

    async def get_raw_disputes_list(
        self,
        dd_payment_method_id: str = None,
        stripe_payment_method_id: str = None,
        dd_stripe_card_id: int = None,
        dd_consumer_id: int = None,
        start_time: datetime = None,
        reasons: List[str] = None,
    ) -> List[Dispute]:
        # FIXME: code refactory needed here.
        if not (
            dd_payment_method_id
            or stripe_payment_method_id
            or dd_stripe_card_id
            or dd_consumer_id
        ):
            self.log.warn("[list_disputes] No parameters provided")
            raise DisputeReadError(
                error_code=PayinErrorCode.DISPUTE_LIST_NO_PARAMETERS, retryable=False
            )
        # Setting defaults
        dispute_db_entities: List[StripeDisputeDbEntity] = []
        if reasons:
            self.validate_reasons(reasons)
        else:
            reasons = self.VALID_REASONS
        if start_time is None:
            start_time = datetime(1970, 1, 1)  # Defaulting to epoch time
        # Business logic to get disputes list
        if dd_payment_method_id or stripe_payment_method_id:
            payment_method_id: str = ""
            if dd_payment_method_id:
                payment_method_id = dd_payment_method_id
            elif stripe_payment_method_id:
                payment_method_id = stripe_payment_method_id
            raw_payment_method = await self.payment_method_client.get_raw_payment_method_without_payer_auth(
                payment_method_id=payment_method_id,
                payment_method_id_type=PaymentMethodIdType.PAYMENT_METHOD_ID
                if dd_payment_method_id
                else PaymentMethodIdType.STRIPE_PAYMENT_METHOD_ID,
            )
            if raw_payment_method:
                legacy_dd_stripe_card_id = str(
                    raw_payment_method.legacy_dd_stripe_card_id
                )
                if legacy_dd_stripe_card_id:
                    dispute_db_entities = await self.dispute_repo.list_disputes_by_payment_method_id(
                        input=GetAllStripeDisputesByPaymentMethodIdInput(
                            stripe_card_id=int(legacy_dd_stripe_card_id)
                        )
                    )
        elif dd_stripe_card_id:
            try:
                dispute_db_entities = await self.dispute_repo.get_disputes_by_dd_stripe_card_id(
                    cumulative_count_input=GetCumulativeCountInput(
                        stripe_card_id=dd_stripe_card_id,
                        reasons=reasons,
                        start_time=start_time,
                    )
                )
            except DBDataError:
                self.log.error("[get_cumulative_count] DBDataError while reading db.")
                raise DisputeReadError(
                    error_code=PayinErrorCode.DISPUTE_READ_DB_ERROR, retryable=False
                )
        elif dd_consumer_id:
            try:
                stripe_card_ids = await self.payment_method_client.get_stripe_card_ids_for_consumer_id(
                    consumer_id=dd_consumer_id
                )
                dispute_db_entities = await self.dispute_repo.get_disputes_by_dd_consumer_id(
                    cumulative_amount_input=GetCumulativeAmountInput(
                        card_ids=stripe_card_ids, start_time=start_time, reasons=reasons
                    )
                )
            except DBDataError:
                self.log.exception(
                    "[get_cumulative_amount] DBDataError while reading db."
                )
                raise DisputeReadError(
                    error_code=PayinErrorCode.DISPUTE_READ_DB_ERROR, retryable=False
                )
        disputes = [
            dispute_db_entity.to_stripe_dispute()
            for dispute_db_entity in dispute_db_entities
        ]
        return disputes

    async def get_dispute_charge_metadata_object(
        self, dispute_id: str, dispute_id_type: Optional[str] = None
    ) -> DisputeChargeMetadata:
        stripe_dispute_entity: Optional[StripeDisputeDbEntity] = None
        consumer_charge_entity: Optional[ConsumerChargeDbEntity] = None
        try:
            stripe_dispute_entity, consumer_charge_entity = await self.dispute_repo.get_dispute_charge_metadata_attributes(
                input=GetDisputeChargeMetadataInput(
                    id=dispute_id, id_type=dispute_id_type
                )
            )
        except DBDataError:
            self.log.exception(
                "[get_disputes_charge_metadata] DBDataError while reading db."
            )
            raise DisputeReadError(
                error_code=PayinErrorCode.DISPUTE_READ_DB_ERROR, retryable=False
            )
        if stripe_dispute_entity is None:
            self.log.error(
                "[get_dispute_charge_metadata_object] Dispute not found",
                dispute_id=dispute_id,
            )
            raise DisputeReadError(
                error_code=PayinErrorCode.DISPUTE_NOT_FOUND, retryable=False
            )
        if consumer_charge_entity is None:
            self.log.error(
                "[get_dispute_charge_metadata_object] Dispute not found",
                dispute_id=dispute_id,
            )
            raise DisputeReadError(
                error_code=PayinErrorCode.DISPUTE_NO_CONSUMER_CHARGE_FOR_STRIPE_DISPUTE,
                retryable=False,
            )
        raw_pm: RawPaymentMethod = await self.payment_method_client.get_raw_payment_method_without_payer_auth(
            payment_method_id=str(stripe_dispute_entity.stripe_card_id),
            payment_method_id_type=PaymentMethodIdType.DD_STRIPE_CARD_ID,
        )
        dispute_charge_metadata_object = DisputeChargeMetadata(
            dd_order_cart_id=str(consumer_charge_entity.target_id),
            dd_charge_id=str(consumer_charge_entity.id),
            dd_consumer_id=str(consumer_charge_entity.consumer_id),
            stripe_card_id=raw_pm.pgp_payment_method_resource_id,
            stripe_dispute_status=stripe_dispute_entity.status,
            stripe_dispute_reason=stripe_dispute_entity.reason,
        )
        return dispute_charge_metadata_object
