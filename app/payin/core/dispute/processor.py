from typing import Optional, List

from fastapi import Depends
from psycopg2._psycopg import DataError
from structlog.stdlib import BoundLogger

from app.commons import tracing
from app.commons.context.app_context import AppContext, get_global_app_context
from app.commons.context.req_context import get_logger_from_req
from app.commons.error.errors import PaymentError
from app.payin.core.dispute.model import Dispute
from app.payin.core.dispute.types import DISPUTE_ID_TYPE
from app.payin.core.exceptions import (
    DisputeReadError,
    PayinErrorCode,
    PaymentMethodReadError,
)
from app.payin.core.payer.model import RawPayer
from app.payin.core.payer.processor import PayerClient
from app.payin.core.payment_method.processor import PaymentMethodClient
from app.payin.core.types import DisputePayerIdType
from app.payin.repository.dispute_repo import (
    DisputeRepository,
    GetStripeDisputeByIdInput,
    GetAllStripeDisputesByPayerIdInput,
    GetAllStripeDisputesByPaymentMethodIdInput,
    StripeDisputeDbEntity,
)


@tracing.set_processor_name("disputes", only_trackable=False)
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

    async def get_dispute_object(
        self, dispute_id: str, dispute_id_type: Optional[str] = None
    ) -> Dispute:
        if dispute_id_type and dispute_id_type not in (
            DISPUTE_ID_TYPE.PGP_DISPUTE_ID,
            DISPUTE_ID_TYPE.STRIPE_DISPUTE_ID,
        ):
            self.log.error(
                f"[get_dispute_object][{dispute_id}] invalid dispute_id_type:[{dispute_id_type}]"
            )
            raise DisputeReadError(
                error_code=PayinErrorCode.DISPUTE_READ_INVALID_DATA, retryable=False
            )
        try:
            dispute_entity = await self.dispute_repo.get_dispute_by_dispute_id(
                dispute_input=GetStripeDisputeByIdInput(
                    stripe_dispute_id=dispute_id, dispute_id_type=dispute_id_type
                )
            )
        except DataError as e:
            self.log.error(
                f"[get_dispute_entity][{dispute_id} DataError while reading db. {e}"
            )
            raise DisputeReadError(
                error_code=PayinErrorCode.DISPUTE_READ_DB_ERROR, retryable=False
            )
        if dispute_entity is None:
            self.log.error("[get_dispute_entity] Dispute not found:[%s]", dispute_id)
            raise DisputeReadError(
                error_code=PayinErrorCode.DISPUTE_NOT_FOUND, retryable=False
            )
        return dispute_entity.to_stripe_dispute()

    async def get_disputes_list(
        self,
        payer_id: str = None,
        payer_id_type: str = None,
        payment_method_id: str = None,
        payment_method_id_type: str = None,
    ) -> List[Dispute]:
        dispute_db_entities: List[StripeDisputeDbEntity] = []
        if not (payer_id or payment_method_id):
            self.log.warn(f"[list_disputes] No parameters provided")
            raise DisputeReadError(
                error_code=PayinErrorCode.DISPUTE_LIST_NO_PARAMETERS, retryable=False
            )
        if not (payer_id_type or payment_method_id_type):
            self.log.warn(f"[list_disputes] No parameters provided")
            raise DisputeReadError(
                error_code=PayinErrorCode.DISPUTE_LIST_NO_ID_PARAMETERS, retryable=False
            )
        if payment_method_id:
            if payer_id:
                try:
                    raw_payment_method = await self.payment_method_client.get_raw_payment_method(
                        payer_id=payer_id,
                        payer_id_type=payer_id_type,
                        payment_method_id=payment_method_id,
                        payment_method_id_type=payment_method_id_type,
                    )
                except PaymentError as e:
                    self.log.error(
                        f"[list_disputes_client] Payment method not associated to payer"
                    )
                    raise e
            else:
                raw_payment_method = await self.payment_method_client.get_raw_payment_method_no_payer_auth(
                    payment_method_id=payment_method_id,
                    payment_method_id_type=payment_method_id_type,
                )
            legacy_dd_stripe_card_id = raw_payment_method.legacy_dd_stripe_card_id()
            assert legacy_dd_stripe_card_id
            stripe_card_id = int(legacy_dd_stripe_card_id)
            dispute_db_entities = await self.dispute_repo.list_disputes_by_payment_method_id(
                input=GetAllStripeDisputesByPaymentMethodIdInput(
                    stripe_card_id=stripe_card_id
                )
            )
        elif payer_id:
            if payer_id_type is DisputePayerIdType.STRIPE_CUSTOMER_ID:
                stripe_customer_id = payer_id
            else:
                raw_payer_object: RawPayer = await self.payer_client.get_raw_payer(
                    payer_id=payer_id, payer_id_type=payer_id_type
                )
                pgp_customer_id = raw_payer_object.pgp_customer_id()
                assert pgp_customer_id
                stripe_customer_id = pgp_customer_id
            if stripe_customer_id is None:
                self.log.error(
                    f"[list_disputes_client] No payer found for the payer_id"
                )
                raise PaymentMethodReadError(
                    error_code=PayinErrorCode.DISPUTE_NO_PAYER_FOR_PAYER_ID,
                    retryable=False,
                )
            try:
                stripe_card_ids = await self.payment_method_client.get_dd_stripe_card_ids_by_stripe_customer_id(
                    stripe_customer_id=stripe_customer_id
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
        disputes = [
            dispute_db_entity.to_stripe_dispute()
            for dispute_db_entity in dispute_db_entities
        ]
        return disputes


class DisputeProcessor:
    def __init__(
        self,
        dispute_client: DisputeClient = Depends(DisputeClient),
        log: BoundLogger = Depends(get_logger_from_req),
    ):
        self.dispute_client = dispute_client
        self.log = log

    async def get(self, dispute_id: str, dispute_id_type: Optional[str] = None):
        """
        Retrieve DoorDash dispute

        :param dispute_id: [string] dispute unique id.
        :param dispute_id_type: [string] identify the type of dispute_id. Valid values include "pgp_dispute_id",
               "stripe_dispute_id")
        :return: Dispute object
        """
        self.log.info(
            f"[get] dispute_id:{dispute_id}, dispute_id_type:{dispute_id_type}"
        )
        dispute = await self.dispute_client.get_dispute_object(
            dispute_id=dispute_id, dispute_id_type=dispute_id_type
        )
        return dispute

    async def list_disputes(
        self,
        payer_id: str = None,
        payer_id_type: str = None,
        payment_method_id: str = None,
        payment_method_id_type: str = None,
    ):
        """
        Retrieve list of DoorDash dispute

        :param payer_id: [string] DoorDash payer_id or stripe_customer_id
        :param payer_id_type: [string] identify the type of payer_id.
        :param payment_method_id: [string] DoorDash payment method id or stripe_payment_method_id.
        :param payment_method_id_type: [string] identify the type of payment_method_id
        :return: List of Dispute Objects
        """
        if not (payer_id or payment_method_id):
            self.log.warn(f"[list_disputes] No parameters provided")
            raise DisputeReadError(
                error_code=PayinErrorCode.DISPUTE_LIST_NO_PARAMETERS, retryable=False
            )
        if not (payer_id_type or payment_method_id_type):
            self.log.warn(f"[list_disputes] No parameters provided")
            raise DisputeReadError(
                error_code=PayinErrorCode.DISPUTE_LIST_NO_ID_PARAMETERS, retryable=False
            )
        return await self.dispute_client.get_disputes_list(
            payer_id, payer_id_type, payment_method_id, payment_method_id_type
        )
