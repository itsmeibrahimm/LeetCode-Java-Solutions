import psycopg2
import pytest
from asynctest import mock, CoroutineMock

from app.commons.core.errors import (
    DBConnectionError,
    DBDataError,
    DBOperationError,
    DBIntegrityError,
    DBProgrammingError,
    DBInternalError,
    DBNotSupportedError,
)
from app.commons.database.client.aiopg import AioConnection


class TestAioConnection:
    pytestmark = [pytest.mark.asyncio]

    psycopg2_errors = [
        psycopg2.InterfaceError,
        psycopg2.OperationalError,
        psycopg2.IntegrityError,
        psycopg2.ProgrammingError,
        psycopg2.DataError,
        psycopg2.InternalError,
        psycopg2.NotSupportedError,
    ]

    @pytest.fixture(autouse=True)
    def setup(self, mock_aio_engine):
        mock_aio_engine.closed.return_value = False
        mock_aio_engine.raw_engine.acquire = CoroutineMock()
        self.error_mapping = {
            psycopg2.InterfaceError: DBConnectionError,
            psycopg2.OperationalError: DBOperationError,
            psycopg2.IntegrityError: DBIntegrityError,
            psycopg2.ProgrammingError: DBProgrammingError,
            psycopg2.DataError: DBDataError,
            psycopg2.InternalError: DBInternalError,
            psycopg2.NotSupportedError: DBNotSupportedError,
        }

    @pytest.mark.parametrize("psycopg2_error", psycopg2_errors)
    async def test_handle_psycopg_errors(self, psycopg2_error, mock_aio_engine):
        with pytest.raises(self.error_mapping[psycopg2_error]):
            async with AioConnection(engine=mock_aio_engine) as conn:
                conn.raw_connection.execute = CoroutineMock(side_effect=psycopg2_error)
                conn.raw_connection.close = CoroutineMock()
                await conn.fetch_one("xxx")


@pytest.fixture
async def mock_aio_engine():
    with mock.patch("app.commons.database.client.aiopg.AioEngine") as mock_aio_engine:
        yield mock_aio_engine
