from datetime import datetime, timedelta, tzinfo
from typing import Tuple

import pytz
from app.payout.repository.maindb.model.transfer import Transfer, TransferStatus
from app.payout.repository.maindb.stripe_transfer import (
    StripeTransferRepositoryInterface,
)
from app.payout.models import TransferMethodType, PayoutTargetType


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


def get_target_type_and_target_id() -> Tuple[PayoutTargetType, int]:
    # todo: call upstream team external api to update logic
    return PayoutTargetType.STORE, 12345
