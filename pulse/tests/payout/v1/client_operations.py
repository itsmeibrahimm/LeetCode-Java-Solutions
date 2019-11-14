from typing import Mapping, Tuple

import payout_v1_client
from payout_v1_client import (
    CreatePayoutAccount,
    PayoutAccount,
    PayoutMethodCard,
    VerificationDetailsWithToken,
    CreatePayoutMethod,
    PayoutMethodList,
    UpdatePayoutAccountStatementDescriptor,
    PaymentEligibility,
    InstantPayoutCreate,
    InstantPayout,
)
from tests.utils import decorate_api_call


@decorate_api_call
def create_payout_account(
    request: CreatePayoutAccount, accounts_api: payout_v1_client.AccountsV1Api, **kwargs
) -> Tuple[PayoutAccount, int, Mapping]:
    return accounts_api.create_payout_account_with_http_info(
        create_payout_account=request, **kwargs
    )


@decorate_api_call
def get_payout_account(
    payout_account_id: int, accounts_api: payout_v1_client.AccountsV1Api, **kwargs
) -> Tuple[PayoutAccount, int, Mapping]:
    return accounts_api.get_payout_account_with_http_info(
        payout_account_id=payout_account_id, **kwargs
    )


@decorate_api_call
def update_payout_account_statement_descriptor(
    payout_account_id: int,
    statement_descriptor: str,
    accounts_api: payout_v1_client.AccountsV1Api,
    **kwargs,
) -> Tuple[PayoutAccount, int, Mapping]:
    update_statement_descriptor = UpdatePayoutAccountStatementDescriptor(
        statement_descriptor=statement_descriptor
    )
    return accounts_api.update_payout_account_statement_descriptor_with_http_info(
        payout_account_id=payout_account_id,
        update_payout_account_statement_descriptor=update_statement_descriptor,
        **kwargs,
    )


@decorate_api_call
def verify_payout_account_legacy(
    payout_account_id: int,
    verification_details_with_token: VerificationDetailsWithToken,
    accounts_api: payout_v1_client.AccountsV1Api,
    **kwargs,
) -> Tuple[PayoutAccount, int, Mapping]:
    return accounts_api.verify_payout_account_legacy_with_http_info(
        payout_account_id=payout_account_id,
        verification_details_with_token=verification_details_with_token,
        **kwargs,
    )


@decorate_api_call
def create_payout_method(
    payout_account_id: int,
    request: CreatePayoutMethod,
    accounts_api: payout_v1_client.AccountsV1Api,
    **kwargs,
) -> Tuple[PayoutMethodCard, int, Mapping]:
    return accounts_api.create_payout_method_with_http_info(
        payout_account_id=payout_account_id, create_payout_method=request, **kwargs
    )


@decorate_api_call
def get_payout_method(
    payout_account_id: int,
    payout_method_id: int,
    accounts_api: payout_v1_client.AccountsV1Api,
    **kwargs,
) -> Tuple[PayoutMethodCard, int, Mapping]:
    return accounts_api.get_payout_method_with_http_info(
        payout_account_id=payout_account_id, payout_method_id=payout_method_id, **kwargs
    )


@decorate_api_call
def list_payout_method(
    payout_account_id: int, accounts_api: payout_v1_client.AccountsV1Api, **kwargs
) -> Tuple[PayoutMethodList, int, Mapping]:
    return accounts_api.list_payout_method_with_http_info(
        payout_account_id=payout_account_id, **kwargs
    )


@decorate_api_call
def check_instant_payout_eligibility(
    payout_account_id: int,
    local_start_of_day: int,
    instant_payout_api: payout_v1_client.InstantPayoutsV1Api,
    **kwargs,
) -> Tuple[PaymentEligibility, int, Mapping]:
    return instant_payout_api.check_instant_payout_eligibility_with_http_info(
        payout_account_id=payout_account_id,
        local_start_of_day=local_start_of_day,
        **kwargs,
    )


@decorate_api_call
def submit_instant_payout(
    instant_payout_create: InstantPayoutCreate,
    instant_payout_api: payout_v1_client.InstantPayoutsV1Api,
    **kwargs,
) -> Tuple[InstantPayout, int, Mapping]:
    return instant_payout_api.submit_instant_payout_with_http_info(
        instant_payout_create=instant_payout_create, **kwargs
    )
