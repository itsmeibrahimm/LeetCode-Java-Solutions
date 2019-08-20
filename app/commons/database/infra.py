from dataclasses import dataclass, replace
from typing import Optional
from urllib import parse

from databases import Database

from app.commons.config.app_config import DBConfig
from app.commons.config.secrets import Secret
from app.commons.context.logger import root_logger


@dataclass(frozen=True)
class DB:
    """
    Encapsulate connections pools for a database.

    """

    _master: Database
    _replica: Database
    _id: str

    @property
    def id(self):
        return self._id

    def master(self) -> Database:
        return self._master

    def replica(self) -> Database:
        return self._replica

    @property
    def connected(self) -> bool:
        return self._replica.is_connected and self._master.is_connected

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.disconnect()

    async def connect(self):
        try:
            if not self._master.is_connected:
                await self._master.connect()
            if not self._replica.is_connected:
                await self._replica.connect()
        except Exception:
            root_logger.exception(f"{self.id} failed to connect!")
            raise
        root_logger.info(f"{self.id} connected")

    async def disconnect(self):
        try:
            if self._master.is_connected:
                await self._master.disconnect()
            if self._replica.is_connected:
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
        # https://magicstack.github.io/asyncpg/current/faq.html#why-am-i-getting-prepared-statement-errors
        # note when running under pgbouncer, we need to disable
        # named prepared statements. we also do not benefit from
        # prepared statement caching
        # https://github.com/MagicStack/asyncpg/issues/339
        statement_cache_size = 0

        assert master_url.value
        master = Database(
            master_url.value,
            max_size=db_config.master_pool_max_size,
            min_size=db_config.master_pool_min_size,
            # echo=db_config.debug,
            # logging_name=f"{name}_master",
            command_timeout=db_config.statement_timeout,
            force_rollback=db_config.force_rollback,
            statement_cache_size=statement_cache_size,
        )

        assert replica_url.value
        replica = Database(
            replica_url.value,
            max_size=db_config.replica_pool_max_size,
            min_size=db_config.replica_pool_min_size,
            # echo=db_config.debug,
            # logging_name=f"{name}_replica",
            command_timeout=db_config.statement_timeout,
            force_rollback=db_config.force_rollback,
            statement_cache_size=statement_cache_size,
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
