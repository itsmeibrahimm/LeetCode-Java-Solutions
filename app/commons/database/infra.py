from dataclasses import dataclass, replace
from typing import Optional
from urllib import parse

from app.commons.config.app_config import DBConfig
from app.commons.config.secrets import Secret
from app.commons.context.logger import root_logger
from app.commons.database.client.aiopg import AioEngine
from app.commons.database.client.interface import DBEngine


@dataclass(frozen=True)
class DB:
    """
    Encapsulate connections pools for a database.

    """

    _master: DBEngine
    _replica: DBEngine
    _id: str

    @property
    def id(self):
        return self._id

    def master(self) -> DBEngine:
        return self._master

    def replica(self) -> DBEngine:
        return self._replica

    @property
    def connected(self) -> bool:
        return self._replica.is_connected() and self._master.is_connected()

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.disconnect()

    async def connect(self):
        try:
            if not self._master.is_connected():
                await self._master.connect()
            if not self._replica.is_connected():
                await self._replica.connect()
        except Exception:
            root_logger.exception(f"{self.id} failed to connect!")
            raise
        root_logger.info(f"{self.id} connected")

    async def disconnect(self):
        try:
            if self._master.is_connected():
                await self._master.disconnect()
            if self._replica.is_connected():
                await self._replica.disconnect()
        except Exception:
            root_logger.exception(f"{self.id} failed to disconnect!")
            raise
        root_logger.info(f"{self.id} discounted")

    @classmethod
    def create(
        cls, *, db_id: str, db_config: DBConfig, master_url: Secret, replica_url: Secret
    ) -> "DB":
        """
        Create an instance of DB with underlying database connection pool NOT yet initialized
        :param db_id: id of this DB wrapper
        :param db_config: config applied to underlying connection pool
        :param master_url: connection string of master instance of target database
        :param replica_url: connection string of replica instance of target database
        :return: instance of DB
        """

        assert master_url.value
        master = AioEngine(
            dsn=master_url.value,
            maxsize=db_config.master_pool_max_size,
            minsize=db_config.master_pool_min_size,
            debug=db_config.debug,
            force_rollback=db_config.force_rollback,
            default_stmt_timeout_sec=db_config.statement_timeout,
            closing_timeout_sec=db_config.closing_timeout,
        )

        assert replica_url.value
        replica = AioEngine(
            dsn=master_url.value,
            maxsize=db_config.replica_pool_max_size,
            minsize=db_config.replica_pool_min_size,
            debug=db_config.debug,
            force_rollback=db_config.force_rollback,
            default_stmt_timeout_sec=db_config.statement_timeout,
            closing_timeout_sec=db_config.closing_timeout,
        )

        return cls(_master=master, _replica=replica, _id=db_id)

    @staticmethod
    def create_with_alternative_replica(
        *,
        db_id: str,
        db_config: DBConfig,
        master_url: Secret,
        replica_url: Secret,
        alternative_replica: Optional[str],
    ) -> "DB":
        """
        Create an instance of DB with underlying database connection pool NOT yet initialized.

        When "available_replicas" is not None, it will rebuild connection string
        with this replica name based on "replica_url".

        :param db_id: id of this DB wrapper
        :param db_config: config applied to underlying connection pool
        :param master_url: connection string of master instance of target database
        :param replica_url: connection string of replica instance of target database
        :param alternative_replica: alternatively available replica instance name of target database
        :return: instance of DB
        """

        if not alternative_replica:
            return DB.create(
                db_id=db_id,
                db_config=db_config,
                master_url=master_url,
                replica_url=replica_url,
            )

        assert replica_url.value
        parsed_replica_url = parse.urlparse(replica_url.value)

        #  TODO Maybe we don't want to directly import root logger here
        root_logger.info(
            f"[create_with_alternative_replica] db_id={db_id}, replacing original "
            f"db={parsed_replica_url.path} with its replica=/{alternative_replica}"
        )
        updated_replica_url_str = parsed_replica_url._replace(
            path=f"/{alternative_replica}"
        ).geturl()

        new_replica_url_secret = replace(replica_url, value=updated_replica_url_str)

        return DB.create(
            db_id=db_id,
            db_config=db_config,
            master_url=master_url,
            replica_url=new_replica_url_secret,
        )
