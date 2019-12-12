import pytest

#####################
# Mock DB Repo Fixtures
#####################
from asynctest import mock

from app.commons.database.infra import DB
from app.purchasecard.repository.marqeta_card import MarqetaCardRepository
from app.purchasecard.repository.marqeta_card_ownership import (
    MarqetaCardOwnershipRepository,
)
from app.purchasecard.repository.marqeta_card_transition import (
    MarqetaCardTransitionRepository,
)
from app.purchasecard.repository.marqeta_transaction import MarqetaTransactionRepository


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
def marqeta_card_repo(purchasecard_maindb: DB) -> MarqetaCardRepository:
    return MarqetaCardRepository(database=purchasecard_maindb)


@pytest.fixture
def marqeta_card_ownership_repo(
    purchasecard_maindb: DB
) -> MarqetaCardOwnershipRepository:
    return MarqetaCardOwnershipRepository(database=purchasecard_maindb)


@pytest.fixture
def marqeta_card_transition_repo(
    purchasecard_maindb: DB
) -> MarqetaCardTransitionRepository:
    return MarqetaCardTransitionRepository(database=purchasecard_maindb)


@pytest.fixture
def marqeta_transaction_repo(purchasecard_maindb: DB) -> MarqetaTransactionRepository:
    return MarqetaTransactionRepository(database=purchasecard_maindb)
