## Update payment DSJ mainDB and bankDB container schema

Instructions on how to dump DSJ maindb and bankdb schemas to separate local postgres container for developing and CI testing purpose in payment services.

**Only need to follow this process if there is any table depended by Payin or Payout service in mainDB or bankDB has schema change**

## Step-by-step guide

### 1. Refresh DSJ local DB schema
1. Checked out latest [doorstep-django project](https://github.com/doordash/doorstep-django) if you haven't.
2. Make sure DSJ postgres container is **NOT** running.
```bash
docker rm -vf doorstep-django.postgres # remove running DSJ postgres container and its volumes
```
2. Update doorstep-django local postgres data volume. ([reference](https://github.com/doordash/doorstep-django/wiki/How-to-Develop#getting-the-database-schema-locally))
```bash
$ cd PATH/TO/DSJ/PROJECT
$ dd-toolbox doorstep-django snap-to-schema
```

### 2. Update payment-dsj schema file
This script will start doorstep-django.postgres container and dump out maindb/bankdb schemas to your local payment repo directory.
```bash
$ cd PATH/TO/PAYMENT/PROJECT
$ ./development/dump-dsj-db-schemas.sh
```

### 3. Validate updated payment-dsj db schema
Recreate your local payment.dsj-postgres container and load updated schemas. Verify if updates are reflected in the new container.
```bash
$ cd PATH/TO/PAYMENT/PROJECT
$ docker-compose -f ./development/docker-compose.nodeploy.yml up -d --force-recreate --renew-anon-volumes payment.dsj-postgres
$ docker exec -it payment.dsj-postgres psql [ maindb_dev | maindb_test | bandb_dev | bankdb_test ]
```

### 4. Create a new pull request to update refreshed DB schema in payment repo
- After above steps you maindb_dump.sql and bankdb_dump.sql should be updated to your local payment repo directory:
```
payment-service/development/
├── ...
├── db-schemas
│   ├── bankdb_dump.sql
│   └── maindb_dump.sql
├── ...
```
- **Please open a PR to update these schema files to remote repo and notify payment team!**

## Payment services dependency tables in mainDB and bankDB
#### Main DB
| Payout                    | Payin             |
|:--------------------------|:------------------|
| managed_account_transfer  | consumer          |
| marqeta_card              | consumer_charge   |
| marqeta_card_ownership    | payment_method    |
| marqeta_card_transition   | stripe_card       |
| marqeta_decline_exemption | stripe_card_event |
| marqeta_transaction       | stripe_charge     |
| marqeta_transaction_event | stripe_customer   |
| payment_account           | stripe_dispute    |
| stripe_managed_account    | stripe_recipient  |
| stripe_transfer           |                   |
| transfer                  |                   |
#### Bank DB
All tables ONLY depended by Payout.
