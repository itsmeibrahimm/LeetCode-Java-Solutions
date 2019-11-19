from datetime import datetime
from typing import List

from fastapi import Depends
from structlog.stdlib import BoundLogger

from app.commons.context.req_context import get_logger_from_req
from app.commons.types import CountryCode
from app.payin.core.dispute.dispute_client import DisputeClient
from app.payin.core.dispute.model import (
    Dispute,
    DisputeList,
    DisputeChargeMetadata,
    Evidence,
)
from app.payin.core.dispute.types import DisputeIdType, ReasonType
from app.payin.core.exceptions import DisputeReadError, PayinErrorCode


class DisputeProcessor:
    """
    Entry of business layer which defines the workflow of each endpoint of API presentation layer.
    """

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

        self.log.info(
            "[get_dispute] getting dispute", dd_stripe_dispute_id=dd_stripe_dispute_id
        )
        dispute = await self.dispute_client.get_raw_dispute(
            dispute_id=dd_stripe_dispute_id,
            dispute_id_type=DisputeIdType.DD_STRIPE_DISPUTE_ID,
        )
        return dispute

    async def submit_dispute_evidence(
        self, stripe_dispute_id: str, evidence: Evidence, country: CountryCode
    ):
        # Step 1: validate existence of dispute object from DB.
        dispute: Dispute = await self.dispute_client.get_raw_dispute(
            dispute_id=stripe_dispute_id,
            dispute_id_type=DisputeIdType.STRIPE_DISPUTE_ID,
        )

        # Step 2: submit evidence to Payment Provider.
        await self.dispute_client.pgp_submit_dispute_evidence(
            dispute_id=dispute.stripe_dispute_id, evidence=evidence, country=country
        )
        submitted_at: datetime = datetime.utcnow()

        # Step 3: update both submitted_at and updated_at
        updated_dispute = await self.dispute_client.update_raw_dispute_submitted_time(
            dd_stripe_dispute_id=dispute.stripe_dispute_id, submitted_at=submitted_at
        )

        return updated_dispute

    def _get_distinct_dispute_list_by_charge_id(self, disputes_list):
        # Returns distinct disputes based on stripe_charge_id and taking latest disputed_at as selection criteria
        from collections import defaultdict

        charge_id_group = defaultdict(list)
        for dispute in disputes_list:
            charge_id_group[dispute.stripe_charge_id].append(dispute)
        distinct_dispute = []
        for key, value in charge_id_group.items():
            value.sort(key=lambda dispute: dispute.disputed_at, reverse=True)
            distinct_dispute.append(value[0])
        return distinct_dispute

    async def list_disputes(
        self,
        reasons: List[ReasonType],
        dd_payment_method_id: str = None,
        stripe_payment_method_id: str = None,
        dd_stripe_card_id: int = None,
        dd_consumer_id: int = None,
        start_time: datetime = None,
        distinct: bool = False,
    ) -> DisputeList:
        """
        Retrieve list of DoorDash dispute

        :param  dd_payment_method_id: [string] DoorDash payment method id
        :param stripe_payment_method_id: [string] Stripe payment method id
        :param dd_stripe_card_id: [int] Primary key in Stripe Card table
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
            or dd_consumer_id
        ):
            self.log.warn("[list_disputes] No parameters provided")
            raise DisputeReadError(error_code=PayinErrorCode.DISPUTE_LIST_NO_PARAMETERS)

        disputes_list: List[Dispute] = await self.dispute_client.get_raw_disputes_list(
            dd_payment_method_id=dd_payment_method_id,
            stripe_payment_method_id=stripe_payment_method_id,
            dd_stripe_card_id=dd_stripe_card_id,
            dd_consumer_id=dd_consumer_id,
            start_time=start_time,
            reasons=reasons,
        )
        data: List[Dispute] = disputes_list
        if distinct:
            data = self._get_distinct_dispute_list_by_charge_id(disputes_list)
        return DisputeList(
            count=len(data),
            has_more=False,  # Currently default to False. Returning all the disputes for a query
            total_amount=sum([dispute.amount for dispute in data]),
            data=data,
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
