from app.commons.core.errors import (
    MarqetaResourceAlreadyCreatedError,
    MarqetaCreateUserError,
)

from app.purchasecard.marqeta_external.marqeta_provider_client import (
    MarqetaProviderClient,
)
from app.purchasecard.marqeta_external.models import (
    MarqetaProviderCreateUserRequest,
    MarqetaProviderCreateUserResponse,
)
from app.purchasecard.core.user.models import InternalMarqetaUser
import app.purchasecard.marqeta_external.error as marqeta_error
from structlog.stdlib import BoundLogger


class UserProcessor:
    def __init__(self, marqeta_client: MarqetaProviderClient, logger: BoundLogger):
        self.marqeta_client = marqeta_client
        self.logger = logger

    async def create_marqeta_user(
        self, token: str, first_name: str, last_name: str, email: str
    ) -> InternalMarqetaUser:
        create_user = MarqetaProviderCreateUserRequest(
            token=token, first_name=first_name, last_name=last_name, email=email
        )

        try:
            response: MarqetaProviderCreateUserResponse = await self.marqeta_client.create_marqeta_user(
                req=create_user
            )
            return InternalMarqetaUser(token=response.token)

        except marqeta_error.DuplicateEmail:
            self.logger.warning(
                "Duplicate email error while creating Marqeta provider user",
                token=token,
                email=email,
            )

        except marqeta_error.MarqetaResourceAlreadyCreated:
            raise MarqetaResourceAlreadyCreatedError()

        # in the event of a duplicate email error, we append user token to email prefix with the plus sign
        # trick and retry
        try:
            create_user = MarqetaProviderCreateUserRequest(
                token=token,
                first_name=first_name,
                last_name=last_name,
                email=("+" + token + "@").join(email.split("@")),
            )
            response = await self.marqeta_client.create_marqeta_user(req=create_user)

        except marqeta_error.MarqetaUserAPIError:
            raise MarqetaCreateUserError()

        except marqeta_error.MarqetaResourceAlreadyCreated:
            raise MarqetaResourceAlreadyCreatedError()

        return InternalMarqetaUser(token=response.token)
