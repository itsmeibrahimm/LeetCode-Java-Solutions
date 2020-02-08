from typing import List, NewType
from uuid import uuid4

from sqlalchemy import text

from app.commons.database.client.interface import DBEngine


class MainDBDataFactory:
    UserId = NewType("UserId", int)
    ConsumerId = NewType("ConsumerId", int)
    AddressId = NewType("AddressId", int)

    maindb_admin_engine: DBEngine

    def __init__(self, maindb_admin_engine: DBEngine):
        self.maindb_admin_engine = maindb_admin_engine

    async def batch_prepare_consumers(self, num_of_consumer: int) -> List["ConsumerId"]:
        return [await self._insert_consumer() for i in range(1, num_of_consumer + 1)]

    async def _insert_user(self) -> "UserId":
        """
                                                          Table "public.user"
                  Column          |           Type           | Collation | Nullable |                  Default
        --------------------------+--------------------------+-----------+----------+-------------------------------------------
         id                       | integer                  |           | not null | nextval('accounts_user_id_seq'::regclass)
         password                 | character varying(128)   |           | not null |
         last_login               | timestamp with time zone |           |          |
         email                    | character varying(255)   |           | not null |
         is_active                | boolean                  |           | not null |
         date_joined              | timestamp with time zone |           | not null |
         phone_number             | character varying(30)    |           | not null |
         first_name               | character varying(255)   |           | not null |
         last_name                | character varying(255)   |           | not null |
         is_staff                 | boolean                  |           | not null |
         is_superuser             | boolean                  |           | not null |
         week_joined              | timestamp with time zone |           | not null |
         is_guest                 | boolean                  |           | not null |
         outgoing_number_id       | integer                  |           |          |
         experiment_id            | uuid                     |           |          |
         is_blacklisted           | boolean                  |           | not null |
         guest_user_type_id       | integer                  |           |          |
         is_whitelisted           | boolean                  |           |          |
         bucket_key_override      | text                     |           |          |
         auth_version             | integer                  |           |          |
         password_changed_at      | timestamp with time zone |           |          |
         password_change_required | boolean                  |           |          |
         is_password_secure       | boolean                  |           |          |
         password_checked_at      | timestamp with time zone |           |          |
         identity_service_key     | bigint                   |           |          |
         block_reason             | text                     |           |          |
         dasher_id                | integer                  |           |          |
         updated_at               | timestamp with time zone |           |          |

        """
        email = f"{uuid4()}@gmail.com"

        stmt = text(
            "insert into public.user "
            "(password, email, is_active, date_joined, phone_number, first_name, last_name, is_staff, is_superuser, week_joined, is_guest, is_blacklisted) "
            "values "
            f"('pwd123', '{email}', TRUE, current_timestamp, 1231231234, 'firstname', 'lastname', FALSE, FALSE, current_timestamp, FALSE, FALSE)"
            "returning *"
        )
        row = await self.maindb_admin_engine.fetch_one(stmt)
        assert row
        return row["id"]

    async def _insert_consumer(self) -> "ConsumerId":
        """
                                                                Table "public.consumer"
                        Column                |           Type           | Collation | Nullable |                    Default
        --------------------------------------+--------------------------+-----------+----------+-----------------------------------------------
         id                                   | integer                  |           | not null | nextval('consumer_consumer_id_seq'::regclass)
         stripe_id                            | character varying(50)    |           | not null |
         stripe_country_id                    | integer                  |           | not null |
         created_at                           | timestamp with time zone |           | not null |
         user_id                              | integer                  |           | not null |
         first_week                           | timestamp with time zone |           | not null |
         account_credits_deprecated           | integer                  |           | not null |
         receive_text_notifications           | boolean                  |           | not null |
         applied_new_user_credits             | boolean                  |           | not null |
         receive_push_notifications           | boolean                  |           | not null |
         channel                              | character varying(50)    |           | not null |
         default_country_id                   | integer                  |           | not null |
         default_substitution_preference      | character varying(100)   |           | not null |
         default_card_id                      | integer                  |           |          |
         referral_code                        | character varying(40)    |           |          |
         default_address_id                   | integer                  |           |          |
         sanitized_email                      | character varying(255)   |           |          |
         last_delivery_time                   | timestamp with time zone |           |          |
         gcm_id                               | text                     |           |          |
         android_version                      | integer                  |           |          |
         is_vip                               | boolean                  |           |          |
         referrer_code                        | text                     |           |          |
         came_from_group_signup               | boolean                  |           |          |
         catering_contact_email               | character varying(254)   |           |          |
         receive_marketing_push_notifications | boolean                  |           |          |
         last_alcohol_delivery_time           | timestamp with time zone |           |          |
         default_payment_method               | text                     |           |          |
         delivery_customer_pii_id             | integer                  |           |          |
         fcm_id                               | text                     |           |          |
         vip_tier                             | integer                  |           |          |
         existing_card_found_at               | timestamp with time zone |           |          |
         existing_phone_found_at              | timestamp with time zone |           |          |
         updated_at                           | timestamp with time zone |           |          |
         forgotten_at                         | timestamp with time zone |           |          |

    """

        user_id = await self._insert_user()
        address_id = await self._insert_address()

        stmt = text(
            "insert into consumer "
            "(user_id, stripe_id, default_country_id, stripe_country_id, created_at, account_credits_deprecated, "
            "applied_new_user_credits, channel, default_address_id, default_substitution_preference, first_week, "
            "receive_push_notifications, receive_text_notifications) "
            "values "
            f"({user_id}, 'cus_{uuid4()}', 1, 1, current_timestamp, 123, FALSE, 'channel', {address_id}, 'perf', "
            f"current_timestamp, TRUE, TRUE) "
            "returning *"
        )

        consumer = await self.maindb_admin_engine.fetch_one(stmt)
        assert consumer
        return consumer["id"]

    async def _insert_address(self) -> "AddressId":
        """
                                                                    Table "public.address"
                   Column            |           Type           | Collation | Nullable |                   Default
        -----------------------------+--------------------------+-----------+----------+----------------------------------------------
         id                          | integer                  |           | not null | nextval('location_address_id_seq'::regclass)
         street                      | character varying(255)   |           | not null |
         created_at                  | timestamp with time zone |           | not null |
         zip_code                    | character varying(20)    |           | not null |
         establishment               | character varying(255)   |           | not null |
         subpremise                  | character varying(255)   |           | not null |
         neighborhood                | character varying(255)   |           | not null |
         country                     | character varying(20)    |           | not null |
         formatted_address           | text                     |           | not null |
         city                        | character varying(255)   |           |          |
         state                       | character varying(2)     |           |          |
         county                      | character varying(255)   |           |          |
         point                       | geometry(Point,4326)     |           |          |
         administrative_area_level_1 | text                     |           |          |
         administrative_area_level_2 | text                     |           |          |
         administrative_area_level_3 | text                     |           |          |
         administrative_area_level_4 | text                     |           |          |
         administrative_area_level_5 | text                     |           |          |
         locality                    | text                     |           |          |
         sublocality                 | text                     |           |          |
         country_shortname           | text                     |           |          |
         google_place_id             | text                     |           |          |
         is_generic                  | boolean                  |           |          |
         name                        | text                     |           |          |
         types                       | jsonb                    |           |          |

        """

        stmt = text(
            "insert into address "
            "(street, created_at, zip_code, establishment, subpremise, neighborhood, country, formatted_address) "
            "values "
            "('street' ,current_timestamp ,'zip_code' ,'establishment' ,'subpremise' ,'neighborhood' ,'country' ,'formatted_address')"
            "returning *"
        )

        address = await self.maindb_admin_engine.fetch_one(stmt)
        assert address
        return address["id"]
