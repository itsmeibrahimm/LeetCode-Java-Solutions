from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class DatabaseConfig:
    debug: bool
    master_pool_size: int
    replica_pool_size: Optional[int]
    statement_timeout = 1.0
    force_rollback: bool = False

    def __post_init__(self):
        if self.master_pool_size <= 0:
            raise ValueError(
                f"master_pool_size should be > 0 but found={self.master_pool_size}"
            )
        if isinstance(self.replica_pool_size, int) and self.replica_pool_size <= 0:
            raise ValueError(
                f"replica_pool_size should be > 0 but found={self.replica_pool_size}"
            )
