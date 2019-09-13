from abc import ABC
from typing import cast

from locust import Locust, TaskSet

from utils.client import (
    Ledger,
    LedgerConfig,
    PayinV0,
    PayinV0Config,
    PayinV1,
    PayinV1Config,
    PayoutV0,
    PayoutV0Config,
    PayoutV1,
    PayoutV1Config,
)


class PaymentLocust(Locust):
    pass


class PayoutV0Locust(PaymentLocust, ABC):
    class PayoutV0TaskSet(TaskSet):
        @property
        def client(self) -> PayoutV0:
            cast(PayoutV0Locust, self.locust)
            return self.locust.client

    client: PayoutV0

    def __init__(self):
        super(PayoutV0Locust, self).__init__()
        config = PayoutV0Config(host=self.host)
        self.client = PayoutV0(configuration=config)


class PayoutV1Locust(PaymentLocust, ABC):
    class PayoutV1TaskSet(TaskSet):
        @property
        def client(self) -> PayoutV1:
            cast(PayoutV1Locust, self.locust)
            return self.locust.client

    client: PayoutV1

    def __init__(self):
        super(PayoutV1Locust, self).__init__()
        config = PayoutV1Config(host=self.host)
        self.client = PayoutV1(configuration=config)


class PayinV0Locust(PaymentLocust, ABC):
    class PayinV0TaskSet(TaskSet):
        @property
        def client(self) -> PayinV0:
            cast(PayinV0Locust, self.locust)
            return self.locust.client

    client: PayinV0

    def __init__(self):
        super(PayinV0Locust, self).__init__()
        config = PayinV0Config(host=self.host)
        self.client = PayinV0(configuration=config)


class PayinV1Locust(PaymentLocust, ABC):
    class PayinV1TaskSet(TaskSet):
        @property
        def client(self) -> PayinV1:
            cast(PayinV1Locust, self.locust)
            return self.locust.client

    client: PayinV1

    def __init__(self):
        super(PayinV1Locust, self).__init__()
        config = PayinV1Config(host=self.host)
        self.client = PayinV1(configuration=config)


class LedgerLocust(PaymentLocust, ABC):
    class LedgerTaskSet(TaskSet):
        @property
        def client(self) -> Ledger:
            cast(LedgerLocust, self.locust)
            return self.locust.client

    client: Ledger

    def __init__(self):
        super(LedgerLocust, self).__init__()
        config = LedgerConfig(host=self.host)
        self.client = Ledger(configuration=config)
