from app.commons.providers.stripe import stripe_models
from app.commons.providers.stripe.stripe_models import (
    Person,
    Verification,
    Document,
    Company,
    Address,
)
from app.commons.types import CountryCode, Currency
import app.payout.core.account.models as models
from app.payout.core.account.utils import get_internal_verification_status
from app.payout.models import StripeBusinessType


def test_get_internal_verification_status_individual():
    stripe_response = stripe_models.Account(
        id="acct_xxxx",
        business_type=StripeBusinessType.INDIVIDUAL,
        country=CountryCode.US,
        default_currency=Currency.USD,
        email="abc@xmail.com",
        individual=Person(
            id="person_xxxx",
            account="acct_xxxx",
            email="abc@xmail.com",
            ssn_last_4_provided=True,
            relationship={
                "director": False,
                "executive": False,
                "owner": False,
                "percent_ownership": None,
                "representative": True,
                "title": None,
            },
            requirements={
                "currently_due": [],
                "eventually_due": [],
                "past_due": [],
                "pending_verification": [],
            },
            verification=Verification(
                document=Document(), additional_document=Document(), status="pending"
            ),
            id_number_provided=True,
            created=1571783850,
            object="person",
        ),
        payouts_enabled=True,
        requirements={
            "current_deadline": None,
            "currently_due": ["external_account"],
            "disabled_reason": None,
            "eventually_due": ["external_account"],
            "past_due": [],
            "pending_verification": [],
        },
        type="custom",
        id_number_provided=True,
        created=1571783850,
        object="account",
        charges_enabled=True,
        details_submitted=False,
    )

    internal_status_returned = get_internal_verification_status(stripe_response)
    assert internal_status_returned == models.VerificationStatus.FIELDS_REQUIRED

    stripe_response.requirements = {
        "current_deadline": None,
        "currently_due": [],
        "disabled_reason": None,
        "eventually_due": [],
        "past_due": [],
        "pending_verification": [],
    }

    internal_status_returned = get_internal_verification_status(stripe_response)
    assert internal_status_returned == models.VerificationStatus.PENDING

    stripe_response.requirements = {
        "current_deadline": None,
        "currently_due": ["external_account"],
        "disabled_reason": None,
        "eventually_due": ["external_account"],
        "past_due": ["external_account"],
        "pending_verification": [],
    }
    stripe_response.payouts_enabled = False

    internal_status_returned = get_internal_verification_status(stripe_response)
    assert internal_status_returned == models.VerificationStatus.BLOCKED

    stripe_response.payouts_enabled = True
    stripe_response.individual.verification = Verification(
        document=Document(), additional_document=Document(), status="verified"
    )
    # But there are fields needed

    internal_status_returned = get_internal_verification_status(stripe_response)
    assert internal_status_returned == models.VerificationStatus.FIELDS_REQUIRED

    stripe_response.requirements = {
        "current_deadline": None,
        "currently_due": [],
        "disabled_reason": None,
        "eventually_due": [],
        "past_due": [],
        "pending_verification": [],
    }

    internal_status_returned = get_internal_verification_status(stripe_response)
    assert internal_status_returned == models.VerificationStatus.VERIFIED


def test_get_internal_verification_status_company():
    stripe_response = stripe_models.Account(
        id="acct_xxxx",
        business_type=StripeBusinessType.COMPANY,
        country=CountryCode.US,
        default_currency=Currency.USD,
        email="abc@xmail.com",
        company=Company(
            address=Address(
                city="SJC",
                country="US",
                line1="123 first ave",
                line2="",
                postal_code="95054",
                state="California",
            ),
            name="Test Corp.",
            tax_id="123432",
        ),
        payouts_enabled=True,
        requirements={
            "current_deadline": None,
            "currently_due": ["external_account"],
            "disabled_reason": None,
            "eventually_due": ["external_account"],
            "past_due": [],
            "pending_verification": [],
        },
        type="custom",
        id_number_provided=True,
        created=1571783850,
        object="account",
        charges_enabled=True,
        details_submitted=False,
    )

    internal_status_returned = get_internal_verification_status(stripe_response)
    assert internal_status_returned == models.VerificationStatus.FIELDS_REQUIRED

    stripe_response.requirements = {
        "current_deadline": None,
        "currently_due": [],
        "disabled_reason": None,
        "eventually_due": [],
        "past_due": [],
        "pending_verification": [],
    }

    internal_status_returned = get_internal_verification_status(stripe_response)
    assert internal_status_returned == models.VerificationStatus.VERIFIED

    stripe_response.requirements = {
        "current_deadline": None,
        "currently_due": ["external_account"],
        "disabled_reason": None,
        "eventually_due": ["external_account"],
        "past_due": ["external_account"],
        "pending_verification": [],
    }
    stripe_response.payouts_enabled = False

    internal_status_returned = get_internal_verification_status(stripe_response)
    assert internal_status_returned == models.VerificationStatus.BLOCKED

    stripe_response.payouts_enabled = True

    # But there are fields needed
    internal_status_returned = get_internal_verification_status(stripe_response)
    assert internal_status_returned == models.VerificationStatus.FIELDS_REQUIRED

    stripe_response.requirements = {
        "current_deadline": None,
        "currently_due": [],
        "disabled_reason": None,
        "eventually_due": [],
        "past_due": [],
        "pending_verification": [],
    }

    internal_status_returned = get_internal_verification_status(stripe_response)
    assert internal_status_returned == models.VerificationStatus.VERIFIED
