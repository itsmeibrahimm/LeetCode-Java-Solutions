from typing import Union

from structlog.stdlib import BoundLogger

from app.commons.cache.cache import cached, PaymentCache, get_cache
from app.commons.cache.utils import compose_cache_key
from app.commons.providers.stripe.stripe_client import StripeAsyncClient
from app.commons.types import CountryCode
from app.payout.constants import (
    PAYOUT_CACHE_APP_NAME,
    CACHE_KEY_PREFIX_GET_PAYOUT_ACCOUNT,
    CACHE_TTL_SEC_GET_PAYOUT_ACCOUNT,
)
from app.payout.core.feature_flags import enabled_cache_key_prefix_list
from app.payout.core.transfer.cancel_payout import (
    CancelPayoutRequest,
    CancelPayoutResponse,
    CancelPayout,
)
from app.payout.core.account.processors.create_account import (
    CreatePayoutAccountRequest,
    CreatePayoutAccount,
)
from app.payout.core.account.processors.create_payout_method import (
    CreatePayoutMethod,
    CreatePayoutMethodRequest,
)
from app.payout.core.transfer.create_standard_payout import (
    CreateStandardPayoutRequest,
    CreateStandardPayoutResponse,
    CreateStandardPayout,
)
from app.payout.core.account.processors.get_account import (
    GetPayoutAccountRequest,
    GetPayoutAccount,
)
from app.payout.core.account.processors.get_account_stream import (
    GetPayoutAccountStreamRequest,
    GetPayoutAccountStreamResponse,
    GetPayoutAccountStream,
)
from app.payout.core.account.processors.get_default_payout_card import (
    GetDefaultPayoutCardRequest,
    GetDefaultPayoutCard,
)
from app.payout.core.account.processors.get_payout_method import (
    GetPayoutMethodRequest,
    GetPayoutMethod,
)
from app.payout.core.account.processors.list_payout_methods import (
    ListPayoutMethodRequest,
    ListPayoutMethod,
)
import app.payout.core.account.models as account_models
from app.payout.repository.bankdb.payment_account_edit_history import (
    PaymentAccountEditHistoryRepositoryInterface,
)
from app.payout.repository.bankdb.payout_card import PayoutCardRepositoryInterface
from app.payout.repository.bankdb.payout_method import PayoutMethodRepositoryInterface
from app.payout.repository.bankdb.payout_method_miscellaneous import (
    PayoutMethodMiscellaneousRepository,
)
from app.payout.repository.bankdb.stripe_managed_account_transfer import (
    StripeManagedAccountTransferRepositoryInterface,
)
from app.payout.core.account.processors.update_account_statement_descriptor import (
    UpdatePayoutAccountStatementDescriptorRequest,
    UpdatePayoutAccountStatementDescriptor,
)
from app.payout.core.account.processors.verify_account import (
    VerifyPayoutAccountRequest,
    VerifyPayoutAccount,
)
from app.payout.core.account.processors.get_required_fields import (
    GetPaymentsOnboardingRequirements,
    GetRequiredFieldsRequest,
)
from app.payout.repository.bankdb.stripe_payout_request import (
    StripePayoutRequestRepositoryInterface,
)
from app.payout.repository.maindb.managed_account_transfer import (
    ManagedAccountTransferRepositoryInterface,
)
from app.payout.repository.maindb.payment_account import (
    PaymentAccountRepositoryInterface,
)
from app.payout.repository.maindb.stripe_transfer import (
    StripeTransferRepositoryInterface,
)
from app.payout.models import PayoutTargetType


