from typing import Mapping, Tuple

import payout_v1_client
from payout_v1_client import (
    CreatePayoutAccount,
    PayoutAccount,
    PayoutMethodCard,
    VerificationDetailsWithToken,
    CreatePayoutMethod,
    PayoutMethodList,
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
    return accounts_api.update_payout_account_statement_descriptor_with_http_info(
        payout_account_id=payout_account_id,
        statement_descriptor=statement_descriptor,
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
