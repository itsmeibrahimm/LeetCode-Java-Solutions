from typing_extensions import final

from app.commons import tracing
from app.commons.database.infra import DB
from app.purchasecard.repository.base import PurchaseCardPaymentDBRepository


@final
@tracing.track_breadcrumb(repository_name="auth_request_state")
class AuthRequestStateRepository(PurchaseCardPaymentDBRepository):
    def __init__(self, database: DB):
        super().__init__(_database=database)
