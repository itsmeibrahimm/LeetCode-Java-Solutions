from app.payout.api.account.v1.models import PayoutAccount
from app.payout.core.account.types import (
    PayoutAccountInternal,
    VerificationRequirements,
)


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
