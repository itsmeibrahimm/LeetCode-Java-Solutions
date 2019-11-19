from structlog import BoundLogger, get_logger

logger: BoundLogger = get_logger()


class VerificationErrorCode:
    MORE_FIELDS_NEEDED = "more_fields_needed"
    REVIEW_WATCHLIST = "review_watchlist"
    REJECTED_FRAUD = "rejected_fraud"
    REJECTED_WATCHLIST = "rejected_watchlist"
    REJECTED_TOS = "rejected_tos"
    REJECTED_OTHER = "rejected_other"
    UNDER_REVIEW = "under_review"
    DISABLED_OTHER = "disabled_other"
    IMPROPER_DOCUMENT = "improper_document"
    COUNTRY_ID_NOT_SUPPORTED = "id_not_supported_by_country"
    ID_NAME_MISMATCH = "id_name_mismatch"
    VERIFICATION_FAILED_OTHER = "verification_failed_other"
    DOCUMENT_INFO_MISMATCH = "document_info_mismatch"
    UNKNOWN = "unknown"


class VerificationErrorAction:
    ACTION_BY_END_USER = "action_by_end_user"
    NO_ACTION = "no_action"
    ACTION_BY_SUPPORT = "action_by_support"


def get_verification_error_from_pgp_code(pgp_error_code) -> str:
    pgp_error_code = pgp_error_code.lower()
    verification_error_code_from_pgp_error = {
        "requirements.past_due": VerificationErrorCode.MORE_FIELDS_NEEDED,
        "fields_needed": VerificationErrorCode.MORE_FIELDS_NEEDED,
        "listed": VerificationErrorCode.REVIEW_WATCHLIST,
        "rejected.fraud": VerificationErrorCode.REJECTED_FRAUD,
        "rejected.listed": VerificationErrorCode.REJECTED_WATCHLIST,
        "rejected.terms_of_service": VerificationErrorCode.REJECTED_TOS,
        "rejected.other": VerificationErrorCode.REJECTED_OTHER,
        "under_review": VerificationErrorCode.UNDER_REVIEW,
        "other": VerificationErrorCode.DISABLED_OTHER,
    }

    if pgp_error_code not in verification_error_code_from_pgp_error.keys():
        logger.warn(
            "[get_verification_error_from_pgp_code] unknown pgp code",
            code=pgp_error_code,
        )

    return verification_error_code_from_pgp_error.get(
        pgp_error_code, VerificationErrorCode.UNKNOWN
    )


def error_to_action_mapping(error_code: str) -> str:
    if error_code in [
        VerificationErrorCode.MORE_FIELDS_NEEDED,
        VerificationErrorCode.REJECTED_FRAUD,
        VerificationErrorCode.REJECTED_WATCHLIST,
        VerificationErrorCode.REJECTED_TOS,
    ]:
        return VerificationErrorAction.ACTION_BY_END_USER
    if error_code in [
        VerificationErrorCode.DISABLED_OTHER,
        VerificationErrorCode.REJECTED_OTHER,
        VerificationErrorCode.UNKNOWN,
    ]:
        return VerificationErrorAction.ACTION_BY_SUPPORT
    return VerificationErrorAction.NO_ACTION


def document_error_mapping(details_code) -> str:
    if details_code in [
        "scan_corrupt",
        "scan_failed_greyscale",
        "scan_not_readable",
        "scan_not_uploaded",
    ]:
        return VerificationErrorCode.IMPROPER_DOCUMENT
    if details_code in ["scan_id_country_not_supported", "scan_id_type_not_supported"]:
        return VerificationErrorCode.COUNTRY_ID_NOT_SUPPORTED
    if details_code in [
        "scan_name_mismatch",
        "failed_keyed_identity",
        "document_name_mismatch",
    ]:
        return VerificationErrorCode.ID_NAME_MISMATCH
    if details_code in ["failed_other", "scan_failed_other"]:
        return VerificationErrorCode.VERIFICATION_FAILED_OTHER
    if details_code in [
        "document_address_mismatch",
        "document_dob_mismatch",
        "document_duplicate_type",
        "document_id_number_mismatch",
        "document_nationality_mismatch",
    ]:
        return VerificationErrorCode.DOCUMENT_INFO_MISMATCH

    logger.warn("[document_error_mapping] unknown code", code=details_code)
    return VerificationErrorCode.UNKNOWN


def document_error_to_action_mapping(document_error_code: str) -> str:
    if document_error_code in [
        VerificationErrorCode.IMPROPER_DOCUMENT,
        VerificationErrorCode.COUNTRY_ID_NOT_SUPPORTED,
        VerificationErrorCode.ID_NAME_MISMATCH,
    ]:
        return VerificationErrorAction.ACTION_BY_END_USER
    if document_error_code in [
        VerificationErrorCode.VERIFICATION_FAILED_OTHER,
        VerificationErrorCode.UNKNOWN,
    ]:
        return VerificationErrorAction.ACTION_BY_SUPPORT
    return VerificationErrorAction.NO_ACTION
