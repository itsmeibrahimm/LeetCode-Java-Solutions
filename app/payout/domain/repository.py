import attr
from gino import Gino

from app.commons.utils.attr_extensions import no_init_attrib
from .payout_account.payment_account_repository import PayoutAccountRepository


@attr.s(auto_attribs=True)
class PayoutRepositories:
    _maindb_connection: Gino
    _bankdb_connection: Gino
    payout_accounts: PayoutAccountRepository = no_init_attrib()

    def __attrs_post_init__(self):
        self.payout_accounts = PayoutAccountRepository(self._maindb_connection)
