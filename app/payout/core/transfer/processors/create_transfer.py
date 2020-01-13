from datetime import datetime, timedelta

from aioredlock import Aioredlock
from starlette.status import HTTP_400_BAD_REQUEST

from app.commons.api.models import DEFAULT_INTERNAL_EXCEPTION, PaymentException
from structlog.stdlib import BoundLogger
from typing import Union, Optional, List, Tuple

from app.commons.cache.cache import PaymentCache
from app.commons.core.processor import (
    AsyncOperation,
    OperationRequest,
    OperationResponse,
)
from doordash_python_stats.ddstats import doorstats_global

from app.commons.async_kafka_producer import KafkaMessageProducer
from app.commons.lock.locks import PaymentLock
from app.commons.providers.dsj_client import DSJClient
from app.commons.providers.stripe.stripe_client import StripeAsyncClient
from app.payout.constants import (
    FRAUD_ENABLE_MX_PAYOUT_DELAY_AFTER_BANK_CHANGE,
    FRAUD_BUSINESS_WHITELIST_FOR_PAYOUT_DELAY_AFTER_BANK_CHANGE,
    FRAUD_MINIMUM_HOURS_BEFORE_MX_PAYOUT_AFTER_BANK_CHANGE,
    DISABLE_DASHER_PAYMENT_ACCOUNT_LIST_NAME,
    DISABLE_MERCHANT_PAYMENT_ACCOUNT_LIST_NAME,
    FRAUD_MX_AUTO_PAYMENT_DELAYED_RECENT_BANK_CHANGE,
    ENABLE_QUEUEING_MECHANISM_FOR_PAYOUT,
    WEEKLY_TRANSFER_PAYOUT_BUSINESS_IDS_MAPPING,
)
from app.payout.core.account.utils import (
    get_country_shortname,
    COUNTRY_TO_CURRENCY_CODE,
)
from app.payout.core.instant_payout.utils import get_payout_account_lock_name
from app.payout.core.transfer.processors.submit_transfer import (
    SubmitTransferRequest,
    SubmitTransfer,
)
from app.payout.core.transfer.tasks.submit_transfer_task import SubmitTransferTask
from app.payout.core.transfer.utils import (
    determine_transfer_status_from_latest_submission,
    get_target_metadata,
)
from app.payout.repository.bankdb.model.transaction import (
    TransactionDBEntity,
    TransactionUpdateDBEntity,
)
from app.payout.repository.bankdb.payment_account_edit_history import (
    PaymentAccountEditHistoryRepositoryInterface,
)
from app.payout.repository.bankdb.transaction import TransactionRepositoryInterface
from app.payout.repository.maindb.managed_account_transfer import (
    ManagedAccountTransferRepositoryInterface,
)
from app.payout.repository.maindb.model.payment_account import PaymentAccount, Entity
from app.payout.repository.maindb.model.transfer import (
    Transfer,
    TransferCreate,
    TransferUpdate,
    TransferStatus,
)
from app.payout.repository.maindb.payment_account import (
    PaymentAccountRepositoryInterface,
)
from app.payout.repository.maindb.stripe_transfer import (
    StripeTransferRepositoryInterface,
)
from app.payout.repository.maindb.transfer import TransferRepositoryInterface
import app.payout.models as payout_models
from app.payout.core.exceptions import PayoutError, PayoutErrorCode
from app.commons.runtime import runtime


class CreateTransferResponse(OperationResponse):
    transfer: Optional[Transfer]
    transaction_ids: List[int]
    error_code: Optional[str]


class CreateTransferRequest(OperationRequest):
    payout_account_id: int
    transfer_type: str
    end_time: datetime
    payout_day: Optional[payout_models.PayoutDay]
    start_time: Optional[datetime]
    payout_countries: Optional[List[str]]
    created_by_id: Optional[int]
    submit_after_creation: Optional[bool] = False


