import pytest

from app.commons.context.app_context import AppContext
from app.payin.repository.cart_payment_repo import CartPaymentRepository
from app.payin.repository.payer_repo import PayerRepository
from app.payin.repository.payment_method_repo import PaymentMethodRepository


@pytest.fixture
async def cart_payment_repository(app_context: AppContext):
    return CartPaymentRepository(app_context)


@pytest.fixture
async def payer_repository(app_context: AppContext):
    yield PayerRepository(app_context)


@pytest.fixture
async def payment_method_repository(app_context: AppContext):
    yield PaymentMethodRepository(app_context)
