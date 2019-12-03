from pydantic import BaseModel

from app.commons.api.models import PaymentResponse


class MarqetaJITFundingRequest(BaseModel):
    # TODO: fill in require fields
    ...


# https://www.marqeta.com/docs/core-api/gateway-jit-funding-messages#_jit_funding_responses
# Following objects are for JIT funding
# TODO: fill in required fields https://www.marqeta.com/docs/core-api/gateway-jit-funding-messages#_jit_funding_responses
class JITFunding(BaseModel):
    ...


# TODO: fill in required fields https://www.marqeta.com/docs/core-api/gateway-jit-funding-messages#_jit_funding_responses
class MarqetaJITFundingResponse(PaymentResponse):
    jit_funding: JITFunding


# End JIT Funding


class LinkStoreWithMidRequest(BaseModel):
    store_id: str
    mid: str
    mname: str


class LinkStoreWithMidResponse(PaymentResponse):
    updated_at: str
