from aioredlock import Aioredlock
from fastapi import Depends
from starlette.requests import Request

from app.commons.context.req_context import get_stripe_async_client_from_req
from app.commons.async_kafka_producer import KafkaMessageProducer
from app.commons.cache.cache import setup_cache, PaymentCache
from app.commons.providers.stripe.stripe_client import StripeAsyncClient
from app.commons.service import BaseService
from app.commons.providers.dsj_client import DSJClient
from app.payout.constants import PAYOUT_CACHE_APP_NAME
from app.payout.core.account.processor import PayoutAccountProcessors
from app.payout.core.instant_payout.processor import InstantPayoutProcessors
from app.payout.core.transfer.processor import TransferProcessors
from app.payout.core.transaction.processor import TransactionProcessors
from app.payout.repository.bankdb import (
    payout,
    stripe_payout_request,
    stripe_managed_account_transfer,
    payout_card,
    payout_method,
    payout_method_miscellaneous,
    transaction,
    payment_account_edit_history,
)
from app.payout.repository.maindb import (
    payment_account,
    stripe_transfer,
    transfer,
    managed_account_transfer,
)
from app.payout.repository.paymentdb import payout_lock

__all__ = [
    "create_payout_account_processors",
    "create_transfer_processors",
    "create_transaction_processors",
    "get_stripe_client",
    "PayoutService",
    "PaymentAccountRepository",
    "PaymentAccountRepositoryInterface",
    "PayoutCardRepositoryInterface",
    "PayoutMethodMiscellaneousRepositoryInterface",
    "PayoutMethodRepositoryInterface",
    "TransferRepository",
    "TransferRepositoryInterface",
    "PayoutRepository",
    "PayoutRepositoryInterface",
    "StripePayoutRequestRepository",
    "StripePayoutRequestRepositoryInterface",
    "ManagedAccountTransferRepository",
    "ManagedAccountTransferRepositoryInterface",
    "StripeManagedAccountTransferRepository",
    "StripeManagedAccountTransferRepositoryInterface",
    "TransactionRepository",
    "TransactionRepositoryInterface",
    "PaymentAccountEditHistoryRepository",
    "PaymentAccountEditHistoryRepositoryInterface",
    "RedisLockManager",
    "create_instant_payout_processors",
    "KafkaProducer",
    "PayoutLockRepository",
]

PaymentAccountRepositoryInterface = payment_account.PaymentAccountRepositoryInterface
PayoutCardRepositoryInterface = payout_card.PayoutCardRepositoryInterface
PayoutMethodRepositoryInterface = payout_method.PayoutMethodRepositoryInterface
PayoutMethodMiscellaneousRepositoryInterface = (
    payout_method_miscellaneous.PayoutMethodMiscellaneousRepositoryInterface
)
TransferRepositoryInterface = transfer.TransferRepositoryInterface
PayoutRepositoryInterface = payout.PayoutRepositoryInterface
StripePayoutRequestRepositoryInterface = (
    stripe_payout_request.StripePayoutRequestRepositoryInterface
)
StripeManagedAccountTransferRepositoryInterface = (
    stripe_managed_account_transfer.StripeManagedAccountTransferRepositoryInterface
)
StripeTransferRepositoryInterface = stripe_transfer.StripeTransferRepositoryInterface
ManagedAccountTransferRepositoryInterface = (
    managed_account_transfer.ManagedAccountTransferRepositoryInterface
)
TransactionRepositoryInterface = transaction.TransactionRepositoryInterface
PaymentAccountEditHistoryRepositoryInterface = (
    payment_account_edit_history.PaymentAccountEditHistoryRepositoryInterface
)


