import json
from typing import Union
from app.commons.api.models import DEFAULT_INTERNAL_EXCEPTION, PaymentException
from app.commons.context.logger import Log
from app.commons.core.processor import OperationRequest, AsyncOperation
from app.commons.runtime import runtime
from app.commons.types import CountryCode
from app.payout.core.account.types import VerificationRequirementsOnboarding
from app.payout.types import PayoutTargetType, StripeBusinessType


class GetRequiredFieldsRequest(OperationRequest):
    entity_type: PayoutTargetType
    country_shortname: CountryCode


class GetPaymentsOnboardingRequirements(
    AsyncOperation[GetRequiredFieldsRequest, VerificationRequirementsOnboarding]
):
    """
    Processor to get required fields during onboarding
    """

    def __init__(self, request: GetRequiredFieldsRequest, *, logger: Log = None):
        super().__init__(request, logger)
        self.request = request

    async def _execute(self):
        # TODO Nikita : Replace current default with {}
        required_fields_no_filter = runtime.get_json(
            "payout/feature-flags/required_fields_stages.json",
            {
                "US": {
                    "individual": {
                        "stage_0": [
                            "individual_dob",
                            "individual_first_name",
                            "individual_last_name",
                        ],
                        "stage_1": ["business_address", "last_four_ssn"],
                        "stage_2": [],
                    },
                    "company": {
                        "stage_0": [
                            "individual_dob",
                            "individual_first_name",
                            "individual_last_name",
                        ],
                        "stage_1": ["business_name", "business_address", "tin"],
                        "stage_2": [],
                    },
                },
                "CA": {
                    "individual": {
                        "stage_0": [
                            "individual_dob",
                            "individual_first_name",
                            "individual_last_name",
                            "business_address",
                        ],
                        "stage_1": [],
                        "stage_2": ["photo_id_copy"],
                    },
                    "company": {
                        "stage_0": [
                            "business_name",
                            "individual_first_name",
                            "individual_last_name",
                            "business_address",
                        ],
                        "stage_1": ["tax_id_CA"],
                        "stage_2": [],
                    },
                },
                "AU": {
                    "individual": {
                        "stage_0": [
                            "individual_dob",
                            "individual_first_name",
                            "individual_last_name",
                        ],
                        "stage_1": ["business_address"],
                        "stage_2": ["photo_id_copy"],
                    },
                    "company": {
                        "stage_0": [
                            "individual_dob",
                            "individual_first_name",
                            "individual_last_name",
                        ],
                        "stage_1": ["business_address", "tin"],
                        "stage_2": ["photo_id_copy"],
                    },
                },
            },
        )
        required_fields_by_country = required_fields_no_filter.get(
            self.request.country_shortname
        )

        if required_fields_by_country:
            if self.request.entity_type == PayoutTargetType.DASHER:
                required_fields_by_country_and_entity = required_fields_by_country.get(
                    StripeBusinessType.INDIVIDUAL
                )
            else:
                required_fields_by_country_and_entity = required_fields_by_country.get(
                    StripeBusinessType.COMPANY
                )
        else:
            required_fields_by_country_and_entity = {}
        return VerificationRequirementsOnboarding(
            required_fields_stages=json.dumps(required_fields_by_country_and_entity)
        )

    def _handle_exception(
        self, internal_exec: BaseException
    ) -> Union[PaymentException, VerificationRequirementsOnboarding]:
        raise DEFAULT_INTERNAL_EXCEPTION
