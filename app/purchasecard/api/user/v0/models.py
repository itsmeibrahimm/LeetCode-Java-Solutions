"""
API Request/Response Models
"""

from app.commons.api.models import PaymentRequest, PaymentResponse


class CreateMarqetaUserRequest(PaymentRequest):
    token: str
    first_name: str
    last_name: str
    email: str


class CreateMarqetaUserResponse(PaymentResponse):
    token: str
