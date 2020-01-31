import time
from typing import Tuple

import pytest

from app.commons.providers.stripe.stripe_models import CustomerId
from app.commons.types import CountryCode, PgpCode
from app.commons.utils.validation import not_none
from app.payin.core.payer.model import Payer
from app.payin.core.payer.payer_client import PayerClient
from app.payin.core.payer.v1.processor import PayerProcessorV1
from app.payin.core.types import PayerReferenceIdType
from app.payin.repository.payer_repo import (
    GetPgpCustomerInput,
    PayerRepository,
    PgpCustomerDbEntity,
)

pytestmark = [pytest.mark.asyncio]


async def test_backfill_existing_stripe_customer(
    payer_processor_v1: PayerProcessorV1,
    payer_client: PayerClient,
    payer_repository: PayerRepository,
):

    country: CountryCode = CountryCode.US
    stripe_customer_id: CustomerId = await payer_client.pgp_create_customer(
        country=country, email="abc@gmail.com", description="customer someone"
    )

    some_cx_id = int(time.time())
    expected_payer_reference_id_type: PayerReferenceIdType = PayerReferenceIdType.DD_CONSUMER_ID

    payer_result: Tuple[Payer, bool] = await payer_processor_v1.backfill_payer(
        payer_reference_id=str(some_cx_id),
        payer_reference_id_type=expected_payer_reference_id_type,
        country=country,
        pgp_customer_id=stripe_customer_id,
    )

    payer: Payer = payer_result[0]
    existing: bool = payer_result[1]

    assert not existing, "should be created"
    assert payer
    assert len(not_none(payer.payment_gateway_provider_customers)) == 1
    provider_cus_details = not_none(payer.payment_gateway_provider_customers)[0]
    assert provider_cus_details.payment_provider == PgpCode.STRIPE
    assert provider_cus_details.payment_provider_customer_id == stripe_customer_id

    pgp_customer: PgpCustomerDbEntity = await payer_repository.get_pgp_customer(
        GetPgpCustomerInput(payer_id=payer.id, pgp_code=PgpCode.STRIPE)
    )
    assert pgp_customer
    assert pgp_customer.pgp_resource_id == stripe_customer_id

    duplicate_payer_result: Tuple[
        Payer, bool
    ] = await payer_processor_v1.backfill_payer(
        payer_reference_id=str(some_cx_id),
        payer_reference_id_type=expected_payer_reference_id_type,
        country=country,
        pgp_customer_id=stripe_customer_id,
    )

    assert duplicate_payer_result[0] == payer
    assert duplicate_payer_result[1], "should be existing"
