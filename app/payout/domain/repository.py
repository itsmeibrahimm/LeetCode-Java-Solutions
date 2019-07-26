from dataclasses import dataclass

from gino import Gino

from app.commons.utils.dataclass_extensions import no_init_field
from app.payout.domain.payout_account.stripe_managed_account_repository import (
    StripeManagedAccountRepository,
)
from .payout_account.payment_account_repository import PayoutAccountRepository


@dataclass
class PayoutRepositories:
    _maindb_connection: Gino
    _bankdb_connection: Gino
    payout_accounts: PayoutAccountRepository = no_init_field()
    stripe_managed_accounts: StripeManagedAccountRepository = no_init_field()

    def __post_init__(self):
        self.payout_accounts = PayoutAccountRepository(self._maindb_connection)
        self.stripe_managed_accounts = StripeManagedAccountRepository(
            self._maindb_connection
        )
