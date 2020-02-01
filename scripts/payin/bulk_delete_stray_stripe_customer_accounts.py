import asyncio

from app.commons.context.app_context import AppContext
from app.commons.context.logger import get_logger
from app.commons.context.req_context import build_req_context
from app.commons.jobs.pool import JobPool
from app.commons.types import CountryCode
from app.payin.core.exceptions import PayinErrorCode, PayerDeleteError
from app.payin.core.payer.payer_client import PayerClient
from app.payin.core.payer.types import (
    DeletePayerRequestStatus,
    DeletePayerRedactingText,
)
from app.payin.repository.payer_repo import (
    DeletePayerRequestMetadataDbEntity,
    PayerRepository,
)

__all__ = ["run_delete_stripe_customers"]

log = get_logger("bulk_delete_stray_stripe_customer_accounts")


async def _delete_stripe_customer(
    app_context: AppContext, job_pool: JobPool, chunk_size: int = 5
):
    log.info("Attempting to process delete payer requests metadata")

    payer_repo = PayerRepository(context=app_context)
    req_context = build_req_context(app_context)
    payer_client = PayerClient(
        app_ctxt=app_context,
        log=req_context.log,
        payer_repo=payer_repo,
        stripe_async_client=req_context.stripe_async_client,
    )

    list_delete_payer_request_metadata = await payer_client.find_delete_payer_requests_metadata_by_status(
        DeletePayerRequestStatus.IN_PROGRESS
    )
    total_delete_payer_requests_metadata = 0
    failed_delete_payer_requests_metadata = []
    for delete_payer_request_metadata in list_delete_payer_request_metadata:
        while job_pool.active_job_count >= chunk_size:
            log.info(
                f"Waiting for active jobs {job_pool.active_job_count} reduced to be lower than limit {chunk_size}"
            )
            await asyncio.sleep(0.1)

        total_delete_payer_requests_metadata += 1

        async def job_callback(res, err, ctx):
            if err:
                log.error(
                    f"Processing delete payer requests metadata failed for consumer_id={delete_payer_request_metadata.consumer_id}",
                    exc_info=err[0],
                )  # err = (exec, traceback)
                failed_delete_payer_requests_metadata.append(
                    delete_payer_request_metadata.client_request_id
                )
            else:
                log.info(
                    f"Processing delete payer requests metadata succeeded for consumer_id={delete_payer_request_metadata.consumer_id}"
                )

        await job_pool.spawn(
            delete_stripe_customer(
                delete_payer_request_metadata=delete_payer_request_metadata,
                payer_client=payer_client,
            ),
            cb=job_callback,
        )

    # wait for all spawned capture tasks finish
    await job_pool.join()

    log.info(
        f"Delete payer requests metadata run for total {total_delete_payer_requests_metadata}"
    )

    if failed_delete_payer_requests_metadata:
        log.warning(
            f"Failed to process delete payer requests for ids={failed_delete_payer_requests_metadata}"
        )


def run_delete_stripe_customers(
    *, app_context: AppContext, job_pool: JobPool, chunk_size: int = 5
):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        _delete_stripe_customer(
            app_context=app_context, job_pool=job_pool, chunk_size=chunk_size
        )
    )


async def delete_stripe_customer(
    delete_payer_request_metadata: DeletePayerRequestMetadataDbEntity,
    payer_client: PayerClient,
):
    stripe_customers = await payer_client.pgp_get_customers(
        email=delete_payer_request_metadata.email,
        country_code=CountryCode(delete_payer_request_metadata.country_code),
    )

    log.info(
        "[delete_stripe_customer] Fetched stripe_customer_ids for consumer",
        consumer_id=delete_payer_request_metadata.consumer_id,
        stripe_customer_ids=[
            stripe_customer.id for stripe_customer in stripe_customers
        ],
        stripe_country=delete_payer_request_metadata.country_code,
    )

    all_deletes_successful = True

    for stripe_customer in stripe_customers:
        if stripe_customer.created > delete_payer_request_metadata.created_at:
            log.info(
                "[delete_stripe_customer] Cannot delete stripe customer since its created after previous delete payer request",
                consumer_id=delete_payer_request_metadata.consumer_id,
                stripe_customer_id=stripe_customer.id,
                stripe_country=delete_payer_request_metadata.country_code,
            )
            continue
        try:
            log.info(
                "[delete_stripe_customer] Trying to delete customer from stripe",
                consumer_id=delete_payer_request_metadata.consumer_id,
                stripe_customer_id=stripe_customer.id,
                stripe_country=delete_payer_request_metadata.country_code,
            )
            stripe_response = await payer_client.pgp_delete_customer(
                CountryCode(delete_payer_request_metadata.country_code),
                stripe_customer.id,
            )
            if stripe_response and stripe_response.deleted:
                log.info(
                    "[delete_stripe_customer] Successfully deleted customer from stripe",
                    consumer_id=delete_payer_request_metadata.consumer_id,
                    stripe_customer_id=stripe_customer.id,
                    stripe_country=delete_payer_request_metadata.country_code,
                )
            else:
                log.warning(
                    "[delete_stripe_customer] Delete customer from stripe unsuccessful",
                    consumer_id=delete_payer_request_metadata.consumer_id,
                    stripe_customer_id=stripe_customer.id,
                    stripe_country=delete_payer_request_metadata.country_code,
                )
                all_deletes_successful = False
        except PayerDeleteError as payer_delete_error:
            log.exception(
                "[delete_stripe_customer] Exception occurred while deleting customer from stripe",
                consumer_id=delete_payer_request_metadata.consumer_id,
                stripe_customer_id=stripe_customer.id,
                stripe_country=delete_payer_request_metadata.country_code,
            )
            if (
                payer_delete_error.error_code
                != PayinErrorCode.PAYER_DELETE_STRIPE_ERROR_NOT_FOUND
            ):
                all_deletes_successful = False

    if all_deletes_successful:
        delete_payer_request_metadata.status = DeletePayerRequestStatus.SUCCEEDED

    try:
        await payer_client.update_delete_payer_request_metadata(
            client_request_id=delete_payer_request_metadata.client_request_id,
            status=DeletePayerRequestStatus.SUCCEEDED
            if all_deletes_successful
            else delete_payer_request_metadata.status,
            email=DeletePayerRedactingText.REDACTED
            if all_deletes_successful
            else delete_payer_request_metadata.email,
        )
    except PayerDeleteError:
        log.exception(
            "[delete_stripe_customer] Error occurred with updating delete payer request metadata",
            client_request_id=delete_payer_request_metadata.client_request_id,
            consumer_id=delete_payer_request_metadata.consumer_id,
        )
        raise
