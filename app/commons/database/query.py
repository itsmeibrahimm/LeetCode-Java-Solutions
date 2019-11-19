from sqlalchemy import desc

from app.commons.database.client.interface import DBEngine


async def paged_query(
    engine: DBEngine, query, pk_attr, desc_order: bool = False, batch_size=500
):
    """

    Given an engine and query, will page through results with an iterator.
    Useful when the query may query for a lot of data and you want to page through it
    rather than getting all records at once and loading them into memory.

    The trade-off here is that the app will issue more queries to get the same amount of data.

    Returns a generator, so that this is happening under the hood

    """

    first_id = None
    while True:
        q = query
        if first_id is not None:
            q = (
                query.where(pk_attr < first_id)
                if desc_order
                else query.where(pk_attr > first_id)
            )
        rec = None
        # grab one more than the batch_size as a test to see if there is another page
        ordered_query = q.order_by(desc(pk_attr)) if desc_order else q.order_by(pk_attr)
        results = await engine.fetch_all(ordered_query.limit(batch_size + 1))
        if not results:
            break
        more_results = len(results) > batch_size
        if more_results:
            # the last record was used to see if there's another page of results, so chop it off
            # slightly inefficient, but inefficiency should be negligible
            results = results[0:-1]  # type: ignore
        for rec in results:
            yield rec
        # if the size of the result set was smaller than batch_size, then it means there are no more results
        if not more_results:
            break
        first_id = rec[pk_attr]
