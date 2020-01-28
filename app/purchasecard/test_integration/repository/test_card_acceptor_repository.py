from uuid import uuid4

import pytest

from app.commons.database.infra import DB
from app.purchasecard.models.maindb.card_acceptor import CardAcceptor
from app.purchasecard.repository.card_acceptor import CardAcceptorRepository
from app.purchasecard.test_integration.utils import prepare_and_insert_card_acceptor
from app.testcase_utils import validate_expected_items_in_dict


@pytest.mark.asyncio
class TestCardAcceptorRepository:
    @pytest.fixture(autouse=True)
    def card_acceptor_repo(self, purchasecard_maindb: DB) -> CardAcceptorRepository:
        return CardAcceptorRepository(database=purchasecard_maindb)

    @pytest.fixture
    async def mock_card_acceptor(self, card_acceptor_repo) -> CardAcceptor:
        return await prepare_and_insert_card_acceptor(
            card_acceptor_repo=card_acceptor_repo,
            mid="dinraal",
            name="din",
            city="springs of wisdom",
            zip_code=str(uuid4()),
            state="botw",
            should_be_examined=False,
        )

    async def test_create_card_acceptor(
        self,
        card_acceptor_repo: CardAcceptorRepository,
        mock_card_acceptor: CardAcceptor,
    ):
        assert mock_card_acceptor.id is not None

    async def test_get_card_acceptor_by_id(
        self,
        card_acceptor_repo: CardAcceptorRepository,
        mock_card_acceptor: CardAcceptor,
    ):
        actual_card_acceptor = await card_acceptor_repo.get_card_acceptor_by_id(
            card_acceptor_id=mock_card_acceptor.id
        )
        assert actual_card_acceptor is not None
        validate_expected_items_in_dict(
            expected=mock_card_acceptor.dict(), actual=actual_card_acceptor.dict()
        )

        wrong_id = mock_card_acceptor.id + 12345
        none_result = await card_acceptor_repo.get_card_acceptor_by_id(
            card_acceptor_id=wrong_id
        )
        assert none_result is None

    async def test_get_card_acceptor_by_card_acceptor_info(
        self,
        card_acceptor_repo: CardAcceptorRepository,
        mock_card_acceptor: CardAcceptor,
    ):
        actual_card_acceptor = await card_acceptor_repo.get_card_acceptor_by_card_acceptor_info(
            mid=mock_card_acceptor.mid,
            name=mock_card_acceptor.name,
            city=mock_card_acceptor.city,
            zip_code=mock_card_acceptor.zip_code,
            state=mock_card_acceptor.state,
        )
        assert actual_card_acceptor is not None
        assert mock_card_acceptor.id == actual_card_acceptor.id
        validate_expected_items_in_dict(
            expected=mock_card_acceptor.dict(), actual=actual_card_acceptor.dict()
        )

        none_result = await card_acceptor_repo.get_card_acceptor_by_card_acceptor_info(
            mid="farosh",
            name="farore",
            city="springs of power",
            zip_code=mock_card_acceptor.zip_code,
            state="botw",
        )
        assert none_result is None

    async def test_update_card_acceptor(
        self,
        card_acceptor_repo: CardAcceptorRepository,
        mock_card_acceptor: CardAcceptor,
    ):
        assert mock_card_acceptor.should_be_examined is False
        updated_card_acceptor = await card_acceptor_repo.update_card_acceptor(
            card_acceptor_id=mock_card_acceptor.id, should_be_examined=True
        )
        assert updated_card_acceptor is not None
        assert updated_card_acceptor.id == mock_card_acceptor.id
        assert updated_card_acceptor.should_be_examined is True

        wrong_id = mock_card_acceptor.id + 12345
        none_result = await card_acceptor_repo.update_card_acceptor(
            card_acceptor_id=wrong_id, should_be_examined=True
        )
        assert none_result is None
