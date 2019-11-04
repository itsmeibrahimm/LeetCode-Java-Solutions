import asyncio
from functools import wraps
import psycopg2
from psycopg2.errorcodes import UNIQUE_VIOLATION, LOCK_NOT_AVAILABLE

from app.commons.core.errors import (
    DBConnectionError,
    DBOperationError,
    DBIntegrityError,
    DBProgrammingError,
    DBDataError,
    DBNotSupportedError,
    DBInternalError,
    DBIntegrityUniqueViolationError,
    DBOperationLockNotAvailableError,
)


def translate_db_error(func):
    """Translate DB Errors into payment processor layer errors.

    This function should be used to decorate app.commons.database.client.aiopg.AioConnection methods, to translate
    psycopg errors into payment processor layer general db errors.

    In fact, psycopg follows DB API 2.0 specification(https://www.python.org/dev/peps/pep-0249/), which defines db
    errors into the following structure,
        StandardError
            - Warning
            - Error
                - InterfaceError
                - DatabaseError
                    - DataError
                    - OperationalError
                    - IntegrityError
                    - InternalError
                    - ProgrammingError
                    - NotSupportedError

    The current error mapping simply maps psycopg errors into payment errors. For future swapping with or adding new db
    drivers, should map to the same processor layer db errors, and keep hiding the bottom db errors from above layer.

    Details of db error mapping can be found at,
    https://github.com/doordash/money-uml/blob/master/payout/puml-png/processor_layer_errors.png.
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        if not asyncio.iscoroutinefunction(func):
            raise Exception(
                "translate_db_error decorator can only be used in async functions."
            )
        try:
            return await func(*args, **kwargs)
        except psycopg2.InterfaceError as e:
            raise DBConnectionError(e.pgerror) from e
        except psycopg2.OperationalError as e:
            if e.pgcode == LOCK_NOT_AVAILABLE:
                raise DBOperationLockNotAvailableError from e
            raise DBOperationError(e.pgerror) from e
        except psycopg2.IntegrityError as e:
            if e.pgcode == UNIQUE_VIOLATION:
                raise DBIntegrityUniqueViolationError from e
            raise DBIntegrityError(e.pgerror) from e
        except psycopg2.ProgrammingError as e:
            raise DBProgrammingError(e.pgerror) from e
        except psycopg2.DataError as e:
            raise DBDataError(e.pgerror) from e
        except psycopg2.InternalError as e:
            raise DBInternalError(e.pgerror) from e
        except psycopg2.NotSupportedError as e:
            raise DBNotSupportedError(e.pgerror) from e

    return wrapper
