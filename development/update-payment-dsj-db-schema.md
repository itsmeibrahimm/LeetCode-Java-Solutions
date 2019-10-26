## Update payment DSJ mainDB and bankDB container schema

Instructions on how to dump DSJ maindb and bankdb schemas to separate local postgres container for developing and CI testing purpose in payment services.

**Only need to follow this process if there is any table depended by Payin or Payout service in mainDB or bankDB has schema change**

## Step-by-step guide

### 1. Update payment-dsj schema file
1. Go to [PgAnalyze](https://app.pganalyze.com/databases/13362/tables) and looking for MainDB or BankDB's newly
updated table schema you want to add
2. Correspondly, in `payment-service/development/db-schemas/bankdb_dump.sql` or/and
`payment-service/development/db-schemas/maindbdb_dump.sql` find creation statements of the table you want to update
and update according to latest schema shown in PgAnalyze

### 2. Validate updated payment-dsj db schema
Recreate your local payment.dsj-postgres container and load updated schemas. Verify if updates are reflected in the new container.
```bash
$ cd PATH/TO/PAYMENT/PROJECT
$ rm -rf  ~/.mountedvolumes/payment.dsj-postgres # !!! Note this will delete all your local dev DB data
$ docker-compose -f ./docker-compose.nodeploy.yml up -d --force-recreate --renew-anon-volumes payment.dsj-postgres
$ docker exec -it payment.dsj-postgres psql [ maindb_dev | maindb_test | bandb_dev | bankdb_test ]
```

### 3. Create a new pull request to update refreshed DB schema in payment repo
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
