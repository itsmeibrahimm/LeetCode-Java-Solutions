import json
from typing import Optional
from starlette.status import HTTP_400_BAD_REQUEST
from structlog import BoundLogger, get_logger
import stripe

from app.commons.utils.obj_util import get_obj_attr
from app.commons.providers.stripe.stripe_client import StripeAsyncClient
from app.commons.types import CountryCode
import app.payout.core.account.models as account_model
from app.payout.core.account.verification_error_mapping import (
    get_verification_error_from_pgp_code,
    error_to_action_mapping,
    document_error_mapping,
    document_error_to_action_mapping,
)
from app.payout.core.exceptions import PayoutError, PayoutErrorCode
from app.payout.models import PayoutAccountId, StripeBusinessType
from app.payout.repository.maindb.model.payment_account import PaymentAccount
from app.payout.repository.maindb.model.stripe_managed_account import (
    StripeManagedAccount,
)
from app.payout.repository.maindb.payment_account import (
    PaymentAccountRepositoryInterface,
)
from app.commons.providers.stripe import stripe_models as models

COUNTRY_TO_CURRENCY_CODE = {
    "US": "USD",
    "CA": "CAD",
    "United States": "USD",
    "Canada": "CAD",
    "Indonesia": "IDR",
    "ID": "IDR",
    "SG": "SGD",
    "MY": "MYR",
    "JP": "JPY",
    "AU": "AUD",
}

logger: BoundLogger = get_logger()


async def get_country_shortname(
    payment_account: Optional[PaymentAccount],
    payment_account_repository: PaymentAccountRepositoryInterface,
) -> Optional[str]:
    if payment_account and payment_account.account_id:
        stripe_managed_account = await payment_account_repository.get_stripe_managed_account_by_id(
            payment_account.account_id
        )
        if stripe_managed_account:
            return stripe_managed_account.country_shortname
    return None


async def get_country_by_payout_account_id(
    payout_account_id: PayoutAccountId,
    payment_account_repository: PaymentAccountRepositoryInterface,
) -> Optional[CountryCode]:
    payment_account = await payment_account_repository.get_payment_account_by_id(
        payout_account_id
    )
    if payment_account and payment_account.account_id:
        stripe_managed_account = await payment_account_repository.get_stripe_managed_account_by_id(
            payment_account.account_id
        )
        if stripe_managed_account:
            return CountryCode(stripe_managed_account.country_shortname)
    return None


async def get_stripe_managed_account_by_payout_account_id(
    payout_account_id: PayoutAccountId,
    payment_account_repository: PaymentAccountRepositoryInterface,
) -> Optional[StripeManagedAccount]:
    payment_account = await payment_account_repository.get_payment_account_by_id(
        payout_account_id
    )
    if payment_account and payment_account.account_id:
        stripe_managed_account = await payment_account_repository.get_stripe_managed_account_by_id(
            payment_account.account_id
        )
        return stripe_managed_account
    return None


def get_currency_code(country_shortname: str) -> str:
    """
    Shortname country code in 2-letter ISO format.  Return none if not valid country.
    """
    if country_shortname in COUNTRY_TO_CURRENCY_CODE:
        return COUNTRY_TO_CURRENCY_CODE[country_shortname]
    raise PayoutError(
        http_status_code=HTTP_400_BAD_REQUEST,
        error_code=PayoutErrorCode.UNSUPPORTED_COUNTRY,
        retryable=False,
    )


async def get_account_balance(
    stripe_managed_account: Optional[StripeManagedAccount], stripe: StripeAsyncClient
) -> int:
    """
    Get balance for stripe account, return 0 if sma is not created
    :param stripe_managed_account: stripe managed account
    :param stripe: StripeAsyncClient
    :return: balance amount
    """
    if stripe_managed_account:
        balance = await stripe.retrieve_balance(
            stripe_account=models.StripeAccountId(stripe_managed_account.stripe_id),
            country=models.CountryCode(stripe_managed_account.country_shortname),
        )
        try:
            return balance.available[0].amount
        except AttributeError:
            return 0
    return 0


