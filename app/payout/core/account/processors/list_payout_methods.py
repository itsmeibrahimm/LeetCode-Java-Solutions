from structlog.stdlib import BoundLogger
from typing import Union, Optional, List

from app.commons.api.models import DEFAULT_INTERNAL_EXCEPTION, PaymentException
from app.commons.core.processor import AsyncOperation, OperationRequest
import app.payout.core.account.models as account_models
from app.commons.types import CountryCode, Currency
from app.payout.core.account.utils import COUNTRY_TO_CURRENCY_CODE
from app.payout.core.exceptions import (
    payout_account_not_found_error,
    pgp_account_not_found_error,
)
from app.payout.repository.bankdb.payout_card import PayoutCardRepositoryInterface
from app.payout.repository.bankdb.payout_method import PayoutMethodRepositoryInterface
from app.payout.models import PayoutAccountId, PayoutExternalAccountType
from app.payout.repository.maindb.payment_account import (
    PaymentAccountRepositoryInterface,
)


class ListPayoutMethodRequest(OperationRequest):
    payout_account_id: PayoutAccountId
    payout_method_type: PayoutExternalAccountType = PayoutExternalAccountType.CARD
    limit: Optional[int] = 50


class ListPayoutMethod(
    AsyncOperation[ListPayoutMethodRequest, account_models.PayoutMethodListInternal]
):
    """
    Processor to get a payout method
    """

    payout_card_repo: PayoutCardRepositoryInterface
    payout_method_repo: PayoutMethodRepositoryInterface
    payment_account_repo: PaymentAccountRepositoryInterface

    def __init__(
        self,
        request: ListPayoutMethodRequest,
        *,
        payout_card_repo: PayoutCardRepositoryInterface,
        payout_method_repo: PayoutMethodRepositoryInterface,
        payment_account_repo: PaymentAccountRepositoryInterface,
        logger: BoundLogger = None,
    ):
        super().__init__(request, logger)
        self.request = request
        self.payout_card_repo = payout_card_repo
        self.payout_method_repo = payout_method_repo
        self.payment_account_repo = payment_account_repo

    async def _execute(self) -> account_models.PayoutMethodListInternal:
        # get a list of payout card when client search for card type or no type
        payout_card_internal_list: List[account_models.PayoutCardInternal] = []
        payout_bank_account_internal_list: List[
            account_models.PayoutBankAccountInternal
        ] = []
        if (
            self.request.payout_method_type == PayoutExternalAccountType.CARD
            or not self.request.payout_method_type
        ):
            payout_method_list = await self.payout_method_repo.list_payout_methods_by_payout_account_id(
                payout_account_id=self.request.payout_account_id,
                payout_method_type=self.request.payout_method_type,
                limit=self.request.limit,
            )

            payout_card_ids = [payout_method.id for payout_method in payout_method_list]
            payout_card_list = await self.payout_card_repo.list_payout_cards_by_ids(
                payout_card_ids
            )
            payout_card_map = {
                payout_card.id: payout_card for payout_card in payout_card_list
            }
            for payout_method in payout_method_list:
                card = payout_card_map.get(payout_method.id, None)
                if not card:
                    self.logger.warning(
                        "payout_card does not exist for payout_method",
                        payout_method_id=payout_method.id,
                    )
                else:
                    payout_card_internal = account_models.PayoutCardInternal(
                        stripe_card_id=card.stripe_card_id,
                        last4=card.last4,
                        brand=card.brand,
                        exp_month=card.exp_month,
                        exp_year=card.exp_year,
                        fingerprint=card.fingerprint,
                        payout_account_id=payout_method.payment_account_id,
                        currency=payout_method.currency,
                        country=payout_method.country,
                        is_default=payout_method.is_default,
                        id=payout_method.id,
                        token=payout_method.token,
                        created_at=payout_method.created_at,
                        updated_at=payout_method.updated_at,
                        deleted_at=payout_method.deleted_at,
                    )
                    payout_card_internal_list.append(payout_card_internal)

        # get the default bank account from stripe_managed_account when client search for bank_account type or no type
        if (
            self.request.payout_method_type == PayoutExternalAccountType.BANK_ACCOUNT
            or not self.request.payout_method_type
        ):
            payout_account = await self.payment_account_repo.get_payment_account_by_id(
                self.request.payout_account_id
            )
            if not payout_account:
                raise payout_account_not_found_error()
            if not payout_account.account_id:
                raise pgp_account_not_found_error()

            stripe_managed_account = await self.payment_account_repo.get_stripe_managed_account_by_id(
                payout_account.account_id
            )
            if not stripe_managed_account:
                raise pgp_account_not_found_error()
            payout_bank_account_internal_list = [
                account_models.PayoutBankAccountInternal(
                    payout_account_id=self.request.payout_account_id,
                    bank_last4=stripe_managed_account.default_bank_last_four,
                    bank_name=stripe_managed_account.default_bank_name,
                    fingerprint=stripe_managed_account.fingerprint,
                    country=CountryCode(
                        stripe_managed_account.country_shortname.upper()
                    ),
                    currency=Currency(
                        COUNTRY_TO_CURRENCY_CODE[
                            stripe_managed_account.country_shortname.upper()
                        ].lower()
                    ),
                )
            ]

        return account_models.PayoutMethodListInternal(
            card_list=payout_card_internal_list,
            bank_account_list=payout_bank_account_internal_list,
        )

    def _handle_exception(
        self, internal_exec: BaseException
    ) -> Union[PaymentException, account_models.PayoutMethodListInternal]:
        raise DEFAULT_INTERNAL_EXCEPTION
