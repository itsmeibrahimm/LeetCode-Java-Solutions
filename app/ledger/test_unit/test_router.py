from app.commons.test_unit.api.utils import validate_router_definition


def test_mx_transactions_v1_router():
    from app.ledger.api.mx_transaction.v1.api import router

    validate_router_definition(router)


def test_mx_ledgers_v1_router():
    from app.ledger.api.mx_ledger.v1.api import router

    validate_router_definition(router)