class PayoutService(BaseService):
    service_name = "payout-service"
    payment_accounts: payment_account.PaymentAccountRepository
    payout_cards: payout_card.PayoutCardRepository
    payout_methods: payout_method.PayoutMethodRepository
    payout_method_miscellaneous: payout_method_miscellaneous.PayoutMethodMiscellaneousRepository
    transactions: transaction.TransactionRepository
    transfers: transfer.TransferRepository
    payouts: payout.PayoutRepository
    stripe_payout_requests: stripe_payout_request.StripePayoutRequestRepository
    striped_managed_account_transfers: stripe_managed_account_transfer.StripeManagedAccountTransferRepository
    stripe_transfers: stripe_transfer.StripeTransferRepository
    managed_account_transfers: managed_account_transfer.ManagedAccountTransferRepository
    payment_account_edit_history: payment_account_edit_history.PaymentAccountEditHistoryRepository
    payout_locks: payout_lock.PayoutLockRepository

    dsj_client: DSJClient
    stripe: StripeAsyncClient
    redis_lock_manager: Aioredlock
    kafka_producer: KafkaMessageProducer
    cache: PaymentCache

    def __init__(self, request: Request):
        super().__init__(request)

        # maindb
        maindb = self.app_context.payout_maindb
        self.payment_accounts = payment_account.PaymentAccountRepository(maindb)
        self.transfers = transfer.TransferRepository(maindb)
        self.stripe_transfers = stripe_transfer.StripeTransferRepository(maindb)
        self.managed_account_transfers = managed_account_transfer.ManagedAccountTransferRepository(
            maindb
        )

        # bankdb
        bankdb = self.app_context.payout_bankdb
        self.payouts = payout.PayoutRepository(bankdb)
        self.stripe_payout_requests = stripe_payout_request.StripePayoutRequestRepository(
            bankdb
        )
        self.striped_managed_account_transfers = stripe_managed_account_transfer.StripeManagedAccountTransferRepository(
            bankdb
        )
        self.payout_cards = payout_card.PayoutCardRepository(bankdb)
        self.payout_methods = payout_method.PayoutMethodRepository(bankdb)
        self.payout_method_miscellaneous = payout_method_miscellaneous.PayoutMethodMiscellaneousRepository(
            bankdb
        )
        self.transactions = transaction.TransactionRepository(bankdb)
        self.payment_account_edit_history = payment_account_edit_history.PaymentAccountEditHistoryRepository(
            bankdb
        )

        # payment_db
        paymentdb = self.app_context.payout_paymentdb
        self.payout_locks = payout_lock.PayoutLockRepository(paymentdb)

        # dsj_client
        self.dsj_client = self.app_context.dsj_client

        # stripe
        self.stripe = get_stripe_async_client_from_req(request)  # type:ignore

        self.redis_lock_manager = self.app_context.redis_lock_manager
        self.kafka_producer = self.app_context.kafka_producer

        self.cache = setup_cache(
            app_context=self.app_context, app=PAYOUT_CACHE_APP_NAME
        )


def PaymentAccountRepository(
    payout_service: PayoutService = Depends()
) -> payment_account.PaymentAccountRepositoryInterface:
    return payout_service.payment_accounts


def PayoutCardRepository(
    payout_service: PayoutService = Depends()
) -> payout_card.PayoutCardRepositoryInterface:
    return payout_service.payout_cards


def PayoutMethodRepository(
    payout_service: PayoutService = Depends()
) -> payout_method.PayoutMethodRepositoryInterface:
    return payout_service.payout_methods


def PayoutMethodMiscellaneousRepository(
    payout_service: PayoutService = Depends()
) -> payout_method_miscellaneous.PayoutMethodMiscellaneousRepositoryInterface:
    return payout_service.payout_method_miscellaneous


def TransactionRepository(
    payout_service: PayoutService = Depends()
) -> transaction.TransactionRepository:
    return payout_service.transactions


def TransferRepository(
    payout_service: PayoutService = Depends()
) -> transfer.TransferRepository:
    return payout_service.transfers


def PayoutRepository(
    payout_service: PayoutService = Depends()
) -> payout.PayoutRepositoryInterface:
    return payout_service.payouts


def StripePayoutRequestRepository(
    payout_service: PayoutService = Depends()
) -> stripe_payout_request.StripePayoutRequestRepositoryInterface:
    return payout_service.stripe_payout_requests


