from dataclasses import dataclass

from gino import Gino

from app.commons.utils.dataclass_extensions import no_init_field
from app.payin.repository.maindb.stripe_customer_repository import (
    StripeCustomerRepository,
)
from app.payin.repository.paymentdb.payer_repository import PayerRepository
from app.payin.repository.paymentdb.pgp_customer_repository import PgpCustomerRepository


@dataclass
class PayinRepositories:
    _maindb_connection: Gino
    _paymentdb_connection: Gino

    payer_repo: PayerRepository = no_init_field()
    pgp_customer_repo: PgpCustomerRepository = no_init_field()
    stripe_customer_repo: StripeCustomerRepository = no_init_field()

    def __post_init__(self):
        # main db
        self.stripe_customer_repo = StripeCustomerRepository(self._maindb_connection)

        # payment db
        self.payer_repo = PayerRepository(self._paymentdb_connection)
        self.pgp_customer_repo = PgpCustomerRepository(self._paymentdb_connection)
