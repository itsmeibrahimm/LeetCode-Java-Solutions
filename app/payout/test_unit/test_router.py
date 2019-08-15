from app.commons.test_unit.api.utils import validate_router_definition


def test_accounts_v0_router():
    from app.payout.api.account.v0.api import router

    validate_router_definition(router)


def test_transfers_v0_router():
    from app.payout.api.transfer.v0.api import router

    validate_router_definition(router)
