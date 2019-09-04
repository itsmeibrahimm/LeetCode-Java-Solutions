from pydantic import errors
import json
from typing import Any


class BankDBBrokenJson:
    """
    In bankdb, some tables are messed up with typing, for example:
        bank_service=> \\d stripe_payout_requests
              Column       |            Type             | ...
        -------------------+-----------------------------+-----
         id                | integer                     |
         payout_id         | integer                     |
         idempotency_key   | character varying           |
         payout_method_id  | integer                     |
         response          | json                        |
         created_at        | timestamp without time zone |
         received_at       | timestamp without time zone |
         updated_at        | timestamp without time zone |
         stripe_payout_id  | character varying           |
         request           | json                        |
         status            | character varying           |
         events            | json                        |
         stripe_account_id | character varying           |

    when inserting rows to the table, some json columns were saved as string, e.g.
    https://github.com/doordash/bank-service/blob/99de03d82e132d599057bb5a8218eb661976418f/bankservice/adapters/database/repositories/stripe_payout_requests/stripe_payout_request_repository.py#L32

    This new type definition will check if the field was saved as string, if so, try to convert, otherwise, just return
    """

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v: Any) -> Any:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except ValueError:
                raise errors.JsonError()
            except TypeError:
                raise errors.JsonTypeError()

        return v
