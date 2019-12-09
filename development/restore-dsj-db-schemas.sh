#!/bin/bash

# This is an additional docker init script for payment.dsj-postgres container. Following actions are applied:
# 1. Read existing DSJ mainDB and bankDB dumped schema files in payment repo:
# payment-service/development/
# ├── ...
# ├── db-schemas
# │   ├── bankdb_dump.sql ---> bankDB schema
# │   └── maindb_dump.sql ---> mainDB schema
# ├── ...
# 2. Create fresh DB copies (without data) for bankDB and mainDB based on schema files for DEV and TEST profile separately:
#     maindb_test, maindb_dev, bankdb_test, bankdb_dev
# 3. Create application DB user for payout and paying separately and only assign CRUD permission on their dependency tables
# across created DB copies.

set -e

bankdb_copies=(bankdb_dev bankdb_test)
maindb_copies=(maindb_dev maindb_test)
paymentdb_copies=(paymentdb_dev paymentdb_test)

payin_db_user=${PAYIN_DB_USER:-payin_user}
payout_db_user=${PAYOUT_DB_USER:-payout_user}
ledger_db_user=${LEDGER_DB_USER:-ledger_user}
purchasecard_db_user=${PURCHASECARD_DB_USER:-purchase_card_user}

echo "Creating payment db users"
psql -v ON_ERROR_STOP=1 --username root --dbname base_db <<-EOSQL
    CREATE ROLE ${payin_db_user} WITH LOGIN NOSUPERUSER;
    CREATE ROLE ${payout_db_user} WITH LOGIN NOSUPERUSER;
    CREATE ROLE ${ledger_db_user} WITH LOGIN NOSUPERUSER;
    CREATE ROLE ${purchasecard_db_user} WITH LOGIN NOSUPERUSER;
EOSQL

echo "Initializing paymentdb copies"
for dbname in "${paymentdb_copies[@]}"; do
createdb --username=root ${dbname}
# Only grant access of payment DB for $payin_db_user and $ledger_db_user
psql -v ON_ERROR_STOP=1 --username root --dbname ${dbname} <<-EOSQL
    GRANT INSERT, SELECT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO ${payin_db_user};
    GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO ${payin_db_user};
    GRANT INSERT, SELECT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO ${ledger_db_user};
    GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO ${ledger_db_user};
    GRANT INSERT, SELECT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO ${purchasecard_db_user};
    GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO ${purchasecard_db_user};
EOSQL
echo "Initialized ${dbname}"
done

echo "Initializing bankdb copies"
for dbname in "${bankdb_copies[@]}"; do
createdb --username=root ${dbname}
psql --username=root -d ${dbname} -f /tmp/db-schemas/bankdb_dump.sql
# Only grant access of bank DB for $payout_db_user
psql -v ON_ERROR_STOP=1 --username root --dbname ${dbname} <<-EOSQL
    GRANT INSERT, SELECT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO ${payout_db_user};
    GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO ${payout_db_user};
EOSQL
echo "Initialized ${dbname}"
done

echo "Creating maindb copies"
for dbname in "${maindb_copies[@]}"; do
createdb --username=root --template=base_db ${dbname}
psql --username=root -d ${dbname} -f /tmp/db-schemas/maindb_dump.sql

# Grant table CRUD access to db user.
# Two grant statements cover payout and payin table separately for readibility.
psql -v ON_ERROR_STOP=1 --username root --dbname ${dbname} <<-EOSQL
    GRANT INSERT, SELECT, UPDATE, DELETE ON
        card_acceptor,
        card_acceptor_store_association,
        delivery_funding,
        managed_account_transfer,
        marqeta_card,
        marqeta_card_ownership,
        marqeta_card_transition,
        marqeta_decline_exemption,
        marqeta_transaction,
        marqeta_transaction_event,
        payment_account,
        store_mastercard_data,
        stripe_managed_account,
        stripe_transfer,
        transfer
    TO ${payout_db_user};

    GRANT INSERT, SELECT, UPDATE, DELETE ON
        consumer,
        consumer_charge,
        payment_method,
        stripe_card,
        stripe_card_event,
        stripe_charge,
        stripe_customer,
        stripe_dispute,
        stripe_recipient
    TO ${payin_db_user};

    GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO ${payin_db_user};
    GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO ${payout_db_user};
    GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO ${ledger_db_user};
EOSQL
echo "Initialized ${dbname}"
done

echo "DB initialization finished!"
