from datetime import datetime
from typing import Optional, List, Union

from fastapi import Depends
from psycopg2._psycopg import DataError
from stripe.error import StripeError
from structlog.stdlib import BoundLogger

from app.commons import tracing
from app.commons.context.app_context import AppContext, get_global_app_context
from app.commons.context.req_context import get_logger_from_req
from app.payin.core.dispute.model import (
    Dispute,
    DisputeList,
    DisputeChargeMetadata,
    Evidence,
)
from app.commons.providers.stripe.stripe_models import UpdateStripeDispute
from app.payin.core.dispute.types import DisputeIdType, ReasonType
from app.payin.core.exceptions import (
    DisputeReadError,
    PayinErrorCode,
    PaymentMethodReadError,
)
from app.payin.core.exceptions import DisputeUpdateError
from app.payin.core.payer.model import RawPayer
from app.payin.core.payer.processor import PayerClient
from app.payin.core.payment_method.processor import PaymentMethodClient
from app.payin.core.types import PaymentMethodIdType
from app.payin.repository.dispute_repo import (
    DisputeRepository,
    GetStripeDisputeByIdInput,
    GetAllStripeDisputesByPayerIdInput,
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
    ):
        self.app_ctxt = app_ctxt
        self.log = log
        self.dispute_repo = dispute_repo
        self.payer_client = payer_client
        self.payment_method_client = payment_method_client
        self.VALID_REASONS = [key.value for key in ReasonType]

    async def get_raw_dispute(
        self, dispute_id: str, dispute_id_type: DisputeIdType
    ) -> Dispute:
        try:
            dispute_entity = await self.dispute_repo.get_dispute_by_dispute_id(
                dispute_input=GetStripeDisputeByIdInput(
                    stripe_dispute_id=dispute_id, dispute_id_type=dispute_id_type
                )
            )
        except DataError as e:
            self.log.error(
                f"[get_raw_dispute][{dispute_id} DataError while reading db. {e}"
            )
            raise DisputeReadError(
                error_code=PayinErrorCode.DISPUTE_READ_DB_ERROR, retryable=False
            )
        if dispute_entity is None:
            self.log.error("[get_raw_dispute] Dispute not found:[%s]", dispute_id)
            raise DisputeReadError(
                error_code=PayinErrorCode.DISPUTE_NOT_FOUND, retryable=False
            )
        return dispute_entity.to_stripe_dispute()

    async def pgp_submit_dispute_evidence(self, dispute_id: str, evidence: Evidence):
        try:
            request = UpdateStripeDispute(sid=dispute_id, evidence=evidence)
            response = await self.app_ctxt.stripe.update_stripe_dispute(request=request)
        except StripeError as e:
            self.log.error(f"Error updating the stripe dispute: {e}")
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
        except DataError as e:
            self.log.error(
                f"[update_raw_dispute_submitted_time][{dd_stripe_dispute_id}] DataError while reading db. {e}"
            )
            raise DisputeReadError(
                error_code=PayinErrorCode.DISPUTE_UPDATE_DB_ERROR, retryable=True
            )
        if not updated_dispute_db_entity:
            self.log.warn(
                f"[update_raw_dispute_submitted_time][{dd_stripe_dispute_id}] error. empty data returned from DB after update submitted_at"
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
                f"[get_cumulative_count][{id}] invalid reasons provided:[{invalid_reasons}]"
            )
            raise DisputeReadError(
                error_code=PayinErrorCode.DISPUTE_READ_INVALID_DATA, retryable=False
            )

    async def get_raw_disputes_list(
        self,
        dd_payment_method_id: str = None,
        stripe_payment_method_id: str = None,
        dd_stripe_card_id: int = None,
        dd_payer_id: str = None,
        stripe_customer_id: str = None,
        dd_consumer_id: int = None,
        start_time: datetime = None,
        reasons: List[str] = None,
    ) -> List[Dispute]:
        # FIXME: code refactory needed here.
        if not (
            dd_payment_method_id
            or stripe_payment_method_id
            or dd_stripe_card_id
            or dd_payer_id
            or stripe_customer_id
            or dd_consumer_id
        ):
            self.log.warn(f"[list_disputes] No parameters provided")
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
                legacy_dd_stripe_card_id = raw_payment_method.legacy_dd_stripe_card_id()
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
            except DataError as e:
                self.log.error(
                    f"[get_cumulative_count][{id} DataError while reading db. {e}"
                )
                raise DisputeReadError(
                    error_code=PayinErrorCode.DISPUTE_READ_DB_ERROR, retryable=False
                )
        elif dd_payer_id or stripe_customer_id:
            stripe_id: Optional[str] = None
            if stripe_customer_id:
                stripe_id = stripe_customer_id
            else:
                raw_payer_object: RawPayer = await self.payer_client.get_raw_payer(
                    payer_id=Union[dd_payer_id, str]
                )
                stripe_id = raw_payer_object.pgp_customer_id()
            if not stripe_id:
                self.log.error(
                    f"[list_disputes_client] No payer found for the dd_payer_id/stripe_customer_id"
                )
                raise PaymentMethodReadError(
                    error_code=PayinErrorCode.DISPUTE_NO_PAYER_FOR_PAYER_ID,
                    retryable=False,
                )
            try:
                stripe_card_ids = await self.payment_method_client.get_dd_stripe_card_ids_by_stripe_customer_id(
                    stripe_customer_id=stripe_id
                )
                dispute_db_entities = await self.dispute_repo.list_disputes_by_payer_id(
                    input=GetAllStripeDisputesByPayerIdInput(
                        stripe_card_ids=stripe_card_ids
                    )
                )
            except DataError as e:
                self.log.error(f"[get_disputes_list] DataError while reading db. {e}")
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
            except DataError as e:
                self.log.error(
                    f"[get_cumulative_amount][{id} DataError while reading db. {e}"
                )
                raise DisputeReadError(
                    error_code=PayinErrorCode.DISPUTE_READ_DB_ERROR, retryable=False
                )
        disputes = [
            dispute_db_entity.to_stripe_dispute()
            for dispute_db_entity in dispute_db_entities
        ]
        return disputes

    async def get_stripe_card_stripe_id(self, id: int):
        stripe_card_stripe_id = await self.payment_method_client.get_stripe_card_id_by_id(
            id=id
        )
        if stripe_card_stripe_id is None:
            self.log.warn(
                "[get_dispute_charge_metadata] No stripe card associated with the dispute"
            )
            raise DisputeReadError(
                error_code=PayinErrorCode.DISPUTE_NO_STRIPE_CARD_FOR_STRIPE_ID,
                retryable=False,
            )
        return stripe_card_stripe_id

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
        except DataError as e:
            self.log.error(
                f"[get_disputes_charge_metadata] DataError while reading db. {e}"
            )
            raise DisputeReadError(
                error_code=PayinErrorCode.DISPUTE_READ_DB_ERROR, retryable=False
            )
        if stripe_dispute_entity is None:
            self.log.error(
                "[get_dispute_charge_metadata_object] Dispute not found:[%s]",
                dispute_id,
            )
            raise DisputeReadError(
                error_code=PayinErrorCode.DISPUTE_NOT_FOUND, retryable=False
            )
        if consumer_charge_entity is None:
            self.log.error(
                "[get_dispute_charge_metadata_object] Dispute not found:[%s]",
                dispute_id,
            )
            raise DisputeReadError(
                error_code=PayinErrorCode.DISPUTE_NO_CONSUMER_CHARGE_FOR_STRIPE_DISPUTE,
                retryable=False,
            )
        stripe_card_id = await self.payment_method_client.get_stripe_card_id_by_id(
            id=stripe_dispute_entity.stripe_card_id
        )
        dispute_charge_metadata_object = DisputeChargeMetadata(
            dd_order_cart_id=str(consumer_charge_entity.target_id),
            dd_charge_id=str(consumer_charge_entity.id),
            dd_consumer_id=str(consumer_charge_entity.consumer_id),
            stripe_card_id=stripe_card_id,
            stripe_dispute_status=stripe_dispute_entity.status,
            stripe_dispute_reason=stripe_dispute_entity.reason,
        )
        return dispute_charge_metadata_object


