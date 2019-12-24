from enum import Enum


class DeletePayerRequestStatus(str, Enum):
    IN_PROGRESS = "IN PROGRESS"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
