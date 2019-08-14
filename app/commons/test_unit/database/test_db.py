from urllib import parse

from app.commons.config.app_config import DBConfig
from app.commons.config.secrets import Secret
from app.commons.database.infra import DB


def test_create_db_with_alternative_replica():
    master_url_obj = parse.urlparse("postgresql://user:pwd@host:123/master")
    replica_url_obj = parse.urlparse("postgresql://user:pwd@host:123/rp0")
    master_url = Secret(name="master_url", value=master_url_obj.geturl())
    replica_url = Secret(name="replica_url", value=replica_url_obj.geturl())
    db_config = DBConfig(debug=True, replica_pool_size=1, master_pool_size=1)
    available_replica = "rp1"

    original_replica_dbname = replica_url_obj.path[1:]
    master_dbname = master_url_obj.path[1:]

    assert original_replica_dbname != available_replica

    db = DB.create_with_alternative_replica(
        db_id="testdb",
        db_config=db_config,
        master_url=master_url,
        replica_url=replica_url,
        alternative_replica=available_replica,
    )

    assert db.master().url.database == master_dbname
    assert db.replica().url.database in available_replica

    available_replica = ""
    db = DB.create_with_alternative_replica(
        db_id="testdb",
        db_config=db_config,
        master_url=master_url,
        replica_url=replica_url,
        alternative_replica=available_replica,
    )

    assert db.master().url.database == master_dbname
    assert db.replica().url.database == original_replica_dbname

    available_replica = None
    db = DB.create_with_alternative_replica(
        db_id="testdb",
        db_config=db_config,
        master_url=master_url,
        replica_url=replica_url,
        alternative_replica=available_replica,
    )

    assert db.master().url.database == master_dbname
    assert db.replica().url.database == original_replica_dbname
