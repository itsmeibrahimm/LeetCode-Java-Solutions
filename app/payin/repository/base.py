from dataclasses import InitVar, dataclass
from gino import GinoConnection
from gino.transaction import GinoTransaction
from typing import Tuple

from app.commons.context.app_context import AppContext
from app.commons.database.model import Database
from app.commons.utils.dataclass_extensions import no_init_field


@dataclass
class PayinDBRepository:
    """
    Base repository containing Payin_PaymentDB connection resources
    """

    context: InitVar[AppContext]  # constructor use only, not persisted in repo instance
    main_database: Database = no_init_field()
    payment_database: Database = no_init_field()

    def __post_init__(self, context: AppContext):
        self.main_database = context.payin_maindb
        self.payment_database = context.payin_paymentdb

    async def get_payment_database_connection(self) -> GinoConnection:
        return await self.payment_database.master().acquire()

    async def close_payment_database_connection(self, connection: GinoConnection):
        await connection.release()

    async def get_transaction(self, connection: GinoConnection):
        return await connection.transaction()

    async def get_payment_database_connection_and_transaction(
        self
    ) -> Tuple[GinoConnection, GinoTransaction]:
        connection = await self.get_payment_database_connection()

        try:
            transaction = await self.get_transaction(connection)
        except Exception as transaction_exception:
            # Error getting transaction.  Try to clean up connection so it is not lost.
            # TODO catch if error comes from closing connection and log it, allowing us to return original exception.
            self.close_payment_database_connection(connection)
            raise transaction_exception

        return (connection, transaction)