class PayoutAccountProcessors:
    logger: BoundLogger
    payment_account_repo: PaymentAccountRepositoryInterface
    payment_account_edit_history_repo: PaymentAccountEditHistoryRepositoryInterface
    payout_card_repo: PayoutCardRepositoryInterface
    payout_method_repo: PayoutMethodRepositoryInterface
    payout_method_miscellaneous_repo: PayoutMethodMiscellaneousRepository
    stripe_transfer_repo: StripeTransferRepositoryInterface
    stripe_payout_request_repo: StripePayoutRequestRepositoryInterface
    stripe: StripeAsyncClient
    cache: PaymentCache

    def __init__(
        self,
        logger: BoundLogger,
        payment_account_repo: PaymentAccountRepositoryInterface,
        payment_account_edit_history_repo: PaymentAccountEditHistoryRepositoryInterface,
        payout_card_repo: PayoutCardRepositoryInterface,
        payout_method_repo: PayoutMethodRepositoryInterface,
        payout_method_miscellaneous_repo: PayoutMethodMiscellaneousRepository,
        stripe_transfer_repo: StripeTransferRepositoryInterface,
        stripe_payout_request_repo: StripePayoutRequestRepositoryInterface,
        stripe_managed_account_transfer_repo: StripeManagedAccountTransferRepositoryInterface,
        stripe: StripeAsyncClient,
        managed_account_transfer_repo: ManagedAccountTransferRepositoryInterface,
        cache: PaymentCache,
    ):
        self.logger = logger
        self.payment_account_repo = payment_account_repo
        self.payment_account_edit_history_repo = payment_account_edit_history_repo
        self.payout_card_repo = payout_card_repo
        self.payout_method_repo = payout_method_repo
        self.payout_method_miscellaneous_repo = payout_method_miscellaneous_repo
        self.stripe_transfer_repo = stripe_transfer_repo
        self.stripe_payout_request_repo = stripe_payout_request_repo
        self.stripe_managed_account_transfer_repo = stripe_managed_account_transfer_repo
        self.stripe = stripe
        self.managed_account_transfer_repo = managed_account_transfer_repo
        self.payout_card_repo = payout_card_repo
        self.payout_method_repo = payout_method_repo
        self.cache = cache

    async def get_payout_account_stream(
        self, request: GetPayoutAccountStreamRequest
    ) -> GetPayoutAccountStreamResponse:
        get_account_stream_op = GetPayoutAccountStream(
            logger=self.logger,
            payment_account_repo=self.payment_account_repo,
            request=request,
        )
        return await get_account_stream_op.execute()

    async def create_payout_account(
        self, request: CreatePayoutAccountRequest
    ) -> account_models.PayoutAccountInternal:
        create_account_op = CreatePayoutAccount(
            logger=self.logger,
            payment_account_repo=self.payment_account_repo,
            request=request,
        )
        return await create_account_op.execute()

    @cached(
        key=CACHE_KEY_PREFIX_GET_PAYOUT_ACCOUNT,
        app=PAYOUT_CACHE_APP_NAME,
        ttl_sec=CACHE_TTL_SEC_GET_PAYOUT_ACCOUNT,
        response_model=account_models.PayoutAccountInternal,
    )
    async def get_payout_account(
        self, request: GetPayoutAccountRequest
    ) -> account_models.PayoutAccountInternal:
        get_account_op = GetPayoutAccount(
            logger=self.logger,
            payment_account_repo=self.payment_account_repo,
            request=request,
        )
        return await get_account_op.execute()

    async def update_payout_account_statement_descriptor(
        self, request: UpdatePayoutAccountStatementDescriptorRequest
    ) -> account_models.PayoutAccountInternal:
        if CACHE_KEY_PREFIX_GET_PAYOUT_ACCOUNT in enabled_cache_key_prefix_list():
            # invalidate cache
            cache = get_cache(app=PAYOUT_CACHE_APP_NAME)
            composed_cache_key = compose_cache_key(
                key=CACHE_KEY_PREFIX_GET_PAYOUT_ACCOUNT,
                args=(self,),
                kwargs={"request": request},
                use_hash=True,
            )
            if cache:
                await cache.invalidate(key=composed_cache_key)

        update_account_op = UpdatePayoutAccountStatementDescriptor(
            logger=self.logger,
            payment_account_repo=self.payment_account_repo,
            request=request,
        )
        return await update_account_op.execute()

    async def verify_payout_account(
        self, request: VerifyPayoutAccountRequest
    ) -> account_models.PayoutAccountInternal:
        if CACHE_KEY_PREFIX_GET_PAYOUT_ACCOUNT in enabled_cache_key_prefix_list():
            # invalidate cache
            cache = get_cache(app=PAYOUT_CACHE_APP_NAME)
            composed_cache_key = compose_cache_key(
                key=CACHE_KEY_PREFIX_GET_PAYOUT_ACCOUNT,
                args=(self,),
                kwargs={"request": request},
                use_hash=True,
            )
            if cache:
                await cache.invalidate(key=composed_cache_key)

        verify_account_op = VerifyPayoutAccount(
            logger=self.logger,
            payment_account_repo=self.payment_account_repo,
            request=request,
            stripe_client=self.stripe,
        )
        return await verify_account_op.execute()

    async def get_default_payout_card(
        self, request: GetDefaultPayoutCardRequest
    ) -> account_models.PayoutCardInternal:
        get_payout_card_op = GetDefaultPayoutCard(
            request=request,
            payout_card_repo=self.payout_card_repo,
            payout_method_repo=self.payout_method_repo,
            logger=self.logger,
        )
        return await get_payout_card_op.execute()

    async def create_payout_method(
        self, request: CreatePayoutMethodRequest
    ) -> Union[
        account_models.PayoutCardInternal, account_models.PayoutBankAccountInternal
    ]:
        if CACHE_KEY_PREFIX_GET_PAYOUT_ACCOUNT in enabled_cache_key_prefix_list():
            # invalidate cache
            cache = get_cache(app=PAYOUT_CACHE_APP_NAME)
            composed_cache_key = compose_cache_key(
                key=CACHE_KEY_PREFIX_GET_PAYOUT_ACCOUNT,
                args=(self,),
                kwargs={"request": request},
                use_hash=True,
            )
            if cache:
                await cache.invalidate(key=composed_cache_key)

        create_payout_method_op = CreatePayoutMethod(
            logger=self.logger,
            payment_account_repo=self.payment_account_repo,
            payment_account_edit_history_repo=self.payment_account_edit_history_repo,
            payout_method_miscellaneous_repo=self.payout_method_miscellaneous_repo,
            request=request,
            stripe=self.stripe,
        )
        return await create_payout_method_op.execute()

    async def get_payout_method(
        self, request: GetPayoutMethodRequest
    ) -> account_models.PayoutCardInternal:
        get_payout_method_op = GetPayoutMethod(
            logger=self.logger,
            payout_card_repo=self.payout_card_repo,
            payout_method_repo=self.payout_method_repo,
            request=request,
        )
        return await get_payout_method_op.execute()

    async def list_payout_method(
        self, request: ListPayoutMethodRequest
    ) -> account_models.PayoutMethodListInternal:
        list_payout_method_op = ListPayoutMethod(
            logger=self.logger,
            payout_card_repo=self.payout_card_repo,
            payout_method_repo=self.payout_method_repo,
            payment_account_repo=self.payment_account_repo,
            request=request,
        )
        return await list_payout_method_op.execute()

    async def create_standard_payout(
        self, request: CreateStandardPayoutRequest
    ) -> CreateStandardPayoutResponse:
        create_standard_payout_op = CreateStandardPayout(
            logger=self.logger,
            stripe_transfer_repo=self.stripe_transfer_repo,
            payment_account_repo=self.payment_account_repo,
            managed_account_transfer_repo=self.managed_account_transfer_repo,
            stripe=self.stripe,
            request=request,
        )
        return await create_standard_payout_op.execute()

    async def cancel_payout(self, request: CancelPayoutRequest) -> CancelPayoutResponse:
        cancel_payout_op = CancelPayout(
            logger=self.logger,
            stripe_transfer_repo=self.stripe_transfer_repo,
            payment_account_repo=self.payment_account_repo,
            stripe=self.stripe,
            request=request,
        )
        return await cancel_payout_op.execute()

    async def get_onboarding_requirements_by_stages(
        self, entity_type: PayoutTargetType, country_shortname: CountryCode
    ) -> account_models.VerificationRequirementsOnboarding:
        request: GetRequiredFieldsRequest = GetRequiredFieldsRequest(
            entity_type=entity_type, country_shortname=country_shortname
        )
        required_fields_op = GetPaymentsOnboardingRequirements(
            logger=self.logger, request=request
        )
        return await required_fields_op.execute()