def get_internal_verification_status(
    stripe_account: stripe.api_resources.Account = None
) -> Optional[account_model.VerificationStatus]:
    """
    Construct internal verification status from Stripe Account object

    Available status:
    - BLOCKED : If either charges or payouts are blocked for the account - details will be specified in additional_error_info
    - FIELDS_REQUIRED : If there's any field in past_due, currently_due, eventually_due
    - PENDING : If there's any field in pending_verification
    - VERIFIED : If no fields in any of the lists and not blocked

    :param stripe_account:
    :return: None if account is None, o/w return internal status
    """
    if not stripe_account:
        return None

    if not (stripe_account.payouts_enabled and stripe_account.charges_enabled):
        # if either one is disabled by stripe, the account is blocked
        return account_model.VerificationStatus.BLOCKED

    #
    # all types of stripe account:
    #   check the requirements field to infer the status
    #
    if not stripe_account.requirements:
        logger.warn(
            "[get_internal_verification_status] expect non-empty stripe requirements"
        )
        return None
    requirements = stripe_account.requirements
    has_past_due = len(requirements.get("past_due", [])) > 0
    has_currently_due = len(requirements.get("currently_due", [])) > 0
    has_eventually_due = len(requirements.get("eventually_due", [])) > 0
    has_pending_verification = len(requirements.get("pending_verification", [])) > 0

    if has_past_due or has_currently_due or has_eventually_due:
        return account_model.VerificationStatus.FIELDS_REQUIRED
    if has_pending_verification:
        return account_model.VerificationStatus.PENDING

    # nothing needed from stripe, mark as verified
    return account_model.VerificationStatus.VERIFIED


def parse_to_required_fields_obj(data, default=None, raise_exception=False):
    try:
        data_dict = None
        if type(data) is str:
            data_dict = json.loads(data)
        elif type(data) is dict:
            data_dict = data
        return account_model.VerificationRequirements.RequiredFields(**data_dict)
    except Exception as e:
        logger.warn("[parse_to_required_fields_obj] error parsing data", data=data)
        if raise_exception:
            raise e
        return default


def get_additional_error_info(stripe_account: stripe.api_resources.Account):
    stripe_requirements = get_obj_attr(stripe_account, "requirements", default={})
    error_info = {}
    if stripe_requirements.get("disabled_reason", None):
        error_info["disabled_reason"] = get_verification_error_from_pgp_code(
            stripe_requirements.get("disabled_reason")
        )
        error_info["action_to_enable"] = error_to_action_mapping(
            error_info["disabled_reason"]
        )

    entity_verification_error_code = None
    if get_obj_attr(stripe_account, "business_type") == StripeBusinessType.COMPANY:
        entity_verification_error_code = get_obj_attr(
            stripe_account, "company.verification.details_code"
        )
    elif get_obj_attr(stripe_account, "business_type") == StripeBusinessType.INDIVIDUAL:
        entity_verification_error_code = get_obj_attr(
            stripe_account, "individual.verification.details_code"
        )
    if entity_verification_error_code:
        error_info["document_error"] = document_error_mapping(
            entity_verification_error_code
        )
        error_info["document_error_action"] = document_error_to_action_mapping(
            error_info["document_error"]
        )
    return json.dumps(error_info)


def get_verification_requirements_from_stripe_obj(
    stripe_account: stripe.api_resources.Account, default=None, raise_exception=False
):
    try:
        stripe_account_requirements = get_obj_attr(
            stripe_account, "requirements", default=None
        )

        required_fields = parse_to_required_fields_obj(
            stripe_account_requirements.to_dict_recursive(), raise_exception=True
        )

        return account_model.VerificationRequirements(
            required_fields_v1=required_fields,
            verification_status=get_internal_verification_status(stripe_account),
            due_by=stripe_account_requirements.get("current_deadline", None),
            additional_error_info=get_additional_error_info(stripe_account),
        )
    except Exception as e:
        logger.warn(
            "[get_verification_requirements_from_stripe_obj] error parsing stripe_account to verification obj",
            data=stripe_account.to_dict_recursive(),
            error=e,
        )
        if raise_exception:
            raise e
        return default
