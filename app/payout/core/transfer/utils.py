from datetime import datetime, timedelta, tzinfo
from typing import Tuple, Optional, List

import pytz

from app.commons.context.logger import get_logger
from app.commons.providers.dsj_client import DSJClient, DSJRESTCallException
from app.payout.repository.maindb.model.transfer import Transfer, TransferStatus
from app.payout.repository.maindb.stripe_transfer import (
    StripeTransferRepositoryInterface,
)
from app.payout.models import TransferMethodType
from app.commons.runtime import runtime

log = get_logger(__name__)


async def determine_transfer_status_from_latest_submission(
    transfer: Transfer, stripe_transfer_repo: StripeTransferRepositoryInterface
):
    """
    Returns the transfer status corresponding to latest gateways specific status for this transfer id
    """

    if transfer.deleted_at:
        return TransferStatus.DELETED

    if not transfer.method:
        return TransferStatus.NEW

    if transfer.method == TransferMethodType.DOORDASH_PAY and transfer.submitted_at:
        return TransferStatus.PAID

    if transfer.amount == 0 and transfer.submitted_at:
        return TransferStatus.PAID

    if transfer.method == TransferMethodType.STRIPE:
        stripe_transfer = await stripe_transfer_repo.get_latest_stripe_transfer_by_transfer_id(
            transfer_id=transfer.id
        )
        if stripe_transfer:
            return TransferStatus.stripe_status_to_transfer_status(
                stripe_transfer.stripe_status
            )
    else:
        if transfer.submitted_at:
            return TransferStatus.PAID
    return TransferStatus.NEW


def get_last_week(timezone_info: tzinfo, inclusive_end: bool):
    """
    Get the previous Monday to Sunday pay period (for dashers and merchants)
    """
    # Choose some datetime in the previous week
    dt = first_instant_of_week(timezone_info=timezone_info) - timedelta(days=1)

    return get_start_and_end_of_week(
        dt=dt, timezone_info=timezone_info, inclusive_end=inclusive_end
    )


def first_instant_of_week(timezone_info: tzinfo):
    """
    @return the datetime adjusted to the first microsecond of the first day of the week
    """
    # reduce to date
    local_date = datetime.utcnow().astimezone(timezone_info).date()

    # date arithmetic is safe from DST problems
    monday = local_date - timedelta(days=local_date.weekday())

    return get_local_datetime(
        year=monday.year,
        month=monday.month,
        day=monday.day,
        timezone_info=timezone_info,
    )


def get_local_datetime(year: int, month: int, day: int, timezone_info: tzinfo):
    """
    Utility function that should be used to create a new local datetime object.

    Takes in the same parameters as datetime.datetime's constructor and returns
    a datetime object with the correct local time.
    """
    if timezone_info is None:
        timezone_info = pytz.timezone("US/Pacific")
    naive_local_dt = datetime(year=year, month=month, day=day, tzinfo=timezone_info)
    # ignore typing check here since DstTzInfo is not exposed externally and tzinfo does not have normalize function
    real_local_dt = timezone_info.normalize(naive_local_dt)  # type: ignore
    if real_local_dt != naive_local_dt:
        # that means there was a DST change at some point
        real_local_dt = real_local_dt.replace(
            year=year, month=month, day=day, hour=0, minute=0, second=0, microsecond=0
        )
    return real_local_dt


def get_start_and_end_of_week(dt: datetime, inclusive_end: bool, timezone_info: tzinfo):
    """
    Get the start and end of a week (Monday-Sunday)
    By default, end is midnight of Sunday, if inclusive_end then it's midnight of Monday
    """
    # Set default date to last Monday to Sunday
    # NOTE: working with naive local dates, e.g. 2014/3/15
    if timezone_info:
        dt = dt.astimezone(timezone_info)

    assert dt.tzinfo

    thedate = dt.date()  # type datetime.date

    monday = thedate - timedelta(days=thedate.weekday())  # week starts monday
    sunday = monday + timedelta(days=6)

    if inclusive_end:
        # make end_datetime the second Monday's midnight, for easier filtering
        sunday += timedelta(days=1)

    # convert date to datetime (time=00:00:00) .. and localize to a timezone
    start_time = get_local_datetime(
        monday.year, monday.month, monday.day, timezone_info=timezone_info
    )
    end_time = get_local_datetime(
        sunday.year, sunday.month, sunday.day, timezone_info=timezone_info
    )
    return start_time, end_time


async def get_target_metadata(
    payment_account_id: int, dsj_client: DSJClient
) -> Tuple[Optional[str], Optional[int], Optional[str], Optional[int]]:
    target_type = None
    target_id = None
    statement_descriptor = None
    business_id = None

    if runtime.get_bool(
        "payout/feature-flags/enable_dsj_api_integration_for_weekly_payout.bool", False
    ):
        try:
            response = await dsj_client.get(
                f"/v1/payment_accounts/{payment_account_id}/tr_metadata", {}
            )

            if response:
                statement_descriptor = response["statement_descriptor"]
                target_type = response["target_type"]
                target_id = response["target_id"]
                if "business_id" in response:
                    business_id = response["business_id"]
        except DSJRESTCallException as e:
            # log for monitor purpose
            log.info(
                "DSJRESTCallException: failed to retrieve target_metadata from dsj",
                payment_account_id=payment_account_id,
                error_msg=e,
            )
            raise
    else:
        weekly_create_transfers_dict_list = runtime.get_json(
            "payout/feature-flags/enable_payment_service_weekly_create_transfers_list.json",
            [],
        )
        for weekly_create_transfer_dict_obj in weekly_create_transfers_dict_list:
            value_dict = weekly_create_transfer_dict_obj.get(
                str(payment_account_id), None
            )
            if value_dict:
                target_type = value_dict.get("target_type")
                target_id = value_dict.get("target_id")
                statement_descriptor = value_dict.get("statement_descriptor")
                break

    return target_type, target_id, statement_descriptor, business_id


def start_and_end_of_date(date: datetime, timezone_info: tzinfo):
    """
    Returns datetimes (in tzinfo) corresponding to the start and end of this date
    (midnight). On a DST day this could actually be 23 or 25 hours
    """
    next_date = date + timedelta(days=1)

    return (
        get_local_datetime(
            date.year, date.month, date.day, timezone_info=timezone_info
        ),
        get_local_datetime(
            next_date.year, next_date.month, next_date.day, timezone_info=timezone_info
        ),
    )


async def get_payment_account_ids_with_biz_id(
    business_id: int, dsj_client: DSJClient
) -> List[int]:
    if runtime.get_bool(
        "payout/feature-flags/enable_dsj_api_integration_for_weekly_payout.bool", False
    ):
        try:
            response = await dsj_client.get(
                "/v1/payment_accounts/", {"business_id": business_id}
            )
            if response:
                payment_account_ids = response["payment_account_ids"]
                return payment_account_ids

        except DSJRESTCallException as e:
            # log for monitor purpose
            log.info(
                "DSJRESTCallException: failed to retrieve payment account ids with biz id from dsj",
                business_id=business_id,
                error_msg=e,
            )
            raise
    return []
