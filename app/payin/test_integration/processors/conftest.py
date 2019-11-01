from uuid import uuid4

import pytest

from app.commons.context.app_context import AppContext
from app.commons.context.req_context import ReqContext
from app.commons.jobs.pool import JobPool
from app.commons.providers.stripe.stripe_client import StripeAsyncClient
from app.conftest import StripeAPISettings
from app.payin.core.cart_payment.processor import (
    CartPaymentInterface,
    CartPaymentProcessor,
    LegacyPaymentInterface,
)
from app.payin.core.payer.payer_client import PayerClient
from app.payin.core.payer.v0.processor import PayerProcessorV0
from app.payin.core.payer.v1.processor import PayerProcessorV1
from app.payin.core.payment_method.payment_method_client import PaymentMethodClient
from app.payin.core.payment_method.processor import PaymentMethodProcessor
from app.payin.repository.cart_payment_repo import CartPaymentRepository
from app.payin.repository.payer_repo import PayerRepository
from app.payin.repository.payment_method_repo import PaymentMethodRepository


def _build_request_context(
    app_context: AppContext, stripe_async_client: StripeAsyncClient
) -> ReqContext:
    req_id = uuid4()
    return ReqContext(
        req_id=req_id,
        log=app_context.log.bind(req_id=req_id),
        commando_mode=False,
        stripe_async_client=stripe_async_client,
        commando_legacy_payment_white_list=[],
        verify_card_in_commando_mode=False,
    )


@pytest.fixture
def stripe_pool() -> JobPool:
    return JobPool(name="stripe")


@pytest.fixture
def stripe_async_client(app_context: AppContext) -> StripeAsyncClient:
    return StripeAsyncClient(
        executor_pool=app_context.stripe_thread_pool,
        stripe_client=app_context.stripe_client,
        commando=False,
    )


@pytest.fixture
def req_context(
    app_context: AppContext, stripe_async_client: StripeAsyncClient
) -> ReqContext:
    return _build_request_context(
        app_context=app_context, stripe_async_client=stripe_async_client
    )


@pytest.fixture
def cart_payment_repository(app_context: AppContext) -> CartPaymentRepository:
    return CartPaymentRepository(app_context)


@pytest.fixture
def payer_repository(app_context: AppContext) -> PayerRepository:
    return PayerRepository(app_context)


@pytest.fixture
def payment_method_repository(app_context: AppContext) -> PaymentMethodRepository:
    return PaymentMethodRepository(app_context)


@pytest.fixture
def payer_client(
    app_context: AppContext,
    req_context: ReqContext,
    payer_repository: PayerRepository,
    stripe_async_client: StripeAsyncClient,
) -> PayerClient:
    return PayerClient(
        app_ctxt=app_context,
        log=req_context.log,
        payer_repo=payer_repository,
        stripe_async_client=stripe_async_client,
    )


@pytest.fixture
def payment_method_client(
    app_context: AppContext,
    req_context: ReqContext,
    payment_method_repository: PaymentMethodRepository,
    stripe_async_client: StripeAsyncClient,
) -> PaymentMethodClient:
    return PaymentMethodClient(
        app_ctxt=app_context,
        payment_method_repo=payment_method_repository,
        log=req_context.log,
        stripe_async_client=stripe_async_client,
    )


@pytest.fixture
def cart_payment_interface(
    app_context: AppContext,
    req_context: ReqContext,
    cart_payment_repository: CartPaymentRepository,
    payer_client: PayerClient,
    payment_method_client: PaymentMethodClient,
    stripe_async_client: StripeAsyncClient,
) -> CartPaymentInterface:
    return CartPaymentInterface(
        app_context=app_context,
        req_context=req_context,
        payment_repo=cart_payment_repository,
        payer_client=payer_client,
        payment_method_client=payment_method_client,
        stripe_async_client=stripe_async_client,
    )


@pytest.fixture
def legacy_payment_interface(
    app_context: AppContext,
    req_context: ReqContext,
    cart_payment_repository: CartPaymentRepository,
    stripe_async_client: StripeAsyncClient,
) -> LegacyPaymentInterface:
    return LegacyPaymentInterface(
        app_context=app_context,
        req_context=req_context,
        payment_repo=cart_payment_repository,
        stripe_async_client=stripe_async_client,
    )


@pytest.fixture
def cart_payment_processor(
    app_context: AppContext,
    req_context: ReqContext,
    cart_payment_interface: CartPaymentInterface,
    legacy_payment_interface: LegacyPaymentInterface,
) -> CartPaymentProcessor:
    return CartPaymentProcessor(
        log=req_context.log,
        cart_payment_interface=cart_payment_interface,
        legacy_payment_interface=legacy_payment_interface,
    )


@pytest.fixture
def payer_processor_v0(
    req_context: ReqContext,
    payment_method_client: PaymentMethodClient,
    payer_client: PayerClient,
) -> PayerProcessorV0:
    return PayerProcessorV0(
        log=req_context.log,
        payer_client=payer_client,
        payment_method_client=payment_method_client,
    )


@pytest.fixture
def payer_processor_v1(
    req_context: ReqContext,
    payment_method_client: PaymentMethodClient,
    payer_client: PayerClient,
) -> PayerProcessorV1:
    return PayerProcessorV1(
        log=req_context.log,
        payer_client=payer_client,
        payment_method_client=payment_method_client,
    )


@pytest.fixture
def payment_method_processor(
    req_context: ReqContext,
    app_context: AppContext,
    payment_method_client: PaymentMethodClient,
    payer_client: PayerClient,
) -> PaymentMethodProcessor:
    return PaymentMethodProcessor(
        log=req_context.log,
        app_ctxt=app_context,
        payment_method_client=payment_method_client,
        payer_client=payer_client,
    )


@pytest.fixture(autouse=True)
def enable_stripe_outbound(stripe_api: StripeAPISettings):
    stripe_api.enable_outbound()


@pytest.fixture(autouse=True)
def override_capture_delay(app_context: AppContext):
    original_capture_service_delay = (
        app_context.capture_service.default_capture_delay_in_minutes
    )
    app_context.capture_service.default_capture_delay_in_minutes = 0
    yield
    app_context.capture_service.default_capture_delay_in_minutes = (
        original_capture_service_delay
    )
