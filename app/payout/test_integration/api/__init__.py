TRANSACTION_ENDPOINT = "/payout/api/v1/transactions"
ACCOUNT_ENDPOINT = "/payout/api/v1/accounts"


def list_transactions_url():
    return f"{TRANSACTION_ENDPOINT}/"


def create_transaction_url():
    return f"{TRANSACTION_ENDPOINT}/"


def reverse_transaction_url(tx_id: int):
    return f"{TRANSACTION_ENDPOINT}/{tx_id}/reverse"


def create_account_url():
    return ACCOUNT_ENDPOINT + "/"


def get_account_by_id_url(account_id: int):
    return f"{ACCOUNT_ENDPOINT}/{account_id}"


def update_account_statement_descriptor(account_id: int):
    return f"{ACCOUNT_ENDPOINT}/{account_id}/statement_descriptor"


def verify_account_url(account_id: int):
    return f"{ACCOUNT_ENDPOINT}/{account_id}/verify/legacy"


def create_payout_method_url_card(account_id: int):
    return f"{ACCOUNT_ENDPOINT}/{account_id}/payout_methods/card"


def create_payout_method_url_bank(account_id: int):
    return f"{ACCOUNT_ENDPOINT}/{account_id}/payout_methods/bank"


def get_payout_method_url(account_id: int, payout_method_id: int):
    return f"{ACCOUNT_ENDPOINT}/{account_id}/payout_cards/{payout_method_id}"


def list_payout_method_url(account_id: int, limit: int = 50):
    return f"{ACCOUNT_ENDPOINT}/{account_id}/payout_methods?limit={limit}"


def get_onboarding_requirements_by_stages_url():
    return f"{ACCOUNT_ENDPOINT}/onboarding_required_fields/"


def get_initiate_payout_url(payout_account_id: int):
    return f"{ACCOUNT_ENDPOINT}/{payout_account_id}/payouts"
