from app.commons.api.models import PaymentResponse


class FundableAmountResponse(PaymentResponse):
    fundable_amount: int


class FundedAmountResponse(PaymentResponse):
    funded_amount: int