def StripeManagedAccountTransferRepository(
    payout_service: PayoutService = Depends()
) -> stripe_managed_account_transfer.StripeManagedAccountTransferRepositoryInterface:
    return payout_service.striped_managed_account_transfers


def StripeTransferRepository(
    payout_service: PayoutService = Depends()
) -> stripe_transfer.StripeTransferRepositoryInterface:
    return payout_service.stripe_transfers


def ManagedAccountTransferRepository(
    payout_service: PayoutService = Depends()
) -> managed_account_transfer.ManagedAccountTransferRepositoryInterface:
    return payout_service.managed_account_transfers


def PaymentAccountEditHistoryRepository(
    payout_service: PayoutService = Depends()
) -> payment_account_edit_history.PaymentAccountEditHistoryRepositoryInterface:
    return payout_service.payment_account_edit_history


def PayoutLockRepository(
    payout_service: PayoutService = Depends()
) -> payout_lock.PayoutLockRepository:
    return payout_service.payout_locks


def DSJClientHandle(payout_service: PayoutService = Depends()):
    return payout_service.dsj_client


def RedisLockManager(payout_service: PayoutService = Depends()):
    return payout_service.redis_lock_manager


def KafkaProducer(payout_service: PayoutService = Depends()):
    return payout_service.kafka_producer


def create_payout_account_processors(payout_service: PayoutService = Depends()):
    return PayoutAccountProcessors(
        logger=payout_service.log,
        payment_account_repo=payout_service.payment_accounts,
        payment_account_edit_history_repo=payout_service.payment_account_edit_history,
        payout_card_repo=payout_service.payout_cards,
        payout_method_repo=payout_service.payout_methods,
        payout_method_miscellaneous_repo=payout_service.payout_method_miscellaneous,
        stripe_transfer_repo=payout_service.stripe_transfers,
        stripe_payout_request_repo=payout_service.stripe_payout_requests,
        stripe_managed_account_transfer_repo=payout_service.striped_managed_account_transfers,
        stripe=payout_service.stripe,
        managed_account_transfer_repo=payout_service.managed_account_transfers,
        cache=payout_service.cache,
    )


def create_transfer_processors(payout_service: PayoutService = Depends()):
    return TransferProcessors(
        logger=payout_service.log,
        stripe=payout_service.stripe,
        transfer_repo=payout_service.transfers,
        payment_account_repo=payout_service.payment_accounts,
        stripe_transfer_repo=payout_service.stripe_transfers,
        managed_account_transfer_repo=payout_service.managed_account_transfers,
        transaction_repo=payout_service.transactions,
        payment_account_edit_history_repo=payout_service.payment_account_edit_history,
        payment_lock_manager=payout_service.redis_lock_manager,
        kafka_producer=payout_service.kafka_producer,
        cache=payout_service.cache,
        dsj_client=payout_service.dsj_client,
        payout_lock_repo=payout_service.payout_locks,
    )


def get_stripe_client(payout_service: PayoutService = Depends()) -> StripeAsyncClient:
    return payout_service.stripe


def create_transaction_processors(payout_service: PayoutService = Depends()):
    return TransactionProcessors(
        logger=payout_service.log, transaction_repo=payout_service.transactions
    )


def create_instant_payout_processors(payout_service: PayoutService = Depends()):
    return InstantPayoutProcessors(
        logger=payout_service.log,
        payout_account_repo=payout_service.payment_accounts,
        payout_card_repo=payout_service.payout_cards,
        payout_method_repo=payout_service.payout_methods,
        payout_repo=payout_service.payouts,
        stripe_payout_request_repo=payout_service.stripe_payout_requests,
        transaction_repo=payout_service.transactions,
        stripe=payout_service.stripe,
        payment_lock_manager=payout_service.redis_lock_manager,
        stripe_managed_account_transfer_repo=payout_service.striped_managed_account_transfers,
        payout_lock_repo=payout_service.payout_locks,
    )
