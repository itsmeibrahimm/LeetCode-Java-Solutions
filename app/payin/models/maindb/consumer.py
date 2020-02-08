from dataclasses import dataclass

from sqlalchemy import Column, Integer, Text
from typing_extensions import final

from app.commons.database.model import TableDefinition
from app.commons.utils.dataclass_extensions import no_init_field


@final
@dataclass(frozen=True)
class PartialConsumerTable(TableDefinition):
    """
    Partial columns of maindb consumer table that are only needed for migration purpose.

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

    name: str = no_init_field("consumer")
    id: Column = no_init_field(Column("id", Integer, primary_key=True))
    stripe_id: Column = no_init_field(Column("stripe_id", Text))
    stripe_country_id: Column = no_init_field(Column("stripe_country_id", Integer))
