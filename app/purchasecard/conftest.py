import pytest

#####################
# Mock DB Repo Fixtures
#####################
from asynctest import mock


@pytest.fixture
def mock_marqeta_card_repo():
    mock_marqeta_card_repo = mock.patch(
        "app.purchasecard.repository.marqeta_card.MarqetaCardRepository"
    )
    return mock_marqeta_card_repo


@pytest.fixture
def mock_marqeta_card_ownership_repo():
    mock_marqeta_card_ownership_repo = mock.patch(
        "app.purchasecard.repository.marqeta_card_ownership.MarqetaCardOwnershipRepository"
    )
    return mock_marqeta_card_ownership_repo


@pytest.fixture
def mock_marqeta_card_transition_repo():
    mock_marqeta_card_transition_repo = mock.patch(
        "app.purchasecard.repository.marqeta_card_transition.MarqetaCardTransitionRepository"
    )
    return mock_marqeta_card_transition_repo


@pytest.fixture
def mock_store_mastercard_data_repo():
    mock_store_mastercard_data_repo = mock.patch(
        "app.purchasecard.repository.store_mastercard_data.StoreMastercardDataRepository"
    )
    return mock_store_mastercard_data_repo


@pytest.fixture
def mock_marqeta_transaction_repo():
    mock_marqeta_transaction_repo = mock.patch(
        "app.purchasecard.repository.marqeta_transaction.MarqetaTransactionRepository"
    )
    return mock_marqeta_transaction_repo


@pytest.fixture
def mock_delivery_funding_repo():
    mock_delivery_funding_repo = mock.patch(
        "app.purchasecard.repository.delivery_funding.DeliveryFundingRepository"
    )
    return mock_delivery_funding_repo


@pytest.fixture
def mock_marqeta_decline_exemption_repo():
    mock_marqeta_decline_exemption_repo = mock.patch(
        "app.purchasecard.repository.marqeta_decline_exemption.MarqetaDeclineExemptionRepository"
    )
    return mock_marqeta_decline_exemption_repo


@pytest.fixture()
def mock_authorization_master_repo():
    mock_auth_request_master_repo = mock.patch(
        "app.purchasecard.repository.authorization_repository.AuthorizationMasterRepository"
    )
    return mock_auth_request_master_repo


@pytest.fixture
def mock_authorization_replica_repo():
    mock_auth_request_replica_repo = mock.patch(
        "app.purchasecard.repository.authorization_repository.AuthorizationReplicaRepository"
    )
    return mock_auth_request_replica_repo