class CreateTransfer(AsyncOperation[CreateTransferRequest, CreateTransferResponse]):
    """
    Processor to create a transfer. This is used for both weekly and manually create_transfer
    """

    transfer_repo: TransferRepositoryInterface
    payment_account_repo: PaymentAccountRepositoryInterface
    payment_account_edit_history_repo: PaymentAccountEditHistoryRepositoryInterface
    transaction_repo: TransactionRepositoryInterface
    stripe_transfer_repo: StripeTransferRepositoryInterface
    managed_account_transfer_repo: ManagedAccountTransferRepositoryInterface
    payment_lock_manager: Aioredlock
    stripe: StripeAsyncClient
    kafka_producer: KafkaMessageProducer
    cache: PaymentCache
    dsj_client: DSJClient

    def __init__(
        self,
        request: CreateTransferRequest,
        *,
        transfer_repo: TransferRepositoryInterface,
        payment_account_repo: PaymentAccountRepositoryInterface,
        payment_account_edit_history_repo: PaymentAccountEditHistoryRepositoryInterface,
        transaction_repo: TransactionRepositoryInterface,
        stripe_transfer_repo: StripeTransferRepositoryInterface,
        managed_account_transfer_repo: ManagedAccountTransferRepositoryInterface,
        payment_lock_manager: Aioredlock,
        stripe: StripeAsyncClient,
        kafka_producer: KafkaMessageProducer,
        cache: PaymentCache,
        dsj_client: DSJClient,
        logger: BoundLogger = None,
    ):
        super().__init__(request, logger)
        self.request = request
        self.transfer_repo = transfer_repo
        self.payment_account_repo = payment_account_repo
        self.payment_account_edit_history_repo = payment_account_edit_history_repo
        self.transaction_repo = transaction_repo
        self.stripe_transfer_repo = stripe_transfer_repo
        self.managed_account_transfer_repo = managed_account_transfer_repo
        self.payment_lock_manager = payment_lock_manager
        self.stripe = stripe
        self.kafka_producer = kafka_producer
        self.cache = cache
        self.dsj_client = dsj_client

    async def _execute(self) -> CreateTransferResponse:
        self.logger.info(
            "Creating transfer for account.",
            payment_account_id=self.request.payout_account_id,
        )
        payment_account = await self.payment_account_repo.get_payment_account_by_id(
            payment_account_id=self.request.payout_account_id
        )
        # payment_account should always be valid
        if not payment_account:
            raise PayoutError(
                http_status_code=HTTP_400_BAD_REQUEST,
                error_code=PayoutErrorCode.INVALID_PAYMENT_ACCOUNT_ID,
                retryable=False,
            )
        # logic within following if statement is from create_transfer_for_account_id
        # when a transfer creation is triggered manually, we do not need to execute following logic
        if self.request.transfer_type != payout_models.TransferType.MANUAL:
            if self.request.payout_day:
                if not payment_account.entity:
                    self.logger.warning(
                        "[Create Transfer] Payment account entity not found.",
                        account_id=payment_account.id,
                    )
                    return CreateTransferResponse(
                        transfer=None,
                        transaction_ids=[],
                        error_code=PayoutErrorCode.PAYMENT_ACCOUNT_ENTITY_NOT_FOUND,
                    )
                account_payout_day = await self.get_payout_day(payment_account)

                if account_payout_day is not self.request.payout_day:
                    self.logger.info(
                        "[Create Transfer] Skip creating transfer for account because payout day does not match",
                        account_id=payment_account.id,
                        payout_day=self.request.payout_day,
                        account_payout_day=account_payout_day,
                    )
                    return CreateTransferResponse(
                        transfer=None,
                        transaction_ids=[],
                        error_code=PayoutErrorCode.PAYOUT_DAY_NOT_MATCH,
                    )

            if self.request.payout_countries:
                stripe_managed_account = (
                    await self.payment_account_repo.get_stripe_managed_account_by_id(
                        payment_account.account_id
                    )
                    if payment_account.account_id
                    else None
                )
                if (
                    stripe_managed_account
                    and stripe_managed_account.country_shortname
                    not in self.request.payout_countries
                ):
                    self.logger.debug(
                        "Skipping transfer for account because the payout country does not match",
                        payment_account_id=payment_account.id,
                        account_country=stripe_managed_account.country_shortname,
                        payout_countries=self.request.payout_countries,
                    )
                    return CreateTransferResponse(
                        transfer=None,
                        transaction_ids=[],
                        error_code=PayoutErrorCode.PAYOUT_COUNTRY_NOT_MATCH,
                    )
            if not await self.should_payment_account_be_auto_paid_weekly(
                payment_account_id=payment_account.id
            ):
                self.logger.info(
                    "Payment stopped: Ignoring creating weekly transfer for account id",
                    payment_account_id=payment_account.id,
                )
                return CreateTransferResponse(
                    transfer=None,
                    transaction_ids=[],
                    error_code=PayoutErrorCode.PAYMENT_BLOCKED,
                )

        currency = await self._get_currency(payment_account=payment_account)
        transfer, transaction_ids = await self.create_transfer_for_unpaid_transactions(
            payment_account_id=payment_account.id,
            currency=currency,
            start_time=self.request.start_time,
            end_time=self.request.end_time,
        )
        # check transaction_ids instead of transfer directly to avoid typing issue
        if not transaction_ids:
            return CreateTransferResponse(
                transfer=None,
                transaction_ids=[],
                error_code=PayoutErrorCode.NO_UNPAID_TRANSACTION_FOUND,
            )

        # update transfer created_by and reason if transfer type is MANUAL
        updated_transfer = transfer
        if (
            updated_transfer
            and self.request.transfer_type == payout_models.TransferType.MANUAL
        ):
            update_transfer_request = TransferUpdate(
                created_by_id=self.request.created_by_id,
                manual_transfer_reason="payout unpaid transactions",
            )
            updated_transfer = await self.transfer_repo.update_transfer_by_id(
                transfer_id=updated_transfer.id, data=update_transfer_request
            )
        if runtime.get_bool(
            "payout/feature-flags/enable_dsj_api_integration_for_weekly_payout.bool",
            False,
        ):
            if (
                payment_account.entity == payout_models.PayoutAccountTargetType.DASHER
                and updated_transfer
                and transaction_ids
            ):
                await self.dsj_client.post(
                    "/v1/transactions/target_metadata/",
                    {
                        "transfer_id": updated_transfer.id,
                        "transaction_ids": transaction_ids,
                    },
                )

        if self.request.submit_after_creation and updated_transfer:
            self.logger.info(
                "Enqueuing transfer submission for account",
                payout_account_id=payment_account.id,
            )
            if runtime.get_bool(ENABLE_QUEUEING_MECHANISM_FOR_PAYOUT, False):
                submit_transfer_task = SubmitTransferTask(
                    transfer_id=updated_transfer.id,
                    method=payout_models.TransferMethodType.STRIPE,
                    retry=False,
                    submitted_by=None,
                )
                await submit_transfer_task.send(kafka_producer=self.kafka_producer)
            else:
                submit_transfer_request = SubmitTransferRequest(
                    transfer_id=updated_transfer.id,
                    method=payout_models.TransferMethodType.STRIPE,
                    retry=False,
                    submitted_by=None,
                )
                submit_transfer_op = SubmitTransfer(
                    logger=self.logger,
                    request=submit_transfer_request,
                    transfer_repo=self.transfer_repo,
                    payment_account_repo=self.payment_account_repo,
                    payment_account_edit_history_repo=self.payment_account_edit_history_repo,
                    managed_account_transfer_repo=self.managed_account_transfer_repo,
                    transaction_repo=self.transaction_repo,
                    stripe_transfer_repo=self.stripe_transfer_repo,
                    stripe=self.stripe,
                    dsj_client=self.dsj_client,
                )
                await submit_transfer_op.execute()
        self.logger.info(
            "Finished executing create transfer for account",
            payout_account_id=payment_account.id,
        )
        return CreateTransferResponse(
            transfer=updated_transfer, transaction_ids=transaction_ids
        )

    def _handle_exception(
        self, dep_exec: BaseException
    ) -> Union[PaymentException, CreateTransferResponse]:
        raise DEFAULT_INTERNAL_EXCEPTION

    async def should_payment_account_be_auto_paid_weekly(
        self, payment_account_id: int
    ) -> bool:
        #  Check for potential mx banking fraud
        if await self.should_block_mx_payout(
            payment_account_id=payment_account_id, payout_date_time=datetime.utcnow()
        ):
            return False

        #  Check for manually set payment stop
        dasher_payment_account_stop_list = runtime.get_json(
            DISABLE_DASHER_PAYMENT_ACCOUNT_LIST_NAME, []
        )
        merchant_payment_account_stop_list = runtime.get_json(
            DISABLE_MERCHANT_PAYMENT_ACCOUNT_LIST_NAME, []
        )
        account_stop_list = (
            dasher_payment_account_stop_list + merchant_payment_account_stop_list
        )
        return payment_account_id not in account_stop_list

    async def should_block_mx_payout(
        self, payout_date_time: datetime, payment_account_id: int
    ) -> bool:
        target_type, target_id, statement_descriptor, target_biz_id = await get_target_metadata(
            payment_account_id=payment_account_id, dsj_client=self.dsj_client
        )
        if runtime.get_bool(FRAUD_ENABLE_MX_PAYOUT_DELAY_AFTER_BANK_CHANGE, False):
            try:
                if (
                    target_type == payout_models.PayoutTargetType.STORE
                    and target_biz_id
                    not in runtime.get_json(
                        FRAUD_BUSINESS_WHITELIST_FOR_PAYOUT_DELAY_AFTER_BANK_CHANGE, []
                    )
                ):
                    time_window_to_check_in_hours = runtime.get_int(
                        FRAUD_MINIMUM_HOURS_BEFORE_MX_PAYOUT_AFTER_BANK_CHANGE, 0
                    )
                    if time_window_to_check_in_hours == 0:
                        return False
                    recent_bank_change_threshold = payout_date_time - timedelta(
                        hours=time_window_to_check_in_hours
                    )
                    bank_info_recently_changed = await self.payment_account_edit_history_repo.get_bank_updates_for_store_with_payment_account_and_time_range(
                        payment_account_id=payment_account_id,
                        start_time=recent_bank_change_threshold,
                        end_time=payout_date_time,
                    )
                    if len(bank_info_recently_changed) > 0:
                        doorstats_global.incr(
                            FRAUD_MX_AUTO_PAYMENT_DELAYED_RECENT_BANK_CHANGE
                        )
                        return True
            except Exception as e:
                self.logger.exception("Exception in should_block_mx_payout", error=e)
        return False

    async def _get_currency(self, payment_account: PaymentAccount) -> Optional[str]:
        country_shortname = await get_country_shortname(
            payment_account=payment_account,
            payment_account_repository=self.payment_account_repo,
        )
        if country_shortname in COUNTRY_TO_CURRENCY_CODE:
            return COUNTRY_TO_CURRENCY_CODE[country_shortname]

        return None

    async def create_transfer_for_unpaid_transactions(
        self,
        payment_account_id: int,
        end_time: datetime,
        currency: Optional[str],
        start_time: Optional[datetime],
    ) -> Tuple[Optional[Transfer], List[int]]:
        # lock_name should be the same as the one for instant payout
        lock_name = get_payout_account_lock_name(payment_account_id)
        async with PaymentLock(lock_name, self.payment_lock_manager):
            return await self.create_with_redis_lock(
                payment_account_id=payment_account_id,
                currency=currency,
                start_time=start_time,
                end_time=end_time,
            )

    async def create_with_redis_lock(
        self,
        payment_account_id: int,
        end_time: datetime,
        currency: Optional[str],
        start_time: Optional[datetime],
    ) -> Tuple[Optional[Transfer], List[int]]:
        unpaid_transactions = await self.transaction_repo.get_unpaid_transaction_by_payout_account_id_without_limit(
            payout_account_id=payment_account_id,
            start_time=start_time,
            end_time=end_time,
        )
        if len(unpaid_transactions) <= 0:
            return None, []
        return await self.create_transfer_for_transactions(
            payment_account_id=payment_account_id,
            unpaid_transactions=unpaid_transactions,
            currency=currency,
        )

    async def create_transfer_for_transactions(
        self,
        payment_account_id: int,
        unpaid_transactions: List[TransactionDBEntity],
        currency: Optional[str],
    ) -> Tuple[Optional[Transfer], List[int]]:
        subtotal = self.compute_transfer_total_from_transactions(
            transactions=unpaid_transactions
        )
        if subtotal < 0:
            return None, []
        # Default behavior in DSJ is that for create_transfer_for_transactions, since there is no adjustments,
        # transfer.amount = transfer.subtotal. Also, method default to ""
        create_request = TransferCreate(
            payment_account_id=payment_account_id,
            subtotal=subtotal,
            amount=subtotal,
            adjustments="{}",
            method="",
            currency=currency,
            status=TransferStatus.CREATING,
        )
        transfer = await self.transfer_repo.create_transfer(data=create_request)
        transaction_ids = [transaction.id for transaction in unpaid_transactions]
        update_transaction_request = TransactionUpdateDBEntity(transfer_id=transfer.id)
        updated_transactions = await self.transaction_repo.update_transaction_ids_without_transfer_id(
            transaction_ids=transaction_ids, data=update_transaction_request
        )

        transfer_status = await determine_transfer_status_from_latest_submission(
            transfer=transfer, stripe_transfer_repo=self.stripe_transfer_repo
        )
        update_transfer_request = TransferUpdate(status=transfer_status)
        updated_transfer = await self.transfer_repo.update_transfer_by_id(
            transfer_id=transfer.id, data=update_transfer_request
        )
        assert updated_transfer, "updated transfer cannot be None"
        self.logger.info(
            "Transfer is attaching to transaction list",
            transfer_id=updated_transfer.id,
            transaction_list=[
                "tx <{}> {}".format(t.id, t.amount) for t in updated_transactions
            ],
        )

        if not (len(updated_transactions) == len(unpaid_transactions)):
            self.logger.error(
                "Inconsistency updating transactions",
                updated_transactions_count=len(updated_transactions),
                transaction_count=len(unpaid_transactions),
            )

        self.logger.info(
            "Transfer is being created with total amount and transaction_ids",
            transfer_id=updated_transfer.id,
            transaction_list=[
                "tx <{}> {}".format(t.id, t.amount) for t in updated_transactions
            ],
        )
        return updated_transfer, [t.id for t in updated_transactions]

    def compute_transfer_total_from_transactions(
        self, transactions: List[TransactionDBEntity]
    ) -> int:
        """
        Computes the transfer total from the transactions passed
        :param transactions:
        :return: transfer amount
        """
        amount = sum(t.amount for t in transactions)
        return amount

    async def get_payout_day(
        self, payment_account: PaymentAccount
    ) -> payout_models.PayoutDay:
        if payment_account.entity == Entity.DASHER:
            return payout_models.PayoutDay.MONDAY
        elif payment_account.entity in (Entity.STORE, Entity.MERCHANT):
            for payout_day in payout_models.PayoutDay:
                # go through payment account ids for each payout day
                # check whether given id is in payment_account_ids of current payout_day
                # if so, return corresponding payout day of that payment account, otherwise default to Thursday
                payment_account_ids = await self.get_payment_account_ids_by_day_from_cache(
                    payout_day
                )
                if payment_account.id in payment_account_ids:
                    return payout_models.PayoutDay(payout_day)
        self.logger.warn(
            "Invalid payout entity type, default payout day to Thursday",
            payment_account_id=payment_account.id,
            entity=payment_account.entity,
        )
        return payout_models.PayoutDay.THURSDAY

    async def get_payment_account_ids_by_day_from_cache(
        self, payout_day: str
    ) -> List[int]:
        cache_key = f"{payout_day}_payout_payment_accounts"
        payment_account_ids = await self.cache.get(cache_key)
        if not payment_account_ids:
            payment_account_ids = await self.get_payment_account_ids_by_payout_day(
                payout_day
            )
            # cache results for 4 hours
            await self.cache.set(cache_key, payment_account_ids, ttl_sec=60 * 60 * 4)
        return payment_account_ids

    async def get_payment_account_ids_by_payout_day(self, payout_day: str) -> List[int]:
        payment_account_ids = []
        biz_ids = runtime.get_json(
            WEEKLY_TRANSFER_PAYOUT_BUSINESS_IDS_MAPPING[payout_day], []
        )
        for biz_id in biz_ids:
            self.logger.info(
                "Retrieving payment account ids with business_id",
                payout_day=payout_day,
                business_id=biz_id,
            )
            retrieved_payment_account_ids = await self.get_payment_account_ids_with_biz_id(
                business_id=biz_id, dsj_client=self.dsj_client
            )
            payment_account_ids.extend(retrieved_payment_account_ids)
        self.logger.info(
            "Finished retrieving payment account ids by payout day",
            payout_day=payout_day,
            payment_account_count=len(payment_account_ids),
        )
        return payment_account_ids

    async def get_payment_account_ids_with_biz_id(
        self, business_id: int, dsj_client: DSJClient
    ) -> List[int]:
        if runtime.get_bool(
            "payout/feature-flags/enable_dsj_api_integration_for_weekly_payout.bool",
            False,
        ):
            response = await dsj_client.get(
                "/v1/payment_accounts/", {"business_id": business_id}
            )

            if response:
                payment_account_ids = response["payment_account_ids"]
                return payment_account_ids
        return []
