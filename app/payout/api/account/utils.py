from typing import Union

from app.payout.api.account.v1 import models as account_api_models
from app.payout.core.account import models as account_models
from app.payout.models import PayoutExternalAccountType


def to_external_payout_account(internal_response: account_models.PayoutAccountInternal):
    return account_api_models.PayoutAccount(
        id=internal_response.payment_account.id,
        pgp_account_type=internal_response.payment_account.account_type,
        pgp_account_id=internal_response.payment_account.account_id,
        statement_descriptor=internal_response.payment_account.statement_descriptor,
        pgp_external_account_id=internal_response.pgp_external_account_id,
        verification_requirements=account_api_models.VerificationRequirements(
            **internal_response.verification_requirements.dict()
        )
        if internal_response.verification_requirements
        else None,
    )


def to_external_payout_method(
    internal_response: Union[
        account_models.PayoutCardInternal, account_models.PayoutBankAccountInternal
    ]
):
    if isinstance(internal_response, account_models.PayoutCardInternal):
        return account_api_models.PayoutMethodCard(
            **internal_response.dict(), type=PayoutExternalAccountType.CARD
        )
    elif isinstance(internal_response, account_models.PayoutBankAccountInternal):
        return account_api_models.PayoutMethodBankAccount(
            **internal_response.dict(), type=PayoutExternalAccountType.BANK_ACCOUNT
        )
