import logging
import time
from typing import List, Mapping, Optional, Tuple

import payout_v0_client
from payout_v0_client import (
    ApiException,
    PaymentAccount,
    PaymentAccountCreate,
    PaymentAccountUpdate,
    StripeManagedAccountCreate,
    StripeManagedAccount,
    StripeManagedAccountUpdate,
)

logger = logging.getLogger(__name__)


def current_time_ms():
    return time.time() * 1000


def decorate_api_call(func):
    def echo_func(*args, **kwargs):
        if "_return_http_data_only" not in kwargs:
            kwargs["_return_http_data_only"] = False

        if "_preload_content" not in kwargs:
            kwargs["_preload_content"] = True

        if "_request_timeout" not in kwargs:
            kwargs["_request_timeout"] = 5  # seconds

        logger.info(f">>>>>>>>>>>> Calling [{func.__name__}] with arguments={kwargs}")

        start = current_time_ms()
        try:
            result = func(*args, **kwargs)
            elapsed = current_time_ms() - start
            logger.info(f">>>>>>>>>>>> Execution completed in={elapsed}ms")
            return result
        except Exception:
            elapsed = current_time_ms() - start
            logger.info(f">>>>>>>>>>>> Failed in={elapsed}ms")
            raise

    return echo_func


@decorate_api_call
def create_payment_account(
    request: PaymentAccountCreate,
    accounts_api: payout_v0_client.AccountsV0Api,
    **kwargs,
) -> Tuple[PaymentAccount, int, Mapping]:
    return accounts_api.create_payment_account_with_http_info(request, **kwargs)


@decorate_api_call
def get_payment_account_by_id(
    payment_account_id: int, accounts_api: payout_v0_client.AccountsV0Api, **kwargs
) -> Tuple[Optional[PaymentAccount], int, Mapping]:
    try:
        return accounts_api.get_payment_account_by_id_with_http_info(
            account_id=payment_account_id, **kwargs
        )
    except ApiException as e:
        if e.status == 404:  # handle 404 and return None
            return None, e.status, e.headers
        raise


@decorate_api_call
def get_payment_account_by_account_type_account_id(
    account_type: str,
    account_id: int,
    accounts_api: payout_v0_client.AccountsV0Api,
    **kwargs,
) -> Tuple[List[PaymentAccount], int, Mapping]:
    return accounts_api.get_payment_accounts_by_account_type_account_id_with_http_info(
        stripe_account_type=account_type, stripe_account_id=account_id, **kwargs
    )


@decorate_api_call
def update_payment_account_by_id(
    payment_account_id: int,
    request: PaymentAccountUpdate,
    accounts_api: payout_v0_client.AccountsV0Api,
    **kwargs,
) -> Tuple[Optional[PaymentAccount], int, Mapping]:
    try:
        return accounts_api.update_payment_account_by_id_with_http_info(
            account_id=payment_account_id, payment_account_update=request, **kwargs
        )
    except ApiException as e:
        if e.status == 404:  # handle 404 and return None
            return None, e.status, e.headers
        raise


@decorate_api_call
def create_stripe_managed_account(
    request: StripeManagedAccountCreate,
    accounts_api: payout_v0_client.AccountsV0Api,
    **kwargs,
) -> Tuple[StripeManagedAccount, int, Mapping]:
    return accounts_api.create_stripe_managed_account_with_http_info(
        stripe_managed_account_create=request, **kwargs
    )


@decorate_api_call
def get_stripe_managed_account_by_id(
    stripe_managed_account_id: int,
    accounts_api: payout_v0_client.AccountsV0Api,
    **kwargs,
) -> Tuple[Optional[StripeManagedAccount], int, Mapping]:
    try:
        return accounts_api.get_stripe_managed_account_by_id_with_http_info(
            stripe_managed_account_id=stripe_managed_account_id, **kwargs
        )
    except ApiException as e:
        if e.status == 404:  # handle 404 and return None
            return None, e.status, e.headers
        raise


@decorate_api_call
def update_stripe_managed_account_by_id(
    stripe_managed_account_id: int,
    request: StripeManagedAccountUpdate,
    accounts_api: payout_v0_client.AccountsV0Api,
    **kwargs,
) -> Tuple[Optional[StripeManagedAccount], int, Mapping]:
    try:
        return accounts_api.update_stripe_managed_account_by_id_with_http_info(
            stripe_managed_account_id=stripe_managed_account_id,
            stripe_managed_account_update=request,
            **kwargs,
        )
    except ApiException as e:
        if e.status == 404:  # handle 404 and return None
            return None, e.status, e.headers
        raise