class DisputeProcessor:
    def __init__(
        self,
        dispute_client: DisputeClient = Depends(DisputeClient),
        log: BoundLogger = Depends(get_logger_from_req),
    ):
        self.dispute_client = dispute_client
        self.log = log

    async def get_dispute(self, dd_stripe_dispute_id: str):
        """
        Retrieve dispute object by dd_stripe_dispute_id.

        :param dd_stripe_dispute_id: [string] integer id of MainDB.stripe_dispute.id
        :return: Dispute object
        """

        self.log.info(f"[get_dispute] dispute_id:{dd_stripe_dispute_id}")
        dispute = await self.dispute_client.get_raw_dispute(
            dispute_id=dd_stripe_dispute_id,
            dispute_id_type=DisputeIdType.DD_STRIPE_DISPUTE_ID,
        )
        return dispute

    async def submit_dispute_evidence(self, stripe_dispute_id: str, evidence: Evidence):
        # Step 1: validate existence of dispute object from DB.
        dispute: Dispute = await self.dispute_client.get_raw_dispute(
            dispute_id=stripe_dispute_id,
            dispute_id_type=DisputeIdType.STRIPE_DISPUTE_ID,
        )

        # Step 2: submit evidence to Payment Provider.
        await self.dispute_client.pgp_submit_dispute_evidence(
            dispute_id=dispute.stripe_dispute_id, evidence=evidence
        )
        submitted_at: datetime = datetime.utcnow()

        # Step 3: update both submitted_at and updated_at
        updated_dispute = await self.dispute_client.update_raw_dispute_submitted_time(
            dd_stripe_dispute_id=dispute.stripe_dispute_id, submitted_at=submitted_at
        )

        return updated_dispute

    async def list_disputes(
        self,
        dd_payment_method_id: str = None,
        stripe_payment_method_id: str = None,
        dd_stripe_card_id: int = None,
        dd_payer_id: str = None,
        stripe_customer_id: str = None,
        dd_consumer_id: int = None,
        start_time: datetime = None,
        reasons: List[str] = None,
        distinct: bool = False,
    ) -> DisputeList:
        """
        Retrieve list of DoorDash dispute

        :param  dd_payment_method_id: [string] DoorDash payment method id
        :param stripe_payment_method_id: [string] Stripe payment method id
        :param dd_stripe_card_id: [int] Primary key in Stripe Card table
        :param dd_payer_id: [string] DoorDash payer id
        :param stripe_customer_id: [string] Stripe customer id
        :param dd_consumer_id: [int]: Primary key in Consumer table
        :param start_time: [datetime] Start date for disputes.Default will be the epoch time
        :param reasons: List[str] List of reasons for dispute.
        :param distinct: [bool] Gives count of distinct disputes according to charge id. Defaults to False
        :return: ListDispute Object
        """
        # FIXME: code refactory needed here.
        if not (
            dd_payment_method_id
            or stripe_payment_method_id
            or dd_stripe_card_id
            or dd_payer_id
            or stripe_customer_id
            or dd_consumer_id
        ):
            self.log.warn(f"[list_disputes] No parameters provided")
            raise DisputeReadError(
                error_code=PayinErrorCode.DISPUTE_LIST_NO_PARAMETERS, retryable=False
            )

        disputes_list: List[Dispute] = await self.dispute_client.get_raw_disputes_list(
            dd_payment_method_id=dd_payment_method_id,
            stripe_payment_method_id=stripe_payment_method_id,
            dd_stripe_card_id=dd_stripe_card_id,
            dd_payer_id=dd_payer_id,
            stripe_customer_id=stripe_customer_id,
            dd_consumer_id=dd_consumer_id,
            start_time=start_time,
            reasons=reasons,
        )

        count: int = 0
        if distinct:
            count = len(set([dispute.stripe_charge_id for dispute in disputes_list]))
        else:
            count = len(disputes_list)
        return DisputeList(
            count=count,
            has_more=False,  # Currently default to False. Returning all the disputes for a query
            total_amount=sum([dispute.amount for dispute in disputes_list]),
            data=disputes_list,
        )

    async def get_dispute_charge_metadata(
        self, dispute_id: str, dispute_id_type: DisputeIdType
    ) -> DisputeChargeMetadata:
        """
        Retrieve charge metadata for a dispute object

        :param dispute_id: [string] id for dispute in dispute table
        :param dispute_id_type: [string] identify the type of id for the dispute.
                Valid values include "dd_stripe_dispute_id", "stripe_dispute_id" (default is "stripe_dispute_id")
        :return: DisputeMetadata object
        """
        return await self.dispute_client.get_dispute_charge_metadata_object(
            dispute_id=dispute_id, dispute_id_type=dispute_id_type
        )
