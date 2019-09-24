from app.payout.api.account.v1.models import PayoutAccount, PayoutMethodCard
from app.payout.core.account.types import (
    PayoutAccountInternal,
    VerificationRequirements,
    PayoutCardInternal,
)
from app.payout.types import PayoutExternalAccountType


def to_external_payout_account(internal_response: PayoutAccountInternal):
    return PayoutAccount(
        id=internal_response.payment_account.id,
        pgp_account_type=internal_response.payment_account.account_type,
        pgp_account_id=internal_response.payment_account.account_id,
        statement_descriptor=internal_response.payment_account.statement_descriptor,
        pgp_external_account_id=internal_response.pgp_external_account_id,
        verification_requirements=VerificationRequirements(
            **internal_response.verification_requirements.dict()
        )
        if internal_response.verification_requirements
        else None,
    )


def to_external_payout_method(internal_response: PayoutCardInternal):
    return PayoutMethodCard(
        **internal_response.dict(), type=PayoutExternalAccountType.CARD
    )
