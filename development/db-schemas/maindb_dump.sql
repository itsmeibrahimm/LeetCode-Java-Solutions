--
-- PostgreSQL database dump
--

-- Dumped from database version 9.6.6
-- Dumped by pg_dump version 9.6.6

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET client_min_messages = warning;
SET row_security = off;

SET search_path = public, pg_catalog;

SET default_tablespace = '';

SET default_with_oids = false;

--
-- Name: address; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE address (
    id integer NOT NULL,
    point geometry(Point,4326),
    created_at timestamp with time zone NOT NULL,
    google_place_id text,
    name text,
    formatted_address text NOT NULL,
    subpremise character varying(255) NOT NULL,
    establishment character varying(255) NOT NULL,
    street character varying(255) NOT NULL,
    neighborhood character varying(255) NOT NULL,
    sublocality text,
    locality text,
    administrative_area_level_5 text,
    administrative_area_level_4 text,
    administrative_area_level_3 text,
    administrative_area_level_2 text,
    administrative_area_level_1 text,
    country character varying(20) NOT NULL,
    country_shortname text,
    zip_code character varying(20) NOT NULL,
    types jsonb,
    is_generic boolean,
    city character varying(255),
    state character varying(2),
    county character varying(255)
);


--
-- Name: address_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE address_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: address_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE address_id_seq OWNED BY address.id;


--
-- Name: address_place_tag_link; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE address_place_tag_link (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    address_id integer NOT NULL,
    place_tag_id integer NOT NULL
);


--
-- Name: address_place_tag_link_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE address_place_tag_link_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: address_place_tag_link_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE address_place_tag_link_id_seq OWNED BY address_place_tag_link.id;


--
-- Name: analytics_businessconstants; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE analytics_businessconstants (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    active_date date NOT NULL,
    stripe_fixed_fee double precision NOT NULL,
    stripe_commission double precision NOT NULL,
    stripe_transfer_fee double precision NOT NULL,
    eel_cost_per_call double precision,
    support_unit_cost integer NOT NULL
);


--
-- Name: analytics_businessconstants_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE analytics_businessconstants_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: analytics_businessconstants_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE analytics_businessconstants_id_seq OWNED BY analytics_businessconstants.id;


--
-- Name: analytics_dailybusinessmetrics; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE analytics_dailybusinessmetrics (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    active_date date NOT NULL,
    deliveries_by_district text NOT NULL,
    profit integer NOT NULL,
    delivery_count integer NOT NULL,
    incorrect_delivery_count integer NOT NULL,
    asap_delivery_count integer NOT NULL,
    median_delivery_time integer NOT NULL,
    lateness_metrics text NOT NULL,
    ratings_count integer,
    ratings_sum integer,
    revenue text NOT NULL,
    costs text NOT NULL,
    constants_id integer NOT NULL,
    submarket_id integer NOT NULL,
    CONSTRAINT analytics_dailybusinessmetrics_asap_delivery_count_check CHECK ((asap_delivery_count >= 0)),
    CONSTRAINT analytics_dailybusinessmetrics_delivery_count_check CHECK ((delivery_count >= 0)),
    CONSTRAINT analytics_dailybusinessmetrics_incorrect_delivery_count_check CHECK ((incorrect_delivery_count >= 0)),
    CONSTRAINT analytics_dailybusinessmetrics_median_delivery_time_check CHECK ((median_delivery_time >= 0))
);


--
-- Name: analytics_dailybusinessmetrics_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE analytics_dailybusinessmetrics_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: analytics_dailybusinessmetrics_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE analytics_dailybusinessmetrics_id_seq OWNED BY analytics_dailybusinessmetrics.id;


--
-- Name: analytics_siteoutage; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE analytics_siteoutage (
    id integer NOT NULL,
    start_time timestamp with time zone NOT NULL,
    end_time timestamp with time zone NOT NULL,
    service character varying(50) NOT NULL,
    minutes_down integer NOT NULL,
    deliveries_lost integer NOT NULL,
    minutes_to_detection integer,
    notes text NOT NULL,
    reported_by_id integer NOT NULL,
    postmortem_link text,
    severity integer
);


--
-- Name: analytics_siteoutage_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE analytics_siteoutage_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: analytics_siteoutage_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE analytics_siteoutage_id_seq OWNED BY analytics_siteoutage.id;


--
-- Name: api_key; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE api_key (
    key text NOT NULL,
    created_at timestamp with time zone NOT NULL,
    is_active boolean NOT NULL,
    is_test_key boolean NOT NULL,
    user_id integer NOT NULL
);


--
-- Name: app_deploy_app; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE app_deploy_app (
    id integer NOT NULL,
    name character varying(50) NOT NULL,
    version character varying(20) NOT NULL,
    plist character varying(100) NOT NULL,
    ipa character varying(100) NOT NULL,
    is_active boolean NOT NULL,
    is_beta boolean NOT NULL,
    added_at timestamp with time zone NOT NULL,
    minimum_os character varying(20) NOT NULL
);


--
-- Name: app_deploy_app_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE app_deploy_app_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: app_deploy_app_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE app_deploy_app_id_seq OWNED BY app_deploy_app.id;


--
-- Name: apple_notification_app; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE apple_notification_app (
    id integer NOT NULL,
    bundle_id text NOT NULL,
    team_id text NOT NULL,
    apns_key_id text NOT NULL,
    apns_secret_key text NOT NULL,
    name text NOT NULL
);


--
-- Name: apple_notification_app_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE apple_notification_app_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: apple_notification_app_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE apple_notification_app_id_seq OWNED BY apple_notification_app.id;


--
-- Name: attribution_data; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE attribution_data (
    id integer NOT NULL,
    object_type text NOT NULL,
    object_id bigint NOT NULL,
    data jsonb NOT NULL
);


--
-- Name: attribution_data_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE attribution_data_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: attribution_data_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE attribution_data_id_seq OWNED BY attribution_data.id;


--
-- Name: auth_group; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE auth_group (
    id integer NOT NULL,
    name character varying(80) NOT NULL
);


--
-- Name: auth_group_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE auth_group_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: auth_group_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE auth_group_id_seq OWNED BY auth_group.id;


--
-- Name: auth_group_permissions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE auth_group_permissions (
    id integer NOT NULL,
    group_id integer NOT NULL,
    permission_id integer NOT NULL
);


--
-- Name: auth_group_permissions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE auth_group_permissions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: auth_group_permissions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE auth_group_permissions_id_seq OWNED BY auth_group_permissions.id;


--
-- Name: auth_permission; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE auth_permission (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    content_type_id integer NOT NULL,
    codename character varying(100) NOT NULL
);


--
-- Name: auth_permission_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE auth_permission_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: auth_permission_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE auth_permission_id_seq OWNED BY auth_permission.id;


--
-- Name: authtoken_token; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE authtoken_token (
    key character varying(40) NOT NULL,
    created timestamp with time zone NOT NULL,
    user_id integer NOT NULL
);


--
-- Name: banned_ip_address; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE banned_ip_address (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    ip_address inet NOT NULL
);


--
-- Name: banned_ip_address_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE banned_ip_address_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: banned_ip_address_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE banned_ip_address_id_seq OWNED BY banned_ip_address.id;


--
-- Name: base_price_sos_event; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE base_price_sos_event (
    id integer NOT NULL,
    metadata text,
    created_at timestamp with time zone NOT NULL,
    base_sos_amount integer NOT NULL,
    activation_time timestamp with time zone,
    expiration_time timestamp with time zone,
    category character varying(20) NOT NULL,
    deactivated_at timestamp with time zone,
    created_by_id integer,
    deactivated_by_id integer,
    starting_point_id integer NOT NULL
);


--
-- Name: base_price_sos_event_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE base_price_sos_event_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: base_price_sos_event_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE base_price_sos_event_id_seq OWNED BY base_price_sos_event.id;


--
-- Name: blacklisted_consumer_address; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE blacklisted_consumer_address (
    id integer NOT NULL,
    subpremise text,
    blacklisted_at timestamp with time zone NOT NULL,
    reason text NOT NULL,
    block_deliveries_to_address boolean,
    address_id integer NOT NULL,
    blacklisted_by_id integer,
    blacklisted_user_id integer,
    regex_to_match_subpremise text,
    use_regex boolean
);


--
-- Name: blacklisted_consumer_address_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE blacklisted_consumer_address_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: blacklisted_consumer_address_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE blacklisted_consumer_address_id_seq OWNED BY blacklisted_consumer_address.id;


--
-- Name: capacity_planning_evaluation; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE capacity_planning_evaluation (
    id integer NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    active_date date NOT NULL,
    num_deliveries integer NOT NULL,
    killed_duration integer NOT NULL,
    actual_supply_error double precision,
    predicted_supply_error double precision,
    predicted_caps_error double precision,
    actual_caps_error double precision,
    percent_utilization double precision,
    oversupply_score double precision NOT NULL,
    undersupply_score double precision NOT NULL,
    manual_changes_score integer NOT NULL,
    growth_error double precision NOT NULL,
    percent_time_on_manual_assign double precision NOT NULL,
    percent_caps_hit double precision NOT NULL,
    idle_ratios_by_window text NOT NULL,
    flf_by_window text NOT NULL,
    actual_scheduling_by_window text NOT NULL,
    post_adjustment_limits text NOT NULL,
    actual_delivery_counts_by_window text NOT NULL,
    ideal_supply text,
    ideal_caps text,
    actual_supply text,
    capacity_plan_id integer,
    starting_point_id integer NOT NULL
);


--
-- Name: capacity_planning_evaluation_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE capacity_planning_evaluation_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: capacity_planning_evaluation_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE capacity_planning_evaluation_id_seq OWNED BY capacity_planning_evaluation.id;


--
-- Name: card_acceptor; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE card_acceptor (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    mid character varying(50) NOT NULL,
    name character varying(50) NOT NULL,
    city character varying(50) NOT NULL,
    zip_code character varying(50) NOT NULL,
    state character varying(50) NOT NULL,
    should_be_examined boolean NOT NULL,
    is_blacklisted boolean NOT NULL,
    blacklisted_by_id integer
);


--
-- Name: card_acceptor_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE card_acceptor_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: card_acceptor_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE card_acceptor_id_seq OWNED BY card_acceptor.id;


--
-- Name: card_acceptor_store_association; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE card_acceptor_store_association (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    unique_drivers text NOT NULL,
    strength integer NOT NULL,
    status character varying(25) NOT NULL,
    card_acceptor_id integer NOT NULL,
    manually_checked_by_id integer,
    store_id integer NOT NULL
);


--
-- Name: card_acceptor_store_association_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE card_acceptor_store_association_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: card_acceptor_store_association_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE card_acceptor_store_association_id_seq OWNED BY card_acceptor_store_association.id;


--
-- Name: cash_payment; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE cash_payment (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    currency text,
    status text,
    amount integer NOT NULL,
    amount_refunded integer,
    description text,
    error_reason text,
    charge_id integer NOT NULL
);


--
-- Name: cash_payment_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE cash_payment_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: cash_payment_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE cash_payment_id_seq OWNED BY cash_payment.id;


--
-- Name: city; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE city (
    id integer NOT NULL,
    name character varying(100) NOT NULL,
    shortname character varying(100) NOT NULL,
    slug text,
    is_active boolean NOT NULL,
    center geometry(Point,4326),
    num_stores integer NOT NULL,
    market_id integer NOT NULL,
    submarket_id integer NOT NULL
);


--
-- Name: city_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE city_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: city_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE city_id_seq OWNED BY city.id;


--
-- Name: communication_preferences_channel_link; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE communication_preferences_channel_link (
    id integer NOT NULL,
    communication_channel_id integer NOT NULL,
    communication_preferences_id integer NOT NULL
);


--
-- Name: communication_preferences_channel_link_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE communication_preferences_channel_link_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: communication_preferences_channel_link_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE communication_preferences_channel_link_id_seq OWNED BY communication_preferences_channel_link.id;


--
-- Name: compensation_request; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE compensation_request (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    approved_at timestamp with time zone,
    recommended_refund integer NOT NULL,
    recommended_credits integer NOT NULL,
    store_cost integer NOT NULL,
    currency text,
    request_data text NOT NULL,
    category character varying(100) NOT NULL,
    revision_reason character varying(100) NOT NULL,
    cannot_auto_approve_reason text,
    submit_platform text,
    approved_by_id integer,
    delivery_id integer NOT NULL,
    error_id integer
);


--
-- Name: compensation_request_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE compensation_request_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: compensation_request_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE compensation_request_id_seq OWNED BY compensation_request.id;


--
-- Name: consumer; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE consumer (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    first_week date NOT NULL,
    receive_text_notifications boolean NOT NULL,
    receive_push_notifications boolean NOT NULL,
    receive_marketing_push_notifications boolean,
    sanitized_email character varying(255),
    catering_contact_email character varying(254),
    account_credits_deprecated integer NOT NULL,
    applied_new_user_credits boolean NOT NULL,
    last_alcohol_delivery_time timestamp with time zone,
    gcm_id text,
    fcm_id text,
    android_version integer,
    default_payment_method text,
    stripe_id character varying(50) NOT NULL,
    channel character varying(50) NOT NULL,
    default_substitution_preference character varying(100) NOT NULL,
    delivery_customer_pii_id integer,
    referral_code character varying(40),
    referrer_code text,
    last_delivery_time timestamp with time zone,
    came_from_group_signup boolean,
    default_address_id integer,
    default_card_id integer,
    default_country_id integer NOT NULL,
    stripe_country_id integer NOT NULL,
    user_id integer NOT NULL,
    vip_tier integer,
    existing_card_found_at timestamp with time zone,
    existing_phone_found_at timestamp with time zone
);


--
-- Name: consumer_account_credits; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE consumer_account_credits (
    id integer NOT NULL,
    support_credit integer NOT NULL,
    referree_credit integer NOT NULL,
    referrer_credit integer NOT NULL,
    gift_code_credit integer NOT NULL,
    delivery_gift_credit integer NOT NULL,
    delivery_update_credit integer NOT NULL,
    manual_credit integer,
    other_credit integer NOT NULL,
    currency text,
    updated_at timestamp with time zone NOT NULL,
    consumer_id integer NOT NULL
);


--
-- Name: consumer_account_credits_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE consumer_account_credits_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: consumer_account_credits_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE consumer_account_credits_id_seq OWNED BY consumer_account_credits.id;


--
-- Name: consumer_account_credits_transaction; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE consumer_account_credits_transaction (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    amount integer NOT NULL,
    balance integer NOT NULL,
    currency text,
    description text NOT NULL,
    type character varying(100) NOT NULL,
    consumer_id integer NOT NULL
);


--
-- Name: consumer_account_credits_transaction_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE consumer_account_credits_transaction_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: consumer_account_credits_transaction_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE consumer_account_credits_transaction_id_seq OWNED BY consumer_account_credits_transaction.id;


--
-- Name: consumer_address_link; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE consumer_address_link (
    id integer NOT NULL,
    created_at timestamp with time zone,
    dasher_instructions text NOT NULL,
    is_active boolean NOT NULL,
    manual_point geometry(Point,4326),
    subpremise character varying(100) NOT NULL,
    address_id integer NOT NULL,
    consumer_id integer NOT NULL,
    address_validation_info text,
    entry_code text,
    parking_instructions text
);


--
-- Name: consumer_address_link_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE consumer_address_link_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: consumer_address_link_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE consumer_address_link_id_seq OWNED BY consumer_address_link.id;


--
-- Name: consumer_announcement; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE consumer_announcement (
    id integer NOT NULL,
    title character varying(140) NOT NULL,
    body text NOT NULL,
    expiration_date timestamp with time zone NOT NULL,
    created_at timestamp with time zone NOT NULL,
    show_once boolean NOT NULL,
    platform character varying(10),
    image character varying(100)
);


--
-- Name: consumer_announcement_district_link; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE consumer_announcement_district_link (
    id integer NOT NULL,
    consumer_announcement_id integer NOT NULL,
    district_id integer NOT NULL
);


--
-- Name: consumer_announcement_district_link_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE consumer_announcement_district_link_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: consumer_announcement_district_link_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE consumer_announcement_district_link_id_seq OWNED BY consumer_announcement_district_link.id;


--
-- Name: consumer_announcement_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE consumer_announcement_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: consumer_announcement_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE consumer_announcement_id_seq OWNED BY consumer_announcement.id;


--
-- Name: consumer_announcement_submarkets; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE consumer_announcement_submarkets (
    id integer NOT NULL,
    consumerannouncement_id integer NOT NULL,
    submarket_id integer NOT NULL
);


--
-- Name: consumer_announcement_submarkets_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE consumer_announcement_submarkets_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: consumer_announcement_submarkets_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE consumer_announcement_submarkets_id_seq OWNED BY consumer_announcement_submarkets.id;


--
-- Name: consumer_channel; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE consumer_channel (
    id integer NOT NULL,
    name character varying(100) NOT NULL,
    image_url character varying(100) NOT NULL
);


--
-- Name: consumer_channel_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE consumer_channel_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: consumer_channel_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE consumer_channel_id_seq OWNED BY consumer_channel.id;


--
-- Name: consumer_channel_submarkets; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE consumer_channel_submarkets (
    id integer NOT NULL,
    consumerchannel_id integer NOT NULL,
    submarket_id integer NOT NULL
);


--
-- Name: consumer_channel_submarkets_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE consumer_channel_submarkets_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: consumer_channel_submarkets_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE consumer_channel_submarkets_id_seq OWNED BY consumer_channel_submarkets.id;


--
-- Name: consumer_charge; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE consumer_charge (
    id integer NOT NULL,
    target_id integer NOT NULL,
    idempotency_key character varying(120),
    is_stripe_connect_based boolean NOT NULL,
    created_at timestamp with time zone,
    total integer NOT NULL,
    original_total integer NOT NULL,
    currency text,
    consumer_id integer,
    country_id integer NOT NULL,
    issue_id integer,
    stripe_customer_id integer,
    target_ct_id integer NOT NULL,
    CONSTRAINT consumer_charge_target_id_check CHECK ((target_id >= 0))
);


--
-- Name: consumer_charge_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE consumer_charge_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: consumer_charge_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE consumer_charge_id_seq OWNED BY consumer_charge.id;


--
-- Name: consumer_communication_channel; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE consumer_communication_channel (
    id integer NOT NULL,
    name text NOT NULL
);


--
-- Name: consumer_communication_channel_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE consumer_communication_channel_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: consumer_communication_channel_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE consumer_communication_channel_id_seq OWNED BY consumer_communication_channel.id;


--
-- Name: consumer_communication_preferences; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE consumer_communication_preferences (
    consumer_id integer NOT NULL,
    email_unsubscribe_time timestamp with time zone,
    email_holdout_group_id integer NOT NULL,
    email_preference_id integer NOT NULL
);


--
-- Name: consumer_delivery_rating; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE consumer_delivery_rating (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    merchant_rating integer NOT NULL,
    dasher_rating integer NOT NULL,
    dasher_comments text NOT NULL,
    merchant_comments text NOT NULL,
    show_consumer boolean,
    processed_at timestamp with time zone,
    store_id integer,
    delivery_id integer NOT NULL
);


--
-- Name: consumer_delivery_rating_category; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE consumer_delivery_rating_category (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    name text,
    friendly_name text
);


--
-- Name: consumer_delivery_rating_category_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE consumer_delivery_rating_category_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: consumer_delivery_rating_category_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE consumer_delivery_rating_category_id_seq OWNED BY consumer_delivery_rating_category.id;


--
-- Name: consumer_delivery_rating_category_link; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE consumer_delivery_rating_category_link (
    id integer NOT NULL,
    category_id integer NOT NULL,
    rating_id integer NOT NULL
);


--
-- Name: consumer_delivery_rating_category_link_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE consumer_delivery_rating_category_link_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: consumer_delivery_rating_category_link_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE consumer_delivery_rating_category_link_id_seq OWNED BY consumer_delivery_rating_category_link.id;


--
-- Name: consumer_delivery_rating_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE consumer_delivery_rating_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: consumer_delivery_rating_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE consumer_delivery_rating_id_seq OWNED BY consumer_delivery_rating.id;


--
-- Name: consumer_discount; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE consumer_discount (
    id integer NOT NULL,
    delivery_fee integer,
    service_rate numeric(6,3),
    extra_sos_fee integer,
    discount_percentage numeric(6,3),
    discount_value integer,
    max_discount integer,
    currency text,
    minimum_subtotal integer NOT NULL,
    discount_type text
);


--
-- Name: consumer_discount_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE consumer_discount_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: consumer_discount_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE consumer_discount_id_seq OWNED BY consumer_discount.id;


--
-- Name: consumer_donation; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE consumer_donation (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    voided_at timestamp with time zone,
    paid_at timestamp with time zone,
    order_cart_id integer NOT NULL,
    donation_recipient_id integer NOT NULL,
    status text NOT NULL,
    amount integer NOT NULL,
    currency text NOT NULL
);


--
-- Name: consumer_donation_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE consumer_donation_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: consumer_donation_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE consumer_donation_id_seq OWNED BY consumer_donation.id;


--
-- Name: consumer_donation_recipient_link; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE consumer_donation_recipient_link (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    consumer_id integer NOT NULL,
    donation_recipient_id integer NOT NULL,
    is_active boolean NOT NULL
);


--
-- Name: consumer_donation_recipient_link_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE consumer_donation_recipient_link_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: consumer_donation_recipient_link_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE consumer_donation_recipient_link_id_seq OWNED BY consumer_donation_recipient_link.id;


--
-- Name: consumer_empty_store_list_request; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE consumer_empty_store_list_request (
    id integer NOT NULL,
    location geometry(Point,4326),
    created_at timestamp with time zone NOT NULL
);


--
-- Name: consumer_empty_store_list_request_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE consumer_empty_store_list_request_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: consumer_empty_store_list_request_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE consumer_empty_store_list_request_id_seq OWNED BY consumer_empty_store_list_request.id;


--
-- Name: consumer_faq; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE consumer_faq (
    id integer NOT NULL,
    question text NOT NULL,
    answer text NOT NULL,
    order_id integer NOT NULL
);


--
-- Name: consumer_faq_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE consumer_faq_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: consumer_faq_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE consumer_faq_id_seq OWNED BY consumer_faq.id;


--
-- Name: consumer_favorites; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE consumer_favorites (
    id integer NOT NULL,
    business_id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    consumer_id integer NOT NULL
);


--
-- Name: consumer_favorites_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE consumer_favorites_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: consumer_favorites_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE consumer_favorites_id_seq OWNED BY consumer_favorites.id;


--
-- Name: consumer_fraud_info; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE consumer_fraud_info (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    event_name text NOT NULL,
    sift_score double precision NOT NULL,
    charge_id integer,
    consumer_id integer NOT NULL,
    order_cart_id integer NOT NULL
);


--
-- Name: consumer_fraud_info_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE consumer_fraud_info_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: consumer_fraud_info_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE consumer_fraud_info_id_seq OWNED BY consumer_fraud_info.id;


--
-- Name: consumer_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE consumer_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: consumer_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE consumer_id_seq OWNED BY consumer.id;


--
-- Name: consumer_ios_devices; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE consumer_ios_devices (
    id integer NOT NULL,
    consumer_id integer NOT NULL,
    device_id integer NOT NULL
);


--
-- Name: consumer_ios_devices_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE consumer_ios_devices_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: consumer_ios_devices_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE consumer_ios_devices_id_seq OWNED BY consumer_ios_devices.id;


--
-- Name: consumer_preferences; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE consumer_preferences (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    consumer_id integer NOT NULL
);


--
-- Name: consumer_preferences_category_link; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE consumer_preferences_category_link (
    id integer NOT NULL,
    category_name text NOT NULL,
    consumer_preferences_id integer NOT NULL
);


--
-- Name: consumer_preferences_category_link_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE consumer_preferences_category_link_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: consumer_preferences_category_link_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE consumer_preferences_category_link_id_seq OWNED BY consumer_preferences_category_link.id;


--
-- Name: consumer_preferences_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE consumer_preferences_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: consumer_preferences_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE consumer_preferences_id_seq OWNED BY consumer_preferences.id;


--
-- Name: consumer_profile_edit_history; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE consumer_profile_edit_history (
    id integer NOT NULL,
    edit_type text NOT NULL,
    platform text NOT NULL,
    old_value text NOT NULL,
    new_value text NOT NULL,
    created_at timestamp with time zone NOT NULL,
    consumer_id integer NOT NULL
);


--
-- Name: consumer_profile_edit_history_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE consumer_profile_edit_history_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: consumer_profile_edit_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE consumer_profile_edit_history_id_seq OWNED BY consumer_profile_edit_history.id;


--
-- Name: consumer_promotion; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE consumer_promotion (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    start_time timestamp with time zone NOT NULL,
    end_time timestamp with time zone NOT NULL,
    local_merchant_start_time time without time zone,
    num_days_active integer,
    max_applicable_consumer_count integer,
    max_applicable_delivery_count integer NOT NULL,
    max_total_redemption_count integer,
    max_redemption_count_per_timezone text,
    redemption_count_per_time_interval text,
    redemption_throttle_time_interval integer,
    error_message_overrides text,
    code text NOT NULL,
    type character varying(20),
    order_type text,
    restricted_to_submarket boolean NOT NULL,
    free_service_fee boolean,
    free_small_order_fee boolean,
    notes text NOT NULL,
    description text,
    title text,
    cuisine_promo text NOT NULL,
    item_promo text NOT NULL,
    new_customer_for_item_promo_only boolean,
    store_ids_for_promo text NOT NULL,
    currency text,
    new_customer_only boolean NOT NULL,
    subscriber_only boolean,
    featured_on_app boolean,
    click_to_apply_only boolean,
    incentive_type text NOT NULL,
    incentive_id integer NOT NULL,
    budget_source character varying(30),
    auto_redeem boolean,
    auto_apply_only boolean,
    "group" text,
    display_promotion_delivery_fee_on_store boolean,
    discount_source text,
    channel_id integer,
    consumer_promotion_campaign_id integer,
    item_promo_exclusion_list text,
    second_item_exclusion_list text,
    second_item_promo text,
    is_active boolean,
    CONSTRAINT consumer_promotion_incentive_id_check CHECK ((incentive_id >= 0)),
    CONSTRAINT consumer_promotion_max_applicable_delivery_count_check CHECK ((max_applicable_delivery_count >= 0)),
    CONSTRAINT consumer_promotion_max_total_redemption_count_check CHECK ((max_total_redemption_count >= 0)),
    CONSTRAINT consumer_promotion_num_days_active_check CHECK ((num_days_active >= 0)),
    CONSTRAINT consumer_promotion_redemption_throttle_time_interval_check CHECK ((redemption_throttle_time_interval >= 0))
);


--
-- Name: consumer_promotion_campaign; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE consumer_promotion_campaign (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    name text,
    is_active boolean NOT NULL,
    notes text,
    store_id integer
);


--
-- Name: consumer_promotion_campaign_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE consumer_promotion_campaign_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: consumer_promotion_campaign_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE consumer_promotion_campaign_id_seq OWNED BY consumer_promotion_campaign.id;


--
-- Name: consumer_promotion_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE consumer_promotion_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: consumer_promotion_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE consumer_promotion_id_seq OWNED BY consumer_promotion.id;


--
-- Name: consumer_push_notification; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE consumer_push_notification (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    message text,
    data text NOT NULL,
    unthrottled boolean NOT NULL,
    min_android_version integer,
    min_ios_version integer,
    topic text NOT NULL,
    scheduled_time timestamp with time zone,
    sent_time timestamp with time zone,
    received_time timestamp with time zone,
    cancelled_by_server timestamp with time zone,
    cancelled_by_client timestamp with time zone,
    consumer_id integer NOT NULL
);


--
-- Name: consumer_push_notification_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE consumer_push_notification_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: consumer_push_notification_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE consumer_push_notification_id_seq OWNED BY consumer_push_notification.id;


--
-- Name: consumer_referral_link; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE consumer_referral_link (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    redeemed_at timestamp with time zone,
    email character varying(40) NOT NULL,
    first_name character varying(40) NOT NULL,
    last_name character varying(40) NOT NULL,
    amount integer NOT NULL,
    currency text,
    referrer_amount integer,
    referree_amount integer,
    referrer_submarket_id integer,
    referree_submarket_id integer,
    min_referree_order_subtotal integer,
    referree_promotion_id integer,
    no_payout_reason character varying(255),
    duplicate_consumer_ids text,
    order_cart_id integer,
    referree_id integer,
    referrer_id integer NOT NULL,
    CONSTRAINT consumer_referral_link_min_referree_order_subtotal_check CHECK ((min_referree_order_subtotal >= 0)),
    CONSTRAINT consumer_referral_link_referree_submarket_id_check CHECK ((referree_submarket_id >= 0)),
    CONSTRAINT consumer_referral_link_referrer_submarket_id_check CHECK ((referrer_submarket_id >= 0))
);


--
-- Name: consumer_referral_link_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE consumer_referral_link_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: consumer_referral_link_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE consumer_referral_link_id_seq OWNED BY consumer_referral_link.id;


--
-- Name: consumer_share; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE consumer_share (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    social_media_type character varying(100) NOT NULL,
    consumer_id integer NOT NULL
);


--
-- Name: consumer_share_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE consumer_share_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: consumer_share_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE consumer_share_id_seq OWNED BY consumer_share.id;


--
-- Name: consumer_store_request; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE consumer_store_request (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    requested_store_type text NOT NULL,
    requested_store_id integer NOT NULL,
    consumer_id integer NOT NULL,
    notified_date timestamp with time zone,
    store_activation_date timestamp with time zone
);


--
-- Name: consumer_store_request_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE consumer_store_request_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: consumer_store_request_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE consumer_store_request_id_seq OWNED BY consumer_store_request.id;


--
-- Name: consumer_stripe_customer_link; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE consumer_stripe_customer_link (
    id integer NOT NULL,
    stripe_id text NOT NULL,
    country_code text NOT NULL,
    consumer_id integer NOT NULL
);


--
-- Name: consumer_stripe_customer_link_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE consumer_stripe_customer_link_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: consumer_stripe_customer_link_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE consumer_stripe_customer_link_id_seq OWNED BY consumer_stripe_customer_link.id;


--
-- Name: consumer_subscription; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE consumer_subscription (
    id integer NOT NULL,
    stripe_id text,
    is_active boolean NOT NULL,
    subscription_status text,
    temporarily_deactivated_at timestamp with time zone,
    renew boolean NOT NULL,
    start_time timestamp with time zone NOT NULL,
    end_time timestamp with time zone NOT NULL,
    cancellation_requested_at timestamp with time zone,
    cancelled_at timestamp with time zone,
    submarket_id_subscribed_from integer,
    currency text,
    consumer_id integer NOT NULL,
    consumer_subscription_plan_id integer NOT NULL,
    payment_card_id integer,
    payment_method_id integer
);


--
-- Name: consumer_subscription_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE consumer_subscription_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: consumer_subscription_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE consumer_subscription_id_seq OWNED BY consumer_subscription.id;


--
-- Name: consumer_subscription_plan; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE consumer_subscription_plan (
    id integer NOT NULL,
    stripe_id text,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    fee integer NOT NULL,
    currency text,
    charge_description text,
    start_time timestamp with time zone NOT NULL,
    end_time timestamp with time zone NOT NULL,
    is_accepting_new_subscribers boolean NOT NULL,
    employees_only boolean NOT NULL,
    allow_all_stores boolean NOT NULL,
    callout_text text,
    policy_text text,
    recurrence_interval_type text,
    recurrence_interval_units integer,
    plan_benefit_short text,
    plan_benefit_long text,
    plan_benefit_delivery_fee text,
    signup_email_campaign_id integer,
    terms_and_conditions text,
    consumer_discount_id integer NOT NULL
);


--
-- Name: consumer_subscription_plan_featured_location_link; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE consumer_subscription_plan_featured_location_link (
    id integer NOT NULL,
    consumer_subscription_plan_id integer NOT NULL,
    featured_location_id integer NOT NULL
);


--
-- Name: consumer_subscription_plan_featured_location_link_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE consumer_subscription_plan_featured_location_link_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: consumer_subscription_plan_featured_location_link_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE consumer_subscription_plan_featured_location_link_id_seq OWNED BY consumer_subscription_plan_featured_location_link.id;


--
-- Name: consumer_subscription_plan_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE consumer_subscription_plan_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: consumer_subscription_plan_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE consumer_subscription_plan_id_seq OWNED BY consumer_subscription_plan.id;


--
-- Name: consumer_subscription_plan_promotion_info; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE consumer_subscription_plan_promotion_info (
    id integer NOT NULL,
    type text,
    title text,
    subtitle text,
    icon_image_url text
);


--
-- Name: consumer_subscription_plan_promotion_info_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE consumer_subscription_plan_promotion_info_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: consumer_subscription_plan_promotion_info_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE consumer_subscription_plan_promotion_info_id_seq OWNED BY consumer_subscription_plan_promotion_info.id;


--
-- Name: consumer_subscription_plan_promotion_infos; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE consumer_subscription_plan_promotion_infos (
    id integer NOT NULL,
    consumersubscriptionplan_id integer NOT NULL,
    consumersubscriptionplanpromotioninfo_id integer NOT NULL
);


--
-- Name: consumer_subscription_plan_promotion_infos_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE consumer_subscription_plan_promotion_infos_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: consumer_subscription_plan_promotion_infos_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE consumer_subscription_plan_promotion_infos_id_seq OWNED BY consumer_subscription_plan_promotion_infos.id;


--
-- Name: consumer_subscription_plan_submarket_link; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE consumer_subscription_plan_submarket_link (
    id integer NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    popular_stores text,
    consumer_subscription_plan_id integer NOT NULL,
    submarket_id integer NOT NULL,
    consent_details text
);


--
-- Name: consumer_subscription_plan_submarket_link_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE consumer_subscription_plan_submarket_link_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: consumer_subscription_plan_submarket_link_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE consumer_subscription_plan_submarket_link_id_seq OWNED BY consumer_subscription_plan_submarket_link.id;


--
-- Name: consumer_subscription_plan_trial; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE consumer_subscription_plan_trial (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    is_active boolean NOT NULL,
    interval_type text,
    interval_units integer,
    payment_provider_type text,
    consumer_subscription_plan_id integer NOT NULL
);


--
-- Name: consumer_subscription_plan_trial_featured_location_link; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE consumer_subscription_plan_trial_featured_location_link (
    id integer NOT NULL,
    consumer_subscription_plan_trial_id integer NOT NULL,
    featured_location_id integer NOT NULL
);


--
-- Name: consumer_subscription_plan_trial_featured_location_link_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE consumer_subscription_plan_trial_featured_location_link_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: consumer_subscription_plan_trial_featured_location_link_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE consumer_subscription_plan_trial_featured_location_link_id_seq OWNED BY consumer_subscription_plan_trial_featured_location_link.id;


--
-- Name: consumer_subscription_plan_trial_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE consumer_subscription_plan_trial_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: consumer_subscription_plan_trial_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE consumer_subscription_plan_trial_id_seq OWNED BY consumer_subscription_plan_trial.id;


--
-- Name: consumer_subscription_plan_trial_promotion_infos; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE consumer_subscription_plan_trial_promotion_infos (
    id integer NOT NULL,
    consumersubscriptionplantrial_id integer NOT NULL,
    consumersubscriptionplanpromotioninfo_id integer NOT NULL
);


--
-- Name: consumer_subscription_plan_trial_promotion_infos_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE consumer_subscription_plan_trial_promotion_infos_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: consumer_subscription_plan_trial_promotion_infos_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE consumer_subscription_plan_trial_promotion_infos_id_seq OWNED BY consumer_subscription_plan_trial_promotion_infos.id;


--
-- Name: consumer_subscription_plan_trial_submarket_link; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE consumer_subscription_plan_trial_submarket_link (
    id integer NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    consumer_subscription_plan_trial_id integer NOT NULL,
    submarket_id integer NOT NULL,
    trial_consent_details text
);


--
-- Name: consumer_subscription_plan_trial_submarket_link_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE consumer_subscription_plan_trial_submarket_link_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: consumer_subscription_plan_trial_submarket_link_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE consumer_subscription_plan_trial_submarket_link_id_seq OWNED BY consumer_subscription_plan_trial_submarket_link.id;


--
-- Name: consumer_subscription_unit; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE consumer_subscription_unit (
    id integer NOT NULL,
    stripe_id text,
    start_time timestamp with time zone NOT NULL,
    end_time timestamp with time zone NOT NULL,
    currency text,
    amount integer NOT NULL,
    charge_id integer,
    consumer_subscription_id integer NOT NULL,
    consumer_subscription_plan_trial_id integer
);


--
-- Name: consumer_subscription_unit_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE consumer_subscription_unit_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: consumer_subscription_unit_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE consumer_subscription_unit_id_seq OWNED BY consumer_subscription_unit.id;


--
-- Name: consumer_survey; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE consumer_survey (
    id integer NOT NULL,
    activated_at timestamp with time zone,
    deactivated_at timestamp with time zone,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: consumer_survey_answer_option; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE consumer_survey_answer_option (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    text text,
    survey_question_id integer NOT NULL
);


--
-- Name: consumer_survey_answer_option_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE consumer_survey_answer_option_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: consumer_survey_answer_option_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE consumer_survey_answer_option_id_seq OWNED BY consumer_survey_answer_option.id;


--
-- Name: consumer_survey_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE consumer_survey_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: consumer_survey_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE consumer_survey_id_seq OWNED BY consumer_survey.id;


--
-- Name: consumer_survey_question; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE consumer_survey_question (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    question text,
    include_freeform_answer_option boolean NOT NULL,
    survey_id integer NOT NULL
);


--
-- Name: consumer_survey_question_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE consumer_survey_question_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: consumer_survey_question_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE consumer_survey_question_id_seq OWNED BY consumer_survey_question.id;


--
-- Name: consumer_survey_question_response; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE consumer_survey_question_response (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    answer_text text,
    is_freeform boolean NOT NULL,
    survey_answer_option_id integer,
    survey_question_id integer NOT NULL,
    survey_response_id integer NOT NULL
);


--
-- Name: consumer_survey_question_response_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE consumer_survey_question_response_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: consumer_survey_question_response_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE consumer_survey_question_response_id_seq OWNED BY consumer_survey_question_response.id;


--
-- Name: consumer_survey_response; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE consumer_survey_response (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    consumer_id integer NOT NULL,
    survey_id integer NOT NULL
);


--
-- Name: consumer_survey_response_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE consumer_survey_response_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: consumer_survey_response_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE consumer_survey_response_id_seq OWNED BY consumer_survey_response.id;


--
-- Name: consumer_terms_of_service; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE consumer_terms_of_service (
    id integer NOT NULL,
    version text NOT NULL,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: consumer_terms_of_service_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE consumer_terms_of_service_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: consumer_terms_of_service_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE consumer_terms_of_service_id_seq OWNED BY consumer_terms_of_service.id;


--
-- Name: consumer_tos_link; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE consumer_tos_link (
    id integer NOT NULL,
    accepted_at timestamp with time zone NOT NULL,
    consumer_id integer NOT NULL,
    terms_of_service_id integer NOT NULL
);


--
-- Name: consumer_tos_link_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE consumer_tos_link_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: consumer_tos_link_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE consumer_tos_link_id_seq OWNED BY consumer_tos_link.id;


--
-- Name: consumer_variable_pay; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE consumer_variable_pay (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    consumer_cohort integer,
    pricing_tiers text,
    tier integer,
    distance double precision,
    consumer_id integer NOT NULL,
    delivery_id integer NOT NULL,
    district_id integer
);


--
-- Name: consumer_variable_pay_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE consumer_variable_pay_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: consumer_variable_pay_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE consumer_variable_pay_id_seq OWNED BY consumer_variable_pay.id;


--
-- Name: consumer_verification_status; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE consumer_verification_status (
    created_at timestamp with time zone NOT NULL,
    consumer_id integer NOT NULL,
    is_phone_number_verified boolean NOT NULL,
    is_email_verified boolean NOT NULL
);


--
-- Name: core_image; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE core_image (
    id integer NOT NULL,
    target_id integer NOT NULL,
    image character varying(100),
    target_ct_id integer NOT NULL,
    CONSTRAINT core_image_target_id_check CHECK ((target_id >= 0))
);


--
-- Name: core_image_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE core_image_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: core_image_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE core_image_id_seq OWNED BY core_image.id;


--
-- Name: core_modelannotation; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE core_modelannotation (
    id integer NOT NULL,
    target_id integer NOT NULL,
    annotation_type character varying(32) NOT NULL,
    data text NOT NULL,
    target_ct_id integer NOT NULL,
    CONSTRAINT core_modelannotation_target_id_check CHECK ((target_id >= 0))
);


--
-- Name: core_modelannotation_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE core_modelannotation_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: core_modelannotation_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE core_modelannotation_id_seq OWNED BY core_modelannotation.id;


--
-- Name: country; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE country (
    id integer NOT NULL,
    name character varying(100) NOT NULL,
    shortname character varying(3) NOT NULL,
    is_active boolean NOT NULL,
    has_fees_tax boolean NOT NULL,
    allows_pre_tipping boolean
);


--
-- Name: country_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE country_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: country_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE country_id_seq OWNED BY country.id;


--
-- Name: credit_refund_delivery_error; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE credit_refund_delivery_error (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    category text NOT NULL,
    recommended_credits integer NOT NULL,
    recommended_refund integer NOT NULL,
    is_allowed_redelivery boolean NOT NULL,
    actual_credits_given integer NOT NULL,
    actual_refund_given integer NOT NULL,
    was_actually_redelivered boolean NOT NULL,
    currency text,
    created_by_id integer,
    credit_refund_error_id integer,
    delivery_id integer
);


--
-- Name: credit_refund_delivery_error_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE credit_refund_delivery_error_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: credit_refund_delivery_error_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE credit_refund_delivery_error_id_seq OWNED BY credit_refund_delivery_error.id;


--
-- Name: credit_refund_error; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE credit_refund_error (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    recommended_credits integer NOT NULL,
    recommended_refund integer NOT NULL,
    is_allowed_redelivery boolean NOT NULL,
    actual_credits_given integer NOT NULL,
    actual_refund_given integer NOT NULL,
    was_actually_redelivered boolean NOT NULL,
    categories jsonb NOT NULL,
    currency text,
    amount_charged_to_store integer NOT NULL,
    created_by_id integer,
    delivery_id integer,
    dispatch_error_id integer,
    redelivery_id integer
);


--
-- Name: credit_refund_error_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE credit_refund_error_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: credit_refund_error_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE credit_refund_error_id_seq OWNED BY credit_refund_error.id;


--
-- Name: credit_refund_order_item_error; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE credit_refund_order_item_error (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    category text NOT NULL,
    recommended_credits integer NOT NULL,
    recommended_refund integer NOT NULL,
    is_allowed_redelivery boolean NOT NULL,
    actual_credits_given integer NOT NULL,
    actual_refund_given integer NOT NULL,
    was_actually_redelivered boolean NOT NULL,
    currency text,
    created_by_id integer,
    credit_refund_error_id integer,
    order_item_id integer,
    order_item_extra_id integer
);


--
-- Name: credit_refund_order_item_error_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE credit_refund_order_item_error_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: credit_refund_order_item_error_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE credit_refund_order_item_error_id_seq OWNED BY credit_refund_order_item_error.id;


--
-- Name: curated_category; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE curated_category (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    start_time timestamp with time zone NOT NULL,
    end_time timestamp with time zone,
    identifier character varying(100) NOT NULL,
    name character varying(100) NOT NULL,
    description character varying(255) NOT NULL,
    display_message character varying(255),
    notes text NOT NULL,
    sort_order integer NOT NULL,
    target_types text NOT NULL,
    image character varying(100),
    large_image character varying(100),
    show_as_carousel boolean,
    submarket_id integer NOT NULL
);


--
-- Name: curated_category_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE curated_category_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: curated_category_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE curated_category_id_seq OWNED BY curated_category.id;


--
-- Name: curated_category_membership; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE curated_category_membership (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    start_time timestamp with time zone NOT NULL,
    end_time timestamp with time zone,
    sort_order integer NOT NULL,
    member_id integer NOT NULL,
    category_id integer NOT NULL,
    member_ct_id integer NOT NULL,
    CONSTRAINT curated_category_membership_member_id_check CHECK ((member_id >= 0))
);


--
-- Name: curated_category_membership_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE curated_category_membership_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: curated_category_membership_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE curated_category_membership_id_seq OWNED BY curated_category_membership.id;


--
-- Name: currency_exchange_rate; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE currency_exchange_rate (
    id integer NOT NULL,
    currency text NOT NULL,
    "timestamp" timestamp with time zone NOT NULL,
    quote double precision NOT NULL
);


--
-- Name: currency_exchange_rate_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE currency_exchange_rate_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: currency_exchange_rate_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE currency_exchange_rate_id_seq OWNED BY currency_exchange_rate.id;


--
-- Name: dasher_capacity_model; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE dasher_capacity_model (
    id integer NOT NULL,
    name text NOT NULL,
    active_date date NOT NULL,
    metadata text,
    weights text NOT NULL,
    normalized_training_mse double precision,
    normalized_testing_mse double precision,
    training_mse double precision,
    testing_mse double precision,
    starting_point_id integer NOT NULL
);


--
-- Name: dasher_capacity_model_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE dasher_capacity_model_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: dasher_capacity_model_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE dasher_capacity_model_id_seq OWNED BY dasher_capacity_model.id;


--
-- Name: dasher_capacity_plan; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE dasher_capacity_plan (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    active_date date NOT NULL,
    supply_target text,
    caps_target text NOT NULL,
    estimated_growth_rate double precision,
    estimated_delivery_distribution text,
    estimated_activation_rates text NOT NULL,
    estimated_incoming_delivery_counts text NOT NULL,
    estimated_outstanding_delivery_counts text,
    estimated_active_efficiencies text,
    ideal_flfs text,
    adjustment_vector text NOT NULL,
    predictor_id text,
    weather_factor text,
    model_id integer,
    starting_point_id integer NOT NULL
);


--
-- Name: dasher_capacity_plan_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE dasher_capacity_plan_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: dasher_capacity_plan_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE dasher_capacity_plan_id_seq OWNED BY dasher_capacity_plan.id;


--
-- Name: dasher_onboarding; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE dasher_onboarding (
    id integer NOT NULL,
    dasher_id integer NOT NULL,
    tier integer NOT NULL,
    onboarded_at timestamp with time zone NOT NULL,
    onboarding_type_id integer NOT NULL
);


--
-- Name: dasher_onboarding_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE dasher_onboarding_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: dasher_onboarding_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE dasher_onboarding_id_seq OWNED BY dasher_onboarding.id;


--
-- Name: dasher_onboarding_type; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE dasher_onboarding_type (
    id integer NOT NULL,
    name text NOT NULL
);


--
-- Name: dasher_onboarding_type_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE dasher_onboarding_type_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: dasher_onboarding_type_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE dasher_onboarding_type_id_seq OWNED BY dasher_onboarding_type.id;


--
-- Name: dd4b_expense_code; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE dd4b_expense_code (
    id integer NOT NULL,
    organization_id bigint NOT NULL,
    expense_code text NOT NULL,
    friendly_name text NOT NULL,
    is_active boolean NOT NULL
);


--
-- Name: dd4b_expense_code_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE dd4b_expense_code_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: dd4b_expense_code_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE dd4b_expense_code_id_seq OWNED BY dd4b_expense_code.id;


--
-- Name: delivery; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE delivery (
    id integer NOT NULL,
    public_id character varying(8) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    cancelled_at timestamp with time zone,
    abandoned_at timestamp with time zone,
    did_respond_to_customer boolean NOT NULL,
    should_be_manually_assigned boolean NOT NULL,
    manually_assigned boolean NOT NULL,
    urgent_cutoff integer,
    is_pending_resolution boolean NOT NULL,
    payout_for_store_no_errors integer,
    dasher_notes text NOT NULL,
    is_asap boolean NOT NULL,
    is_from_store_to_us boolean NOT NULL,
    is_from_partner_store boolean,
    is_consumer_pickup boolean,
    is_depot boolean,
    is_test boolean,
    is_preassign boolean,
    is_preassignable boolean,
    is_route_based_delivery boolean,
    fulfillment_type text,
    is_curbside_dropoff boolean,
    proactive_monitoring_required boolean,
    source text,
    partner_source text,
    signature_required boolean,
    allow_unattended_delivery boolean,
    google_estimate text,
    gmaps_d2r_for_candidates text,
    gmaps_d2r_at_assignment text,
    active_date date,
    assignment_first_considered_time timestamp with time zone,
    first_assignment_made_time timestamp with time zone,
    dasher_assigned_time timestamp with time zone,
    dasher_confirmed_time timestamp with time zone,
    dasher_at_store_time timestamp with time zone,
    dasher_confirmed_at_store_time timestamp with time zone,
    dasher_confirmed_at_consumer_time timestamp with time zone,
    estimated_store_prep_time timestamp with time zone,
    internally_calculated_pickup_time timestamp with time zone,
    actual_pickup_time timestamp with time zone,
    internally_calculated_delivery_time timestamp with time zone,
    actual_delivery_time timestamp with time zone,
    delivery_completed_message text,
    delivery_location text,
    onsite_estimated_prep_time integer,
    onsite_estimated_prep_time_updated_at timestamp with time zone,
    onsite_estimated_prep_time_timestamp timestamp with time zone,
    at_depot_time timestamp with time zone,
    quoted_delivery_time timestamp with time zone,
    eta_prediction_updated_at timestamp with time zone,
    fee integer NOT NULL,
    fee_baserate integer NOT NULL,
    marketing_fee integer,
    boost integer,
    currency text,
    batch_id integer,
    value_of_contents integer,
    cash_on_delivery integer,
    consumer_pickup_auto_closed boolean,
    updated_at timestamp with time zone,
    dasher_wait_until timestamp with time zone,
    market_shortname text,
    starting_point_id integer,
    pickup_location_info text,
    dropoff_location_info text,
    min_age_required integer,
    can_be_batched boolean,
    soft_requirements text,
    serviceable_vehicle_types text,
    order_protocol_type text,
    store_order_confirmed_time timestamp with time zone,
    order_ready_time timestamp with time zone,
    creator_id integer,
    delivery_address_id integer,
    eta_prediction_id integer,
    market integer,
    merchant_transaction_id integer,
    order_cart_id integer,
    parent_delivery_id integer,
    pickup_address_id integer,
    shift_id integer,
    store_id integer NOT NULL,
    store_order_cart_id integer,
    submarket integer,
    transfer_id integer,
    idempotency_key text
);


--
-- Name: delivery_assignment_constraint; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE delivery_assignment_constraint (
    id integer NOT NULL,
    delivery_id integer NOT NULL,
    single_store_batching boolean NOT NULL,
    order_volume integer,
    max_batch_size integer,
    max_mins_allowed_on_road integer,
    pickup_window_start_time timestamp with time zone,
    pickup_window_end_time timestamp with time zone,
    delivery_window_start_time timestamp with time zone,
    delivery_window_end_time timestamp with time zone,
    updated_at timestamp with time zone,
    preferred_dasher_equipment_ids text
);


--
-- Name: delivery_assignment_constraint_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE delivery_assignment_constraint_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: delivery_assignment_constraint_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE delivery_assignment_constraint_id_seq OWNED BY delivery_assignment_constraint.id;


--
-- Name: delivery_batch; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE delivery_batch (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: delivery_batch_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE delivery_batch_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: delivery_batch_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE delivery_batch_id_seq OWNED BY delivery_batch.id;


--
-- Name: delivery_batch_membership; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE delivery_batch_membership (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    sort_index integer NOT NULL,
    batch_id integer NOT NULL,
    delivery_id integer NOT NULL,
    CONSTRAINT delivery_batch_membership_sort_index_check CHECK ((sort_index >= 0))
);


--
-- Name: delivery_batch_membership_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE delivery_batch_membership_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: delivery_batch_membership_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE delivery_batch_membership_id_seq OWNED BY delivery_batch_membership.id;


--
-- Name: delivery_cancellation_reason; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE delivery_cancellation_reason (
    id integer NOT NULL,
    name text NOT NULL,
    friendly_name text NOT NULL,
    sort_order integer,
    category_id integer
);


--
-- Name: delivery_cancellation_reason_category; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE delivery_cancellation_reason_category (
    id integer NOT NULL,
    name text NOT NULL,
    friendly_name text NOT NULL,
    consumer_sms_reason_copy text,
    consumer_email_reason_copy text,
    consumer_email_reason_copy_credit text,
    consumer_email_reason_copy_just_cancel text,
    consumer_email_reason_copy_refund text
);


--
-- Name: delivery_cancellation_reason_category_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE delivery_cancellation_reason_category_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: delivery_cancellation_reason_category_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE delivery_cancellation_reason_category_id_seq OWNED BY delivery_cancellation_reason_category.id;


--
-- Name: delivery_cancellation_reason_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE delivery_cancellation_reason_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: delivery_cancellation_reason_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE delivery_cancellation_reason_id_seq OWNED BY delivery_cancellation_reason.id;


--
-- Name: delivery_catering_verification; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE delivery_catering_verification (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    cancelled_at timestamp with time zone,
    dasher_id integer NOT NULL,
    setup_photo_url character varying(200) NOT NULL,
    setup_waived boolean NOT NULL,
    delivery_id integer NOT NULL
);


--
-- Name: delivery_catering_verification_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE delivery_catering_verification_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: delivery_catering_verification_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE delivery_catering_verification_id_seq OWNED BY delivery_catering_verification.id;


--
-- Name: delivery_drive_info; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE delivery_drive_info (
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    delivery_id integer NOT NULL,
    pickup_business_name text,
    pickup_instructions text,
    pickup_phone_number character varying(30),
    external_order_reference text,
    order_type text,
    order_volume integer,
    verification_type text,
    is_route_based boolean,
    dasher_pay_per_dropoff integer,
    verification_attempts integer,
    accept_dasher_receipts boolean,
    commission_rate numeric(6,3),
    delivery_pay_pad_time integer,
    delivery_radius integer,
    min_fee integer,
    max_fee integer,
    setup_pay integer,
    sof_pay_boost integer,
    requires_catering_setup boolean,
    include_catering_setup boolean,
    searchable text,
    completed_by_preferred_dasher boolean,
    completed_by_drive_dasher boolean,
    delivery_requirements jsonb,
    pickup_window_start_time timestamp with time zone,
    pickup_window_end_time timestamp with time zone,
    delivery_window_start_time timestamp with time zone,
    delivery_window_end_time timestamp with time zone,
    team_lift_required boolean,
    quantity integer,
    is_return_delivery boolean,
    return_type text,
    contains_alcohol boolean,
    min_age_requirement integer,
    commission_subtotal integer,
    commission_tax integer,
    commission_total integer,
    barcode_scanning_required boolean,
    delivery_metadata jsonb,
    allowed_vehicles jsonb,
    tip_pending_until timestamp with time zone,
    return_delivery_id integer,
    CONSTRAINT delivery_drive_info_commission_subtotal_check CHECK ((commission_subtotal >= 0)),
    CONSTRAINT delivery_drive_info_commission_tax_check CHECK ((commission_tax >= 0)),
    CONSTRAINT delivery_drive_info_commission_total_check CHECK ((commission_total >= 0)),
    CONSTRAINT delivery_drive_info_min_age_requirement_check CHECK ((min_age_requirement >= 0))
);


--
-- Name: delivery_error_source; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE delivery_error_source (
    id integer NOT NULL,
    name text NOT NULL
);


--
-- Name: delivery_error_source_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE delivery_error_source_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: delivery_error_source_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE delivery_error_source_id_seq OWNED BY delivery_error_source.id;


--
-- Name: delivery_event; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE delivery_event (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    metadata text NOT NULL,
    category_id integer NOT NULL,
    created_by_id integer,
    delivery_id integer NOT NULL
);


--
-- Name: delivery_event_category; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE delivery_event_category (
    id integer NOT NULL,
    name character varying(140) NOT NULL,
    description text NOT NULL,
    created_at timestamp with time zone NOT NULL,
    can_view text NOT NULL,
    can_create text NOT NULL
);


--
-- Name: delivery_event_category_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE delivery_event_category_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: delivery_event_category_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE delivery_event_category_id_seq OWNED BY delivery_event_category.id;


--
-- Name: delivery_event_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE delivery_event_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: delivery_event_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE delivery_event_id_seq OWNED BY delivery_event.id;


--
-- Name: delivery_fee_promotion; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE delivery_fee_promotion (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    delivery_fee integer NOT NULL,
    min_subtotal integer NOT NULL,
    CONSTRAINT delivery_fee_promotion_delivery_fee_check CHECK ((delivery_fee >= 0)),
    CONSTRAINT delivery_fee_promotion_min_subtotal_check CHECK ((min_subtotal >= 0))
);


--
-- Name: delivery_fee_promotion_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE delivery_fee_promotion_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: delivery_fee_promotion_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE delivery_fee_promotion_id_seq OWNED BY delivery_fee_promotion.id;


--
-- Name: delivery_funding; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE delivery_funding (
    id integer NOT NULL,
    amount integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    created_by_id integer NOT NULL,
    delivery_id integer NOT NULL,
    CONSTRAINT delivery_funding_amount_check CHECK ((amount >= 0))
);


--
-- Name: delivery_funding_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE delivery_funding_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: delivery_funding_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE delivery_funding_id_seq OWNED BY delivery_funding.id;


--
-- Name: delivery_gift; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE delivery_gift (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    value integer NOT NULL,
    currency text,
    code character varying(40) NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    status character varying(20),
    redeemed_at timestamp with time zone,
    consumer_id integer NOT NULL,
    delivery_id integer NOT NULL
);


--
-- Name: delivery_gift_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE delivery_gift_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: delivery_gift_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE delivery_gift_id_seq OWNED BY delivery_gift.id;


--
-- Name: delivery_growth_model; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE delivery_growth_model (
    id integer NOT NULL,
    name text NOT NULL,
    active_date date NOT NULL,
    weights text NOT NULL,
    normalized_training_mse double precision,
    normalized_testing_mse double precision,
    training_mse double precision,
    testing_mse double precision,
    starting_point_id integer NOT NULL
);


--
-- Name: delivery_growth_model_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE delivery_growth_model_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: delivery_growth_model_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE delivery_growth_model_id_seq OWNED BY delivery_growth_model.id;


--
-- Name: delivery_growth_prediction; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE delivery_growth_prediction (
    id integer NOT NULL,
    active_date date NOT NULL,
    created_at timestamp with time zone NOT NULL,
    metadata text,
    prediction text NOT NULL,
    growth_model_id integer,
    starting_point_id integer NOT NULL
);


--
-- Name: delivery_growth_prediction_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE delivery_growth_prediction_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: delivery_growth_prediction_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE delivery_growth_prediction_id_seq OWNED BY delivery_growth_prediction.id;


--
-- Name: delivery_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE delivery_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: delivery_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE delivery_id_seq OWNED BY delivery.id;


--
-- Name: delivery_issue; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE delivery_issue (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    claimed_at timestamp with time zone,
    resolved_at timestamp with time zone,
    notes text NOT NULL,
    salesforce_case_uid text,
    zendesk_id bigint,
    claimed_by_id integer,
    created_by_id integer,
    event_id integer NOT NULL,
    resolved_by_id integer
);


--
-- Name: delivery_issue_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE delivery_issue_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: delivery_issue_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE delivery_issue_id_seq OWNED BY delivery_issue.id;


--
-- Name: delivery_item; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE delivery_item (
    id integer NOT NULL,
    name text NOT NULL,
    description text,
    quantity integer NOT NULL,
    bundle_key text,
    barcode text,
    scan_status text,
    is_damaged boolean,
    delivery_id integer NOT NULL,
    drive_order_id integer,
    external_id text,
    volume numeric(6,3),
    weight numeric(6,3)
);


--
-- Name: delivery_item_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE delivery_item_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: delivery_item_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE delivery_item_id_seq OWNED BY delivery_item.id;


--
-- Name: delivery_masking_number_assignment; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE delivery_masking_number_assignment (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    deactivated_at timestamp with time zone,
    is_active boolean,
    consumer_id integer,
    dasher_id integer,
    store_id integer,
    consumer_phone_number character varying(30),
    dasher_phone_number character varying(30),
    store_phone_number character varying(30),
    participants_type text,
    delivery_id integer NOT NULL,
    twilio_masking_number_id integer
);


--
-- Name: delivery_masking_number_assignment_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE delivery_masking_number_assignment_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: delivery_masking_number_assignment_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE delivery_masking_number_assignment_id_seq OWNED BY delivery_masking_number_assignment.id;


--
-- Name: delivery_rating; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE delivery_rating (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    waived_at timestamp with time zone,
    stars integer NOT NULL,
    comments text NOT NULL,
    dasher_id integer,
    delivery_id integer NOT NULL
);


--
-- Name: delivery_rating_category; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE delivery_rating_category (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    name text NOT NULL,
    description text NOT NULL,
    delivery_method text
);


--
-- Name: delivery_rating_category_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE delivery_rating_category_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: delivery_rating_category_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE delivery_rating_category_id_seq OWNED BY delivery_rating_category.id;


--
-- Name: delivery_rating_category_link; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE delivery_rating_category_link (
    id integer NOT NULL,
    category_id integer NOT NULL,
    rating_id integer NOT NULL
);


--
-- Name: delivery_rating_category_link_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE delivery_rating_category_link_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: delivery_rating_category_link_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE delivery_rating_category_link_id_seq OWNED BY delivery_rating_category_link.id;


--
-- Name: delivery_rating_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE delivery_rating_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: delivery_rating_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE delivery_rating_id_seq OWNED BY delivery_rating.id;


--
-- Name: delivery_receipt; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE delivery_receipt (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    cancelled_at timestamp with time zone,
    viewed_at timestamp with time zone,
    image_url character varying(200) NOT NULL,
    recipient_name text,
    dasher_input_tip_amount integer,
    override_tip_amount integer,
    currency text,
    dasher_creator_id integer NOT NULL,
    delivery_id integer NOT NULL,
    transaction_id integer
);


--
-- Name: delivery_receipt_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE delivery_receipt_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: delivery_receipt_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE delivery_receipt_id_seq OWNED BY delivery_receipt.id;


--
-- Name: delivery_recipient; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE delivery_recipient (
    id integer NOT NULL,
    first_name text,
    last_name text,
    business_name text,
    email character varying(255),
    phone_number character varying(30) NOT NULL
);


--
-- Name: delivery_recipient_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE delivery_recipient_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: delivery_recipient_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE delivery_recipient_id_seq OWNED BY delivery_recipient.id;


--
-- Name: delivery_request; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE delivery_request (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    first_name text NOT NULL,
    last_name text NOT NULL,
    business_name text NOT NULL,
    email character varying(254) NOT NULL,
    phone_number character varying(30) NOT NULL,
    deliver_time timestamp with time zone NOT NULL,
    order_size integer NOT NULL,
    driver_tip integer NOT NULL,
    special_instructions text NOT NULL,
    creator_id integer NOT NULL,
    delivery_id integer,
    dropoff_address_id integer,
    order_cart_id integer NOT NULL,
    pickup_address_id integer NOT NULL,
    store_id integer NOT NULL
);


--
-- Name: delivery_request_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE delivery_request_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: delivery_request_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE delivery_request_id_seq OWNED BY delivery_request.id;


--
-- Name: delivery_request_submission_monitor; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE delivery_request_submission_monitor (
    id integer NOT NULL,
    key text NOT NULL,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: delivery_request_submission_monitor_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE delivery_request_submission_monitor_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: delivery_request_submission_monitor_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE delivery_request_submission_monitor_id_seq OWNED BY delivery_request_submission_monitor.id;


--
-- Name: delivery_set; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE delivery_set (
    id integer NOT NULL,
    assigned_at timestamp with time zone,
    completion_bonus_cents integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    earliest_pickup_time timestamp with time zone NOT NULL,
    latest_delivery_time timestamp with time zone NOT NULL,
    cancelled_at timestamp with time zone,
    completed_at timestamp with time zone,
    should_be_manually_assigned boolean NOT NULL,
    market_id integer NOT NULL
);


--
-- Name: delivery_set_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE delivery_set_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: delivery_set_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE delivery_set_id_seq OWNED BY delivery_set.id;


--
-- Name: delivery_set_mapping; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE delivery_set_mapping (
    id integer NOT NULL,
    delivery_set_id integer NOT NULL,
    delivery_id integer NOT NULL,
    dropoff_route_order integer NOT NULL,
    removed_at timestamp with time zone
);


--
-- Name: delivery_set_mapping_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE delivery_set_mapping_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: delivery_set_mapping_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE delivery_set_mapping_id_seq OWNED BY delivery_set_mapping.id;


--
-- Name: delivery_simulator; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE delivery_simulator (
    delivery_id integer NOT NULL,
    mode text NOT NULL,
    state text NOT NULL,
    in_transition boolean NOT NULL,
    business_id integer,
    drive_order_id integer,
    store_id integer
);


--
-- Name: depot; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE depot (
    id integer NOT NULL,
    config text
);


--
-- Name: depot_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE depot_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: depot_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE depot_id_seq OWNED BY depot.id;


--
-- Name: developer; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE developer (
    user_id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    deactivated_at timestamp with time zone,
    webhook_url text,
    source text,
    business_id integer NOT NULL
);


--
-- Name: device_fingerprint; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE device_fingerprint (
    id integer NOT NULL,
    fingerprint text NOT NULL,
    fingerprint_type text NOT NULL,
    block_reason text,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    metadata jsonb NOT NULL,
    abuse_reason text
);


--
-- Name: device_fingerprint_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE device_fingerprint_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: device_fingerprint_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE device_fingerprint_id_seq OWNED BY device_fingerprint.id;


--
-- Name: dispatch_error; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE dispatch_error (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    consumer_refund integer NOT NULL,
    consumer_charge integer NOT NULL,
    store_charge integer NOT NULL,
    store_refund integer NOT NULL,
    dasher_penalty integer NOT NULL,
    consumer_credits integer NOT NULL,
    currency text,
    category character varying(100) NOT NULL,
    fault text NOT NULL,
    consumer_explanation text NOT NULL,
    store_explanation text NOT NULL,
    dasher_explanation text NOT NULL,
    dispatch_notes text NOT NULL,
    created_by_id integer,
    delivery_id integer,
    order_id integer,
    shift_id integer,
    source_id integer,
    transaction_id integer
);


--
-- Name: dispatch_error_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE dispatch_error_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: dispatch_error_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE dispatch_error_id_seq OWNED BY dispatch_error.id;


--
-- Name: dispatcher; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE dispatcher (
    user_id integer NOT NULL,
    is_active boolean NOT NULL,
    timezone character varying(63) NOT NULL,
    customer_support boolean NOT NULL,
    delivery_support boolean NOT NULL,
    dasher_support boolean NOT NULL,
    market_management_tool boolean NOT NULL,
    can_fund boolean NOT NULL,
    can_refund boolean NOT NULL,
    can_refund_and_mark_fraudulent boolean,
    can_edit_delivery boolean
);


--
-- Name: district; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE district (
    id integer NOT NULL,
    name character varying(100) NOT NULL,
    user_facing_name character varying(100) NOT NULL,
    shortname character varying(4) NOT NULL,
    is_active boolean NOT NULL,
    slug character varying(100) NOT NULL,
    geohash_precision integer,
    is_on_homepage boolean NOT NULL,
    use_tiered_delivery_radius boolean NOT NULL,
    html_color character varying(7) NOT NULL,
    store_radius integer NOT NULL,
    store_road_duration integer,
    previous_store_road_duration integer,
    printable_delivery_hours text NOT NULL,
    delivery_fee_discount_subtotal_threshold integer NOT NULL,
    delivery_fee_discount integer NOT NULL,
    tiered_delivery_fee text,
    first_delivery_price integer NOT NULL,
    price_per_second double precision,
    average_s2c_duration_seconds double precision,
    avg_speed_meters_per_second double precision,
    popular_business_tag_names text NOT NULL,
    override boolean NOT NULL,
    city_id integer,
    market_id integer NOT NULL,
    submarket_id integer NOT NULL,
    CONSTRAINT district_delivery_fee_discount_check CHECK ((delivery_fee_discount >= 0)),
    CONSTRAINT district_delivery_fee_discount_subtotal_threshold_check CHECK ((delivery_fee_discount_subtotal_threshold >= 0))
);


--
-- Name: district_geometry; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE district_geometry (
    district_id integer NOT NULL,
    geom geometry(MultiPolygon,4326)
);


--
-- Name: district_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE district_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: district_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE district_id_seq OWNED BY district.id;


--
-- Name: district_starting_point_availability_override; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE district_starting_point_availability_override (
    id integer NOT NULL,
    district_id integer NOT NULL,
    startingpoint_id integer NOT NULL
);


--
-- Name: district_starting_point_availability_override_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE district_starting_point_availability_override_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: district_starting_point_availability_override_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE district_starting_point_availability_override_id_seq OWNED BY district_starting_point_availability_override.id;


--
-- Name: django_admin_log; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE django_admin_log (
    id integer NOT NULL,
    action_time timestamp with time zone NOT NULL,
    object_id text,
    object_repr character varying(200) NOT NULL,
    action_flag smallint NOT NULL,
    change_message text NOT NULL,
    content_type_id integer,
    user_id integer NOT NULL,
    CONSTRAINT django_admin_log_action_flag_check CHECK ((action_flag >= 0))
);


--
-- Name: django_admin_log_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE django_admin_log_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: django_admin_log_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE django_admin_log_id_seq OWNED BY django_admin_log.id;


--
-- Name: django_content_type; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE django_content_type (
    id integer NOT NULL,
    app_label character varying(100) NOT NULL,
    model character varying(100) NOT NULL
);


--
-- Name: django_content_type_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE django_content_type_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: django_content_type_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE django_content_type_id_seq OWNED BY django_content_type.id;


--
-- Name: django_migrations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE django_migrations (
    id integer NOT NULL,
    app character varying(255) NOT NULL,
    name character varying(255) NOT NULL,
    applied timestamp with time zone NOT NULL
);


--
-- Name: django_migrations_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE django_migrations_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: django_migrations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE django_migrations_id_seq OWNED BY django_migrations.id;


--
-- Name: django_session; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE django_session (
    session_key character varying(40) NOT NULL,
    session_data text NOT NULL,
    expire_date timestamp with time zone NOT NULL
);


--
-- Name: django_twilio_caller; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE django_twilio_caller (
    id integer NOT NULL,
    blacklisted boolean NOT NULL,
    phone_number character varying(128) NOT NULL
);


--
-- Name: django_twilio_caller_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE django_twilio_caller_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: django_twilio_caller_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE django_twilio_caller_id_seq OWNED BY django_twilio_caller.id;


--
-- Name: django_twilio_credential; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE django_twilio_credential (
    id integer NOT NULL,
    name character varying(30) NOT NULL,
    account_sid character varying(34) NOT NULL,
    auth_token character varying(32) NOT NULL,
    user_id integer NOT NULL
);


--
-- Name: django_twilio_credential_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE django_twilio_credential_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: django_twilio_credential_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE django_twilio_credential_id_seq OWNED BY django_twilio_credential.id;


--
-- Name: donation_recipient; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE donation_recipient (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    name text NOT NULL,
    short_description text,
    long_description text,
    logo_image_url text NOT NULL,
    cover_image_url text NOT NULL,
    is_active boolean NOT NULL
);


--
-- Name: donation_recipient_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE donation_recipient_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: donation_recipient_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE donation_recipient_id_seq OWNED BY donation_recipient.id;


--
-- Name: doordash_blacklistedemail; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE doordash_blacklistedemail (
    id integer NOT NULL,
    email character varying(255) NOT NULL,
    blacklisted_at timestamp with time zone NOT NULL,
    reason text NOT NULL,
    blacklisted_by_id integer,
    blacklisted_user_id integer
);


--
-- Name: doordash_blacklistedemail_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE doordash_blacklistedemail_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: doordash_blacklistedemail_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE doordash_blacklistedemail_id_seq OWNED BY doordash_blacklistedemail.id;


--
-- Name: doordash_blacklistedpaymentcard; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE doordash_blacklistedpaymentcard (
    id integer NOT NULL,
    fingerprint text NOT NULL,
    blacklisted_at timestamp with time zone NOT NULL,
    reason text NOT NULL,
    blacklisted_by_id integer,
    blacklisted_user_id integer
);


--
-- Name: doordash_blacklistedpaymentcard_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE doordash_blacklistedpaymentcard_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: doordash_blacklistedpaymentcard_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE doordash_blacklistedpaymentcard_id_seq OWNED BY doordash_blacklistedpaymentcard.id;


--
-- Name: doordash_blacklistedphonenumber; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE doordash_blacklistedphonenumber (
    id integer NOT NULL,
    phone_number character varying(30) NOT NULL,
    blacklisted_at timestamp with time zone NOT NULL,
    reason text NOT NULL,
    blacklisted_by_id integer,
    blacklisted_user_id integer
);


--
-- Name: doordash_blacklistedphonenumber_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE doordash_blacklistedphonenumber_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: doordash_blacklistedphonenumber_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE doordash_blacklistedphonenumber_id_seq OWNED BY doordash_blacklistedphonenumber.id;


--
-- Name: doordash_blacklisteduser; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE doordash_blacklisteduser (
    id integer NOT NULL,
    blacklisted_at timestamp with time zone NOT NULL,
    reason text NOT NULL,
    blacklisted_by_id integer,
    deactivation_source_id integer,
    user_id integer NOT NULL
);


--
-- Name: doordash_blacklisteduser_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE doordash_blacklisteduser_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: doordash_blacklisteduser_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE doordash_blacklisteduser_id_seq OWNED BY doordash_blacklisteduser.id;


--
-- Name: doordash_employmentperiod; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE doordash_employmentperiod (
    id integer NOT NULL,
    employee_id integer NOT NULL,
    hire_date date NOT NULL,
    termination_date date,
    is_intern boolean NOT NULL,
    is_full_time boolean NOT NULL
);


--
-- Name: doordash_employmentperiod_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE doordash_employmentperiod_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: doordash_employmentperiod_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE doordash_employmentperiod_id_seq OWNED BY doordash_employmentperiod.id;


--
-- Name: doordash_orderitemsubstitutionevent; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE doordash_orderitemsubstitutionevent (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    type text NOT NULL,
    order_item_id integer NOT NULL,
    replaced_order_item_id integer
);


--
-- Name: doordash_orderitemsubstitutionevent_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE doordash_orderitemsubstitutionevent_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: doordash_orderitemsubstitutionevent_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE doordash_orderitemsubstitutionevent_id_seq OWNED BY doordash_orderitemsubstitutionevent.id;


--
-- Name: drive_business_mapping; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE drive_business_mapping (
    id integer NOT NULL,
    brand_name text NOT NULL,
    source text NOT NULL,
    business_id integer,
    developer_id integer
);


--
-- Name: drive_business_mapping_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE drive_business_mapping_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: drive_business_mapping_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE drive_business_mapping_id_seq OWNED BY drive_business_mapping.id;


--
-- Name: drive_delivery_identifier_mapping; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE drive_delivery_identifier_mapping (
    created_at timestamp with time zone NOT NULL,
    delivery_id integer NOT NULL,
    drive_order_id bigint,
    external_id text NOT NULL,
    external_source text,
    developer_id integer,
    store_id integer NOT NULL
);


--
-- Name: drive_effort_based_pay_vars; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE drive_effort_based_pay_vars (
    id integer NOT NULL,
    submarket_id integer,
    start_time timestamp with time zone NOT NULL,
    retention_wage integer,
    toll_pay integer,
    large_order_buckets jsonb,
    delivery_pay_floor integer
);


--
-- Name: drive_effort_based_pay_vars_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE drive_effort_based_pay_vars_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: drive_effort_based_pay_vars_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE drive_effort_based_pay_vars_id_seq OWNED BY drive_effort_based_pay_vars.id;


--
-- Name: drive_external_batch_id_mapping; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE drive_external_batch_id_mapping (
    created_at timestamp with time zone NOT NULL,
    delivery_id integer NOT NULL,
    external_batch_id text NOT NULL
);


--
-- Name: drive_order; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE drive_order (
    id integer NOT NULL,
    public_id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    store_id integer,
    driver_reference_tag text,
    quoted_delivery_time timestamp with time zone,
    quoted_pickup_time timestamp with time zone,
    order_type text,
    order_volume integer,
    is_route_based boolean NOT NULL,
    pickup_window_start_time timestamp with time zone,
    pickup_window_end_time timestamp with time zone,
    delivery_window_start_time timestamp with time zone,
    delivery_window_end_time timestamp with time zone,
    delivery_id bigint,
    return_delivery_id bigint,
    accepts_dasher_receipts boolean NOT NULL,
    requires_catering_setup boolean NOT NULL,
    includes_catering_setup boolean NOT NULL,
    requires_barcode_scanning boolean NOT NULL,
    contains_alcohol boolean NOT NULL,
    requires_team_lift boolean NOT NULL,
    requires_signature boolean NOT NULL,
    allow_unattended_delivery boolean NOT NULL,
    allowed_vehicles jsonb,
    min_age_requirement integer,
    tip integer NOT NULL,
    commission_rate numeric(6,3),
    commission_subtotal integer,
    commission_tax integer,
    commission_total integer,
    merchant_payment_transaction_id integer,
    is_asap boolean NOT NULL,
    pickup_instructions text,
    dropoff_instructions text,
    currency text,
    order_value integer,
    delivery_tracking_url text NOT NULL,
    developer_id integer,
    external_delivery_id text,
    num_items integer,
    pickup_address_id integer,
    dropoff_address_id integer,
    delivery_creation_status text,
    delivery_creation_response text,
    task_id text,
    items jsonb,
    customer jsonb NOT NULL,
    delivery_creation_extra_params jsonb,
    return_type text,
    cancelled_at timestamp with time zone,
    external_order_status text,
    aggregator_fee integer,
    post_tip integer,
    CONSTRAINT drive_order_aggregator_fee_check CHECK ((aggregator_fee >= 0)),
    CONSTRAINT drive_order_commission_subtotal_check CHECK ((commission_subtotal >= 0)),
    CONSTRAINT drive_order_commission_tax_check CHECK ((commission_tax >= 0)),
    CONSTRAINT drive_order_commission_total_check CHECK ((commission_total >= 0)),
    CONSTRAINT drive_order_min_age_requirement_check CHECK ((min_age_requirement >= 0))
);


--
-- Name: drive_order_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE drive_order_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: drive_order_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE drive_order_id_seq OWNED BY drive_order.id;


--
-- Name: drive_quote; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE drive_quote (
    created_at timestamp with time zone NOT NULL,
    quote_id uuid NOT NULL,
    delivery_time timestamp with time zone NOT NULL,
    pickup_time timestamp with time zone NOT NULL,
    delivery_fee double precision NOT NULL,
    delivery_fee_subtotal integer,
    delivery_fee_tax integer,
    currency text NOT NULL,
    order_value double precision NOT NULL,
    has_quoted_pickup_time boolean,
    expires_at timestamp with time zone NOT NULL
);


--
-- Name: drive_quote_acceptance; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE drive_quote_acceptance (
    quote_id uuid NOT NULL,
    delivery_id integer NOT NULL,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: drive_store_catering_setup_instruction; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE drive_store_catering_setup_instruction (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    name text NOT NULL,
    store_id integer NOT NULL,
    url text NOT NULL
);


--
-- Name: drive_store_catering_setup_instruction_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE drive_store_catering_setup_instruction_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: drive_store_catering_setup_instruction_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE drive_store_catering_setup_instruction_id_seq OWNED BY drive_store_catering_setup_instruction.id;


--
-- Name: drive_store_id_mapping; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE drive_store_id_mapping (
    store_id integer NOT NULL,
    external_store_id text NOT NULL,
    business_id integer NOT NULL
);


--
-- Name: drive_webhook_event; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE drive_webhook_event (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    payload_url text NOT NULL,
    request_body text,
    exception text,
    retried boolean NOT NULL,
    response_status_code integer,
    request_id text,
    request_retries integer NOT NULL,
    business_id integer NOT NULL,
    delivery_id integer,
    delivery_event_category_id integer NOT NULL
);


--
-- Name: drive_webhook_event_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE drive_webhook_event_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: drive_webhook_event_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE drive_webhook_event_id_seq OWNED BY drive_webhook_event.id;


--
-- Name: drive_webhook_subscription; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE drive_webhook_subscription (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    business_id integer NOT NULL,
    delivery_event_category_id integer NOT NULL
);


--
-- Name: drive_webhook_subscription_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE drive_webhook_subscription_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: drive_webhook_subscription_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE drive_webhook_subscription_id_seq OWNED BY drive_webhook_subscription.id;


--
-- Name: email_holdout_group; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE email_holdout_group (
    id integer NOT NULL,
    name text NOT NULL
);


--
-- Name: email_holdout_group_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE email_holdout_group_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: email_holdout_group_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE email_holdout_group_id_seq OWNED BY email_holdout_group.id;


--
-- Name: email_notification; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE email_notification (
    id integer NOT NULL,
    target_id integer NOT NULL,
    message text NOT NULL,
    created_at timestamp with time zone NOT NULL,
    subject character varying(78) NOT NULL,
    from_email character varying(100) NOT NULL,
    bcc text NOT NULL,
    issue_id integer,
    target_ct_id integer NOT NULL,
    CONSTRAINT email_notification_target_id_check CHECK ((target_id >= 0))
);


--
-- Name: email_notification_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE email_notification_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: email_notification_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE email_notification_id_seq OWNED BY email_notification.id;


--
-- Name: email_preference; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE email_preference (
    id integer NOT NULL,
    name text NOT NULL
);


--
-- Name: email_preference_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE email_preference_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: email_preference_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE email_preference_id_seq OWNED BY email_preference.id;


--
-- Name: email_verification_request; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE email_verification_request (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    token_created_at timestamp with time zone NOT NULL,
    verified_at timestamp with time zone,
    email text,
    token text,
    num_token_generations integer NOT NULL,
    num_verification_attempts integer NOT NULL,
    user_id integer NOT NULL
);


--
-- Name: email_verification_request_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE email_verification_request_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: email_verification_request_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE email_verification_request_id_seq OWNED BY email_verification_request.id;


--
-- Name: employee; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE employee (
    user_id integer NOT NULL,
    title character varying(200) NOT NULL,
    display_name character varying(200) NOT NULL,
    description text NOT NULL,
    profile_picture character varying(100),
    is_active boolean NOT NULL,
    team character varying(100) NOT NULL,
    location character varying(100) NOT NULL,
    birth_date date,
    tshirt_size character varying(100) NOT NULL,
    gender character varying(100) NOT NULL,
    hr_superpower boolean NOT NULL,
    favorite_doordash_store character varying(200) NOT NULL,
    favorite_food_item character varying(200) NOT NULL,
    manager_id integer
);


--
-- Name: employee_monthly_culture_shift; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE employee_monthly_culture_shift (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    shift_type character varying(32) NOT NULL,
    month integer NOT NULL,
    year integer NOT NULL,
    employee_id integer NOT NULL,
    approved_by_id integer,
    approved_at timestamp with time zone,
    rejected_by_id integer,
    rejected_at timestamp with time zone,
    description text NOT NULL,
    metadata jsonb
);


--
-- Name: employee_monthly_culture_shift_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE employee_monthly_culture_shift_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: employee_monthly_culture_shift_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE employee_monthly_culture_shift_id_seq OWNED BY employee_monthly_culture_shift.id;


--
-- Name: estimate; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE estimate (
    id integer NOT NULL,
    start_time timestamp with time zone NOT NULL,
    estimated_at timestamp with time zone NOT NULL,
    estimator_id character varying(255) NOT NULL,
    info text NOT NULL,
    duration interval NOT NULL,
    result_info text NOT NULL,
    target_name character varying(255) NOT NULL,
    delivery_id integer
);


--
-- Name: estimate_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE estimate_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: estimate_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE estimate_id_seq OWNED BY estimate.id;


--
-- Name: eta_prediction; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE eta_prediction (
    id integer NOT NULL,
    predictor_id text NOT NULL,
    is_asap boolean NOT NULL,
    predicted_at timestamp with time zone,
    estimated_assignment_latency integer,
    estimated_assignment_latency_calculated_at timestamp with time zone,
    estimated_order_place_duration integer,
    estimated_order_place_time timestamp with time zone,
    per_starting_point text NOT NULL,
    estimated_prep_duration integer,
    estimated_prep_duration_calculated_at timestamp with time zone,
    estimated_assignment_to_pickup_duration integer,
    estimated_assignment_to_pickup_duration_calculated_at timestamp with time zone,
    estimated_r2c_duration integer,
    estimated_pickup_duration integer,
    estimated_pickup_time timestamp with time zone,
    manual_pickup_time timestamp with time zone,
    ideal_pickup_duration integer,
    ideal_pickup_time timestamp with time zone,
    store_list_asap_duration integer,
    estimated_delivery_duration integer,
    estimated_delivery_time timestamp with time zone,
    quoted_delivery_duration integer,
    quoted_delivery_time timestamp with time zone,
    max_estimated_assignment_latency integer,
    restaurant_min_prep_duration integer,
    restaurant_max_prep_duration integer,
    market_min_asap_duration integer,
    extra_starting_point_pad_duration integer,
    extra_submarket_pad_duration integer,
    prediction_info text,
    features_info text,
    delivery_id integer,
    order_cart_id integer
);


--
-- Name: eta_prediction_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE eta_prediction_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: eta_prediction_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE eta_prediction_id_seq OWNED BY eta_prediction.id;


--
-- Name: experiment; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE experiment (
    id uuid NOT NULL,
    name character varying(250) NOT NULL,
    description text NOT NULL,
    is_active boolean NOT NULL,
    target character varying(50) NOT NULL,
    bucket_key character varying(120) NOT NULL,
    analytics_key character varying(40) NOT NULL,
    whitelist_type character varying(120) NOT NULL,
    whitelist_ids text NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: experiment2; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE experiment2 (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone,
    active_version integer,
    returned_parameters text NOT NULL,
    reserved_mapping text NOT NULL,
    whitelist_type character varying(120),
    whitelist_ids text NOT NULL,
    overrides text NOT NULL,
    default_employee_treatments text,
    default_bucket_key character varying(50),
    target character varying(50) NOT NULL,
    tracking_target character varying(50),
    disable_logging boolean NOT NULL,
    has_frontend_tracking boolean NOT NULL,
    owner_id integer,
    mobile_version_rules text,
    enable_real_time_tracking boolean
);


--
-- Name: experiment2_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE experiment2_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: experiment2_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE experiment2_id_seq OWNED BY experiment2.id;


--
-- Name: experiment_bucket_assignment; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE experiment_bucket_assignment (
    id integer NOT NULL,
    user_id integer NOT NULL,
    experiment_id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    last_accessed_at timestamp with time zone,
    bucket_key character varying(255) NOT NULL
);


--
-- Name: experiment_bucket_assignment_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE experiment_bucket_assignment_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: experiment_bucket_assignment_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE experiment_bucket_assignment_id_seq OWNED BY experiment_bucket_assignment.id;


--
-- Name: experiment_distribution; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE experiment_distribution (
    id integer NOT NULL,
    identifier character varying(100) NOT NULL,
    description text NOT NULL,
    buckets text NOT NULL,
    weights text NOT NULL,
    bucket_index_map text NOT NULL,
    bucket_index_rules text NOT NULL,
    default_employee_value text NOT NULL,
    experiment_id uuid NOT NULL
);


--
-- Name: experiment_distribution_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE experiment_distribution_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: experiment_distribution_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE experiment_distribution_id_seq OWNED BY experiment_distribution.id;


--
-- Name: experiment_override; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE experiment_override (
    id integer NOT NULL,
    bucket text NOT NULL,
    experiment_id uuid NOT NULL,
    user_id integer NOT NULL
);


--
-- Name: experiment_override_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE experiment_override_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: experiment_override_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE experiment_override_id_seq OWNED BY experiment_override.id;


--
-- Name: experiment_user; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE experiment_user (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    original_device_id text,
    original_session_id text,
    user_id integer NOT NULL
);


--
-- Name: experiment_user_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE experiment_user_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: experiment_user_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE experiment_user_id_seq OWNED BY experiment_user.id;


--
-- Name: experiment_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE experiment_version (
    id integer NOT NULL,
    version integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone,
    last_activated_at timestamp with time zone,
    specification text,
    compiled_specification text NOT NULL,
    simple_yaml text,
    experiment_id integer NOT NULL
);


--
-- Name: experiment_version_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE experiment_version_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: experiment_version_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE experiment_version_id_seq OWNED BY experiment_version.id;


--
-- Name: external_request; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE external_request (
    id integer NOT NULL,
    entity_type text NOT NULL,
    entity_id text NOT NULL,
    idempotency_key text NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    started_at timestamp with time zone NOT NULL,
    completed_at timestamp with time zone
);


--
-- Name: external_request_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE external_request_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: external_request_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE external_request_id_seq OWNED BY external_request.id;


--
-- Name: fraud_status; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE fraud_status (
    id integer NOT NULL,
    entity_type text NOT NULL,
    entity_id integer NOT NULL,
    action text NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    status text NOT NULL,
    metadata jsonb NOT NULL,
    CONSTRAINT fraud_status_entity_id_check CHECK ((entity_id >= 0))
);


--
-- Name: fraud_status_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE fraud_status_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: fraud_status_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE fraud_status_id_seq OWNED BY fraud_status.id;


--
-- Name: free_delivery_promotion; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE free_delivery_promotion (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    min_subtotal integer NOT NULL,
    max_value integer,
    CONSTRAINT free_delivery_promotion_max_value_check CHECK ((max_value >= 0)),
    CONSTRAINT free_delivery_promotion_min_subtotal_check CHECK ((min_subtotal >= 0))
);


--
-- Name: free_delivery_promotion_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE free_delivery_promotion_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: free_delivery_promotion_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE free_delivery_promotion_id_seq OWNED BY free_delivery_promotion.id;


--
-- Name: gift_code; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE gift_code (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    last_modified timestamp with time zone NOT NULL,
    value integer NOT NULL,
    currency text,
    code character varying(50) NOT NULL,
    redeemed boolean NOT NULL,
    redeemed_at timestamp with time zone,
    potential_redeemer_email character varying(254) NOT NULL,
    message character varying(255) NOT NULL,
    new_customer_only boolean NOT NULL,
    is_deactivated boolean,
    deactivation_reason text,
    charge_id integer,
    creator_id integer NOT NULL,
    redeemer_id integer
);


--
-- Name: gift_code_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE gift_code_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: gift_code_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE gift_code_id_seq OWNED BY gift_code.id;


--
-- Name: github_activity_metrics; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE github_activity_metrics (
    id integer NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_at timestamp with time zone NOT NULL,
    active_date date NOT NULL,
    type text NOT NULL,
    data text NOT NULL
);


--
-- Name: github_activity_metrics_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE github_activity_metrics_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: github_activity_metrics_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE github_activity_metrics_id_seq OWNED BY github_activity_metrics.id;


--
-- Name: globalvars_gatekeeper; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE globalvars_gatekeeper (
    name character varying(200) NOT NULL,
    staff_users boolean NOT NULL,
    public boolean NOT NULL,
    allowed_emails text NOT NULL
);


--
-- Name: globalvars_variable; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE globalvars_variable (
    key character varying(200) NOT NULL,
    value text NOT NULL,
    can_view text NOT NULL,
    can_edit text
);


--
-- Name: grab_pay_account; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE grab_pay_account (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    status text,
    bind_token text,
    additional_data jsonb,
    idempotency_key text,
    grab_pay_transaction_id text,
    consumer_id integer NOT NULL
);


--
-- Name: grab_pay_account_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE grab_pay_account_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: grab_pay_account_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE grab_pay_account_id_seq OWNED BY grab_pay_account.id;


--
-- Name: grab_pay_charge; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE grab_pay_charge (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    currency text,
    status text,
    amount integer NOT NULL,
    amount_refunded integer,
    description text,
    error_reason text,
    additional_data jsonb,
    idempotency_key text,
    grab_pay_transaction_id text,
    charge_id integer NOT NULL,
    grab_pay_account_id integer NOT NULL
);


--
-- Name: grab_pay_charge_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE grab_pay_charge_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: grab_pay_charge_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE grab_pay_charge_id_seq OWNED BY grab_pay_charge.id;


--
-- Name: grab_payment_account; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE grab_payment_account (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    safe_id text NOT NULL,
    country_shortname text
);


--
-- Name: grab_payment_account_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE grab_payment_account_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: grab_payment_account_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE grab_payment_account_id_seq OWNED BY grab_payment_account.id;


--
-- Name: grab_transfer; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE grab_transfer (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    grab_pay_transfer_id character varying(50) NOT NULL,
    grab_pay_status character varying(10) NOT NULL,
    grab_pay_failure_code character varying(50),
    grab_pay_failure_message character varying(100),
    idempotency_key text,
    original_grab_pay_transfer_id text,
    grab_pay_account_type text,
    country_shortname text,
    transfer_id integer NOT NULL
);


--
-- Name: grab_transfer_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE grab_transfer_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: grab_transfer_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE grab_transfer_id_seq OWNED BY grab_transfer.id;


--
-- Name: guest_user_type; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE guest_user_type (
    id integer NOT NULL,
    name text NOT NULL
);


--
-- Name: guest_user_type_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE guest_user_type_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: guest_user_type_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE guest_user_type_id_seq OWNED BY guest_user_type.id;


--
-- Name: invoicing_group; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE invoicing_group (
    id integer NOT NULL,
    name text NOT NULL,
    netsuite_entity_id text,
    netsuite_market_name text,
    netsuite_customform_id text,
    export_external_order_reference boolean,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: invoicing_group_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE invoicing_group_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: invoicing_group_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE invoicing_group_id_seq OWNED BY invoicing_group.id;


--
-- Name: invoicing_group_membership; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE invoicing_group_membership (
    id integer NOT NULL,
    store_id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    invoicing_group_id integer NOT NULL
);


--
-- Name: invoicing_group_membership_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE invoicing_group_membership_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: invoicing_group_membership_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE invoicing_group_membership_id_seq OWNED BY invoicing_group_membership.id;


--
-- Name: invoicing_group_onboarding_rule; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE invoicing_group_onboarding_rule (
    id integer NOT NULL,
    entity_type text NOT NULL,
    entity_id text NOT NULL,
    created_at timestamp with time zone NOT NULL,
    invoicing_group_id integer NOT NULL
);


--
-- Name: invoicing_group_onboarding_rule_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE invoicing_group_onboarding_rule_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: invoicing_group_onboarding_rule_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE invoicing_group_onboarding_rule_id_seq OWNED BY invoicing_group_onboarding_rule.id;


--
-- Name: ios_notifications_apnservice; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE ios_notifications_apnservice (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    hostname character varying(255) NOT NULL,
    certificate text NOT NULL,
    private_key text NOT NULL,
    passphrase character varying(229)
);


--
-- Name: ios_notifications_apnservice_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE ios_notifications_apnservice_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: ios_notifications_apnservice_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE ios_notifications_apnservice_id_seq OWNED BY ios_notifications_apnservice.id;


--
-- Name: ios_notifications_device; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE ios_notifications_device (
    id integer NOT NULL,
    token character varying(64) NOT NULL,
    is_active boolean NOT NULL,
    deactivated_at timestamp with time zone,
    added_at timestamp with time zone NOT NULL,
    last_notified_at timestamp with time zone,
    platform character varying(30),
    display character varying(30),
    os_version character varying(20),
    service_id integer NOT NULL
);


--
-- Name: ios_notifications_device_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE ios_notifications_device_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: ios_notifications_device_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE ios_notifications_device_id_seq OWNED BY ios_notifications_device.id;


--
-- Name: ios_notifications_device_users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE ios_notifications_device_users (
    id integer NOT NULL,
    device_id integer NOT NULL,
    user_id integer NOT NULL
);


--
-- Name: ios_notifications_device_users_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE ios_notifications_device_users_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: ios_notifications_device_users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE ios_notifications_device_users_id_seq OWNED BY ios_notifications_device_users.id;


--
-- Name: ios_notifications_feedbackservice; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE ios_notifications_feedbackservice (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    hostname character varying(255) NOT NULL,
    apn_service_id integer NOT NULL
);


--
-- Name: ios_notifications_feedbackservice_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE ios_notifications_feedbackservice_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: ios_notifications_feedbackservice_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE ios_notifications_feedbackservice_id_seq OWNED BY ios_notifications_feedbackservice.id;


--
-- Name: ios_notifications_notification; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE ios_notifications_notification (
    id integer NOT NULL,
    message character varying(200) NOT NULL,
    badge integer,
    sound character varying(30) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    last_sent_at timestamp with time zone,
    custom_payload character varying(240) NOT NULL,
    service_id integer NOT NULL,
    silent boolean,
    loc_payload character varying(240) NOT NULL,
    CONSTRAINT ios_notifications_notification_badge_check CHECK ((badge >= 0))
);


--
-- Name: ios_notifications_notification_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE ios_notifications_notification_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: ios_notifications_notification_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE ios_notifications_notification_id_seq OWNED BY ios_notifications_notification.id;


--
-- Name: kill_switch_interval; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE kill_switch_interval (
    id integer NOT NULL,
    date date NOT NULL,
    start_time time without time zone NOT NULL,
    end_time time without time zone,
    start_datetime timestamp with time zone,
    end_datetime timestamp with time zone,
    killed_by_id integer,
    starting_point_id integer NOT NULL,
    unkilled_by_id integer
);


--
-- Name: kill_switch_interval_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE kill_switch_interval_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: kill_switch_interval_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE kill_switch_interval_id_seq OWNED BY kill_switch_interval.id;


--
-- Name: managed_account_transfer; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE managed_account_transfer (
    id integer NOT NULL,
    account_id integer,
    amount integer NOT NULL,
    currency text,
    stripe_id character varying(50) NOT NULL,
    stripe_status character varying(10) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    submitted_at timestamp with time zone,
    account_ct_id integer,
    payment_account_id integer,
    transfer_id integer NOT NULL,
    CONSTRAINT managed_account_transfer_account_id_check CHECK ((account_id >= 0))
);


--
-- Name: managed_account_transfer_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE managed_account_transfer_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: managed_account_transfer_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE managed_account_transfer_id_seq OWNED BY managed_account_transfer.id;


--
-- Name: market; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE market (
    id integer NOT NULL,
    name character varying(100) NOT NULL,
    shortname character varying(4) NOT NULL,
    is_active boolean NOT NULL,
    is_acquiring_dashers boolean NOT NULL,
    is_at_dasher_capacity boolean NOT NULL,
    local_team_email text NOT NULL,
    performance_score_threshold_for_drive integer NOT NULL,
    orientation_length integer NOT NULL,
    virtual_orientation_passing_threshold integer,
    bounds geometry(Polygon,4326),
    center geometry(Point,4326),
    timezone character varying(63) NOT NULL,
    tax_rate_override numeric(6,3),
    min_asap_time integer NOT NULL,
    under_dr_control boolean NOT NULL,
    use_dr_etas boolean NOT NULL,
    always_run_fallback_assigner boolean NOT NULL,
    country_id integer NOT NULL,
    region_id integer,
    subnational_division_id integer NOT NULL,
    virtual_orientation_slide_deck_id integer,
    virtual_orientation_slide_deck_bikes_only_id integer,
    updated_at timestamp with time zone
);


--
-- Name: market_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE market_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: market_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE market_id_seq OWNED BY market.id;


--
-- Name: market_special_hours; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE market_special_hours (
    id integer NOT NULL,
    date date NOT NULL,
    start_time time without time zone NOT NULL,
    end_time time without time zone NOT NULL,
    closed boolean NOT NULL,
    market_id integer NOT NULL
);


--
-- Name: market_special_hours_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE market_special_hours_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: market_special_hours_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE market_special_hours_id_seq OWNED BY market_special_hours.id;


--
-- Name: marqeta_card; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE marqeta_card (
    token character varying(36) NOT NULL,
    delight_number integer NOT NULL,
    terminated_at timestamp with time zone,
    last4 character varying(4) NOT NULL
);


--
-- Name: marqeta_card_ownership; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE marqeta_card_ownership (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    ended_at timestamp with time zone,
    card_id character varying(36) NOT NULL,
    dasher_id integer NOT NULL
);


--
-- Name: marqeta_card_ownership_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE marqeta_card_ownership_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: marqeta_card_ownership_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE marqeta_card_ownership_id_seq OWNED BY marqeta_card_ownership.id;


--
-- Name: marqeta_card_transition; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE marqeta_card_transition (
    id integer NOT NULL,
    succeeded_at timestamp with time zone,
    aborted_at timestamp with time zone,
    created_at timestamp with time zone NOT NULL,
    desired_state character varying(25) NOT NULL,
    card_id character varying(36) NOT NULL,
    shift_id integer
);


--
-- Name: marqeta_card_transition_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE marqeta_card_transition_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: marqeta_card_transition_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE marqeta_card_transition_id_seq OWNED BY marqeta_card_transition.id;


--
-- Name: marqeta_decline_exemption; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE marqeta_decline_exemption (
    id integer NOT NULL,
    amount integer NOT NULL,
    mid text NOT NULL,
    delivery_id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    used_at timestamp with time zone,
    dasher_id integer NOT NULL,
    created_by_id integer NOT NULL,
    CONSTRAINT marqeta_decline_exemption_amount_check CHECK ((amount >= 0))
);


--
-- Name: marqeta_decline_exemption_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE marqeta_decline_exemption_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: marqeta_decline_exemption_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE marqeta_decline_exemption_id_seq OWNED BY marqeta_decline_exemption.id;


--
-- Name: marqeta_transaction; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE marqeta_transaction (
    id integer NOT NULL,
    token text NOT NULL,
    amount integer NOT NULL,
    swiped_at timestamp with time zone NOT NULL,
    card_acceptor text NOT NULL,
    currency text,
    timed_out boolean,
    delivery_id integer NOT NULL
);


--
-- Name: marqeta_transaction_event; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE marqeta_transaction_event (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    token character varying(36) NOT NULL,
    amount integer NOT NULL,
    transaction_type character varying(25) NOT NULL,
    metadata text NOT NULL,
    raw_type character varying(50) NOT NULL,
    card_acceptor_id integer,
    ownership_id integer NOT NULL,
    shift_id integer
);


--
-- Name: marqeta_transaction_event_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE marqeta_transaction_event_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: marqeta_transaction_event_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE marqeta_transaction_event_id_seq OWNED BY marqeta_transaction_event.id;


--
-- Name: marqeta_transaction_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE marqeta_transaction_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: marqeta_transaction_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE marqeta_transaction_id_seq OWNED BY marqeta_transaction.id;


--
-- Name: mass_communication_status; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE mass_communication_status (
    id integer NOT NULL,
    message_uuid character varying(128) NOT NULL,
    source character varying(100) NOT NULL,
    message text NOT NULL,
    total_requests integer NOT NULL,
    in_progress integer NOT NULL,
    received_status integer NOT NULL,
    failed integer NOT NULL,
    delayed_by_5min integer NOT NULL,
    delayed_by_10min integer NOT NULL,
    delayed_by_15min integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    sender_id integer NOT NULL,
    CONSTRAINT mass_communication_status_delayed_by_10min_check CHECK ((delayed_by_10min >= 0)),
    CONSTRAINT mass_communication_status_delayed_by_15min_check CHECK ((delayed_by_15min >= 0)),
    CONSTRAINT mass_communication_status_delayed_by_5min_check CHECK ((delayed_by_5min >= 0)),
    CONSTRAINT mass_communication_status_failed_check CHECK ((failed >= 0)),
    CONSTRAINT mass_communication_status_in_progress_check CHECK ((in_progress >= 0)),
    CONSTRAINT mass_communication_status_received_status_check CHECK ((received_status >= 0)),
    CONSTRAINT mass_communication_status_total_requests_check CHECK ((total_requests >= 0))
);


--
-- Name: mass_communication_status_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE mass_communication_status_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: mass_communication_status_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE mass_communication_status_id_seq OWNED BY mass_communication_status.id;


--
-- Name: multi_promotion; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE multi_promotion (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    delivery_fee integer,
    service_rate numeric(6,3),
    extra_sos_fee integer,
    discount_percentage numeric(6,3),
    discount_value integer,
    max_discount integer,
    currency text,
    min_subtotal integer NOT NULL,
    discount_type text,
    CONSTRAINT multi_promotion_delivery_fee_check CHECK ((delivery_fee >= 0)),
    CONSTRAINT multi_promotion_discount_value_check CHECK ((discount_value >= 0)),
    CONSTRAINT multi_promotion_extra_sos_fee_check CHECK ((extra_sos_fee >= 0)),
    CONSTRAINT multi_promotion_max_discount_check CHECK ((max_discount >= 0)),
    CONSTRAINT multi_promotion_min_subtotal_check CHECK ((min_subtotal >= 0))
);


--
-- Name: multi_promotion_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE multi_promotion_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: multi_promotion_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE multi_promotion_id_seq OWNED BY multi_promotion.id;


--
-- Name: order; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE "order" (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    cancelled_at timestamp with time zone,
    last_modified timestamp with time zone,
    dd4b_expense_code text,
    consumer_id integer,
    menu_id integer,
    order_cart_id integer,
    store_id integer,
    store_order_cart_id integer
);


--
-- Name: order_cart; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE order_cart (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    submitted_at timestamp with time zone,
    cancelled_at timestamp with time zone,
    fulfilled_at timestamp with time zone,
    url_code character varying(40) NOT NULL,
    order_special_instructions text NOT NULL,
    dasher_instructions text,
    subpremise text,
    payment_policy character varying(100) NOT NULL,
    group_cart boolean NOT NULL,
    max_individual_cost integer,
    max_individuals integer,
    hide_other_individual_orders boolean,
    auto_checkout_time timestamp with time zone,
    split_bill boolean,
    locked boolean NOT NULL,
    is_first_ordercart boolean NOT NULL,
    is_reorder boolean,
    amount_paid_out_to_store integer,
    currency text,
    extra_cart_order_fee integer,
    min_order_subtotal integer,
    charge_id integer,
    submit_platform character varying(16),
    submission_attributes jsonb,
    is_bike_friendly boolean NOT NULL,
    is_bike_friendly_updated_at timestamp with time zone,
    min_age_requirement integer NOT NULL,
    min_age_requirement_updated_at timestamp with time zone,
    omnivore_id text,
    merchant_supplied_id text,
    is_fraudulent boolean,
    refunded_as_fraudulent boolean,
    business_referral_id integer,
    creator_id integer NOT NULL,
    delivery_address_id integer,
    payment_card_id integer,
    payment_method_id integer,
    pricing_strategy_id integer,
    promo_code_id integer
);


--
-- Name: order_cart_consumer_promotion_link; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE order_cart_consumer_promotion_link (
    id integer NOT NULL,
    created_at timestamp with time zone,
    consumer_promotion_id integer NOT NULL,
    order_cart_id integer NOT NULL
);


--
-- Name: order_cart_consumer_promotion_link_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE order_cart_consumer_promotion_link_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: order_cart_consumer_promotion_link_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE order_cart_consumer_promotion_link_id_seq OWNED BY order_cart_consumer_promotion_link.id;


--
-- Name: order_cart_device_fingerprint_link; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE order_cart_device_fingerprint_link (
    id integer NOT NULL,
    source text,
    metadata jsonb NOT NULL,
    fingerprint_id integer NOT NULL,
    order_cart_id integer NOT NULL
);


--
-- Name: order_cart_device_fingerprint_link_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE order_cart_device_fingerprint_link_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: order_cart_device_fingerprint_link_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE order_cart_device_fingerprint_link_id_seq OWNED BY order_cart_device_fingerprint_link.id;


--
-- Name: order_cart_discount; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE order_cart_discount (
    id integer NOT NULL,
    support_credit integer NOT NULL,
    first_delivery_discount integer NOT NULL,
    upsell_delivery_discount integer,
    referree_credit integer NOT NULL,
    referrer_credit integer NOT NULL,
    gift_code_credit integer NOT NULL,
    delivery_gift_credit integer NOT NULL,
    first_time_promo_code_credit integer NOT NULL,
    promo_code_credit integer NOT NULL,
    delivery_update_credit integer NOT NULL,
    manual_credit integer,
    discount_percent integer,
    discount_percent_max_credit integer,
    accounting_consistency_credit integer NOT NULL,
    other_credit integer NOT NULL,
    currency text,
    updated_at timestamp with time zone NOT NULL,
    order_cart_id integer NOT NULL
);


--
-- Name: order_cart_discount_component; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE order_cart_discount_component (
    id integer NOT NULL,
    monetary_field text,
    source_id integer,
    "group" text,
    amount integer,
    status text,
    delivery_fee integer,
    service_rate numeric(6,3),
    extra_sos_fee integer,
    discount_percentage numeric(6,3),
    max_discount integer,
    minimum_subtotal integer NOT NULL,
    metadata jsonb NOT NULL,
    currency text,
    updated_at timestamp with time zone NOT NULL,
    order_cart_id integer NOT NULL,
    source_type_id integer NOT NULL,
    store_order_cart_id integer
);


--
-- Name: order_cart_discount_component_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE order_cart_discount_component_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: order_cart_discount_component_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE order_cart_discount_component_id_seq OWNED BY order_cart_discount_component.id;


--
-- Name: order_cart_discount_component_source_type; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE order_cart_discount_component_source_type (
    id integer NOT NULL,
    name text,
    source_model_name text,
    "group" text,
    priority integer,
    is_refundable boolean NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: order_cart_discount_component_source_type_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE order_cart_discount_component_source_type_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: order_cart_discount_component_source_type_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE order_cart_discount_component_source_type_id_seq OWNED BY order_cart_discount_component_source_type.id;


--
-- Name: order_cart_discount_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE order_cart_discount_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: order_cart_discount_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE order_cart_discount_id_seq OWNED BY order_cart_discount.id;


--
-- Name: order_cart_escalation; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE order_cart_escalation (
    created_at timestamp with time zone NOT NULL,
    reviewed_at timestamp with time zone,
    order_cart_id integer NOT NULL,
    status text NOT NULL,
    notes text NOT NULL,
    reviewed_by_id integer,
    stripe_charge_id integer
);


--
-- Name: order_cart_escalation_reason; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE order_cart_escalation_reason (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    escalation_type text NOT NULL,
    detail text NOT NULL,
    escalation_id integer NOT NULL
);


--
-- Name: order_cart_escalation_reason_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE order_cart_escalation_reason_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: order_cart_escalation_reason_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE order_cart_escalation_reason_id_seq OWNED BY order_cart_escalation_reason.id;


--
-- Name: order_cart_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE order_cart_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: order_cart_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE order_cart_id_seq OWNED BY order_cart.id;


--
-- Name: order_cart_pricing_strategy; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE order_cart_pricing_strategy (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    strategy_type text NOT NULL
);


--
-- Name: order_cart_pricing_strategy_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE order_cart_pricing_strategy_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: order_cart_pricing_strategy_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE order_cart_pricing_strategy_id_seq OWNED BY order_cart_pricing_strategy.id;


--
-- Name: order_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE order_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: order_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE order_id_seq OWNED BY "order".id;


--
-- Name: order_item; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE order_item (
    id integer NOT NULL,
    created_at timestamp with time zone,
    item jsonb,
    quantity integer NOT NULL,
    special_instructions text NOT NULL,
    original_item_price integer NOT NULL,
    additional_cost integer NOT NULL,
    removed_at timestamp with time zone,
    is_recommendation boolean,
    substitution_preference character varying(100),
    num_missing integer,
    num_incorrect integer,
    subtotal integer,
    legacy_inflation_amount integer,
    bottle_deposit_amount integer,
    tax_amount integer,
    unit_price integer,
    unit_legacy_inflation_amount integer,
    discount_source text,
    item_id integer NOT NULL,
    order_id integer NOT NULL,
    store_id integer
);


--
-- Name: order_item_extra_option; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE order_item_extra_option (
    id integer NOT NULL,
    created_at timestamp with time zone,
    child_options jsonb,
    quantity integer,
    is_free boolean NOT NULL,
    item_extra_option jsonb,
    original_option_price integer NOT NULL,
    item_extra_option_id integer NOT NULL,
    order_item_id integer NOT NULL,
    parent_order_item_extra_option_id integer
);


--
-- Name: order_item_extra_option_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE order_item_extra_option_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: order_item_extra_option_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE order_item_extra_option_id_seq OWNED BY order_item_extra_option.id;


--
-- Name: order_item_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE order_item_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: order_item_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE order_item_id_seq OWNED BY order_item.id;


--
-- Name: order_menu_option; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE order_menu_option (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    selection boolean,
    option_id integer NOT NULL,
    order_id integer NOT NULL
);


--
-- Name: order_menu_option_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE order_menu_option_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: order_menu_option_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE order_menu_option_id_seq OWNED BY order_menu_option.id;


--
-- Name: order_placer_queue_state; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE order_placer_queue_state (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    queue_length integer NOT NULL,
    number_of_order_placers integer NOT NULL,
    order_placer_ids text NOT NULL,
    delivery_ids text NOT NULL
);


--
-- Name: order_placer_queue_state_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE order_placer_queue_state_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: order_placer_queue_state_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE order_placer_queue_state_id_seq OWNED BY order_placer_queue_state.id;


--
-- Name: payment_account; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE payment_account (
    id integer NOT NULL,
    account_type text,
    account_id integer,
    entity text,
    old_account_id integer,
    upgraded_to_managed_account_at timestamp with time zone,
    is_verified_with_stripe boolean,
    transfers_enabled boolean,
    charges_enabled boolean,
    statement_descriptor text NOT NULL,
    created_at timestamp with time zone,
    payout_disabled boolean,
    resolve_outstanding_balance_frequency text,
    CONSTRAINT payment_account_account_id_check CHECK ((account_id >= 0)),
    CONSTRAINT payment_account_old_account_id_check CHECK ((old_account_id >= 0))
);


--
-- Name: payment_account_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE payment_account_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: payment_account_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE payment_account_id_seq OWNED BY payment_account.id;


--
-- Name: payment_method; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE payment_method (
    id integer NOT NULL,
    name text NOT NULL
);


--
-- Name: payment_method_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE payment_method_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: payment_method_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE payment_method_id_seq OWNED BY payment_method.id;


--
-- Name: percentage_promotion; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE percentage_promotion (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    discount_percent integer NOT NULL,
    discount_percent_max_credit integer,
    min_subtotal integer NOT NULL,
    CONSTRAINT percentage_promotion_discount_percent_check CHECK ((discount_percent >= 0)),
    CONSTRAINT percentage_promotion_discount_percent_max_credit_check CHECK ((discount_percent_max_credit >= 0)),
    CONSTRAINT percentage_promotion_min_subtotal_check CHECK ((min_subtotal >= 0))
);


--
-- Name: percentage_promotion_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE percentage_promotion_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: percentage_promotion_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE percentage_promotion_id_seq OWNED BY percentage_promotion.id;


--
-- Name: place_tag; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE place_tag (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    name character varying(40) NOT NULL
);


--
-- Name: place_tag_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE place_tag_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: place_tag_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE place_tag_id_seq OWNED BY place_tag.id;


--
-- Name: platform; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE platform (
    id integer NOT NULL,
    name text NOT NULL
);


--
-- Name: platform_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE platform_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: platform_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE platform_id_seq OWNED BY platform.id;


--
-- Name: price_transparency_bucket_assignments; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE price_transparency_bucket_assignments (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    bucket integer NOT NULL,
    consumer_id integer NOT NULL
);


--
-- Name: price_transparency_bucket_assignments_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE price_transparency_bucket_assignments_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: price_transparency_bucket_assignments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE price_transparency_bucket_assignments_id_seq OWNED BY price_transparency_bucket_assignments.id;


--
-- Name: promo_code; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE promo_code (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    last_modified timestamp with time zone NOT NULL,
    start_date timestamp with time zone NOT NULL,
    end_date timestamp with time zone NOT NULL,
    discount_percent integer,
    value integer NOT NULL,
    "limit" integer,
    discount_percent_max_credit integer,
    code character varying(50) NOT NULL,
    channel character varying(100),
    restricted_to_market boolean NOT NULL,
    restricted_to_submarket boolean,
    notes text NOT NULL,
    cuisine_promo text NOT NULL,
    item_promo text NOT NULL,
    store_ids_for_promo text NOT NULL,
    new_customer_only boolean NOT NULL,
    min_subtotal integer NOT NULL
);


--
-- Name: promo_code_consumer_link; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE promo_code_consumer_link (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    consumer_id integer NOT NULL,
    promo_code_id integer NOT NULL
);


--
-- Name: promo_code_consumer_link_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE promo_code_consumer_link_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: promo_code_consumer_link_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE promo_code_consumer_link_id_seq OWNED BY promo_code_consumer_link.id;


--
-- Name: promo_code_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE promo_code_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: promo_code_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE promo_code_id_seq OWNED BY promo_code.id;


--
-- Name: promo_code_markets; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE promo_code_markets (
    id integer NOT NULL,
    promocode_id integer NOT NULL,
    market_id integer NOT NULL
);


--
-- Name: promo_code_markets_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE promo_code_markets_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: promo_code_markets_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE promo_code_markets_id_seq OWNED BY promo_code_markets.id;


--
-- Name: promo_code_submarket_link; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE promo_code_submarket_link (
    id integer NOT NULL,
    promo_code_id integer NOT NULL,
    submarket_id integer NOT NULL
);


--
-- Name: promo_code_submarket_link_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE promo_code_submarket_link_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: promo_code_submarket_link_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE promo_code_submarket_link_id_seq OWNED BY promo_code_submarket_link.id;


--
-- Name: promotion_consumer_link; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE promotion_consumer_link (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    num_remaining_deliveries integer,
    num_deliveries_redeemed integer,
    consumer_id integer NOT NULL,
    promotion_id integer NOT NULL,
    CONSTRAINT promotion_consumer_link_num_remaining_deliveries_check CHECK ((num_remaining_deliveries >= 0))
);


--
-- Name: promotion_consumer_link_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE promotion_consumer_link_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: promotion_consumer_link_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE promotion_consumer_link_id_seq OWNED BY promotion_consumer_link.id;


--
-- Name: promotion_featured_location_link; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE promotion_featured_location_link (
    id integer NOT NULL,
    featured_location_id integer NOT NULL,
    promotion_id integer NOT NULL
);


--
-- Name: promotion_featured_location_link_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE promotion_featured_location_link_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: promotion_featured_location_link_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE promotion_featured_location_link_id_seq OWNED BY promotion_featured_location_link.id;


--
-- Name: promotion_place_tag_link; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE promotion_place_tag_link (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    place_tag_id integer NOT NULL,
    promotion_id integer NOT NULL
);


--
-- Name: promotion_place_tag_link_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE promotion_place_tag_link_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: promotion_place_tag_link_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE promotion_place_tag_link_id_seq OWNED BY promotion_place_tag_link.id;


--
-- Name: promotion_redemption_event; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE promotion_redemption_event (
    id integer NOT NULL,
    "timestamp" timestamp with time zone NOT NULL,
    timezone character varying(63),
    order_cart_id integer NOT NULL,
    promotion_id integer NOT NULL,
    promotion_campaign_id integer,
    region_id integer NOT NULL,
    store_id integer NOT NULL
);


--
-- Name: promotion_redemption_event_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE promotion_redemption_event_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: promotion_redemption_event_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE promotion_redemption_event_id_seq OWNED BY promotion_redemption_event.id;


--
-- Name: promotion_submarket_link; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE promotion_submarket_link (
    id integer NOT NULL,
    promotion_id integer NOT NULL,
    submarket_id integer NOT NULL
);


--
-- Name: promotion_submarket_link_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE promotion_submarket_link_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: promotion_submarket_link_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE promotion_submarket_link_id_seq OWNED BY promotion_submarket_link.id;


--
-- Name: promotions_featured_location; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE promotions_featured_location (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    name character varying(128) NOT NULL,
    location_on_app character varying(128) NOT NULL,
    show_only_once boolean NOT NULL,
    feature_component character varying(128) NOT NULL,
    cover_image character varying(100),
    title text,
    description text,
    props jsonb,
    user_state text,
    next_featured_location_id integer
);


--
-- Name: promotions_featured_location_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE promotions_featured_location_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: promotions_featured_location_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE promotions_featured_location_id_seq OWNED BY promotions_featured_location.id;


--
-- Name: real_time_supply_model; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE real_time_supply_model (
    id integer NOT NULL,
    name text NOT NULL,
    active_date date NOT NULL,
    metadata text,
    weights text NOT NULL,
    normalized_training_mse double precision,
    normalized_testing_mse double precision,
    training_mse double precision,
    testing_mse double precision,
    starting_point_id integer NOT NULL
);


--
-- Name: real_time_supply_model_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE real_time_supply_model_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: real_time_supply_model_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE real_time_supply_model_id_seq OWNED BY real_time_supply_model.id;


--
-- Name: real_time_supply_prediction; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE real_time_supply_prediction (
    id integer NOT NULL,
    active_date date NOT NULL,
    created_at timestamp with time zone NOT NULL,
    metadata text,
    prediction text NOT NULL,
    starting_point_id integer NOT NULL,
    supply_model_id integer
);


--
-- Name: real_time_supply_prediction_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE real_time_supply_prediction_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: real_time_supply_prediction_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE real_time_supply_prediction_id_seq OWNED BY real_time_supply_prediction.id;


--
-- Name: realtime_demand_evaluation; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE realtime_demand_evaluation (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    active_date date NOT NULL,
    metadata jsonb,
    eyeballing_count_sum_prediction_list jsonb,
    outstanding_orders_mean_prediction_list jsonb,
    eyeballing_count_sum_target_list jsonb,
    outstanding_orders_mean_target_list jsonb,
    starting_point_id integer NOT NULL
);


--
-- Name: realtime_demand_evaluation_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE realtime_demand_evaluation_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: realtime_demand_evaluation_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE realtime_demand_evaluation_id_seq OWNED BY realtime_demand_evaluation.id;


--
-- Name: referral_programs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE referral_programs (
    id integer NOT NULL,
    name text,
    referrer_amount integer,
    referree_amount integer,
    referree_promotion_id integer,
    min_referree_order_subtotal integer,
    referree_invite_title text,
    referree_invite_subtitle text,
    referree_invite_sms_text text,
    referree_acceptance_title text,
    referree_acceptance_subtitle text,
    referree_acceptance_annotation text,
    referree_invite_email_subject text,
    referree_invite_email_body text,
    referree_acceptance_annotation_fr_ca text,
    referree_acceptance_subtitle_fr_ca text,
    referree_acceptance_title_fr_ca text,
    referree_invite_email_body_fr_ca text,
    referree_invite_email_subject_fr_ca text,
    referree_invite_sms_text_fr_ca text,
    referree_invite_subtitle_fr_ca text,
    referree_invite_title_fr_ca text,
    CONSTRAINT referral_programs_min_referree_order_subtotal_check CHECK ((min_referree_order_subtotal >= 0)),
    CONSTRAINT referral_programs_referree_amount_check CHECK ((referree_amount >= 0)),
    CONSTRAINT referral_programs_referrer_amount_check CHECK ((referrer_amount >= 0))
);


--
-- Name: referral_programs_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE referral_programs_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: referral_programs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE referral_programs_id_seq OWNED BY referral_programs.id;


--
-- Name: refresh_token; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE refresh_token (
    key character varying(40) NOT NULL,
    app character varying(255) NOT NULL,
    created timestamp with time zone NOT NULL,
    user_id integer NOT NULL
);


--
-- Name: region; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE region (
    id integer NOT NULL,
    name text NOT NULL,
    shortname text NOT NULL,
    description text NOT NULL,
    created_at timestamp with time zone NOT NULL,
    is_active boolean NOT NULL,
    country_id integer NOT NULL
);


--
-- Name: region_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE region_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: region_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE region_id_seq OWNED BY region.id;


--
-- Name: region_snapshot; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE region_snapshot (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    region character varying(20) NOT NULL,
    asap_time integer,
    kill_switch boolean NOT NULL,
    total_onshift_dashers integer,
    total_busy_dashers integer,
    total_outstanding_orders integer,
    total_picked_up_orders integer,
    ideal_flf double precision,
    date date NOT NULL,
    auto_sos_price integer,
    base_sos_price integer,
    eyeballing_count integer,
    realtime_demand_prediction jsonb,
    metadata text NOT NULL,
    district_id integer,
    starting_point_id integer
);


--
-- Name: region_snapshot_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE region_snapshot_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: region_snapshot_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE region_snapshot_id_seq OWNED BY region_snapshot.id;


--
-- Name: scheduled_caps_boost; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE scheduled_caps_boost (
    id integer NOT NULL,
    start_date date NOT NULL,
    end_date date NOT NULL,
    boost_factor double precision NOT NULL,
    window_indices text NOT NULL,
    starting_point_id integer NOT NULL
);


--
-- Name: scheduled_caps_boost_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE scheduled_caps_boost_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: scheduled_caps_boost_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE scheduled_caps_boost_id_seq OWNED BY scheduled_caps_boost.id;


--
-- Name: search_engine_store_feed; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE search_engine_store_feed (
    id integer NOT NULL,
    updated_at timestamp with time zone,
    search_engine text,
    store_id integer NOT NULL,
    starting_point_id integer NOT NULL,
    offer_schema text,
    restaurant_schema text
);


--
-- Name: search_engine_store_feed_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE search_engine_store_feed_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: search_engine_store_feed_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE search_engine_store_feed_id_seq OWNED BY search_engine_store_feed.id;


--
-- Name: seo_local_region; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE seo_local_region (
    id integer NOT NULL,
    name character varying(128) NOT NULL,
    slug character varying(128) NOT NULL,
    type character varying(128) NOT NULL,
    center geometry(Point,4326),
    is_active boolean NOT NULL,
    city_id integer NOT NULL
);


--
-- Name: seo_local_region_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE seo_local_region_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: seo_local_region_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE seo_local_region_id_seq OWNED BY seo_local_region.id;


--
-- Name: shortened_url; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE shortened_url (
    id integer NOT NULL,
    url_code text NOT NULL,
    expanded_url text NOT NULL,
    url_type text NOT NULL,
    pub_date timestamp with time zone NOT NULL,
    count integer NOT NULL
);


--
-- Name: shortened_url_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE shortened_url_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: shortened_url_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE shortened_url_id_seq OWNED BY shortened_url.id;


--
-- Name: sms_help_message_status; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE sms_help_message_status (
    id integer NOT NULL,
    phone_number character varying(128) NOT NULL,
    status text NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_at timestamp with time zone NOT NULL,
    user_id integer
);


--
-- Name: sms_help_message_status_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE sms_help_message_status_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: sms_help_message_status_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE sms_help_message_status_id_seq OWNED BY sms_help_message_status.id;


--
-- Name: sms_opt_out_number; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE sms_opt_out_number (
    id integer NOT NULL,
    phone_number character varying(128) NOT NULL,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: sms_opt_out_number_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE sms_opt_out_number_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: sms_opt_out_number_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE sms_opt_out_number_id_seq OWNED BY sms_opt_out_number.id;


--
-- Name: starship_delivery_info; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE starship_delivery_info (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    starship_delivery_id text NOT NULL,
    status text NOT NULL,
    tracking text,
    tracker text,
    drive_duration_to_loading integer,
    drive_duration_to_recipient integer,
    step text,
    cancelled_at timestamp with time zone,
    cancelled_reason text,
    delivery_id integer NOT NULL
);


--
-- Name: starship_delivery_info_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE starship_delivery_info_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: starship_delivery_info_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE starship_delivery_info_id_seq OWNED BY starship_delivery_info.id;


--
-- Name: starting_point; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE starting_point (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    dasher_instructions text NOT NULL,
    extra_asap_pad integer NOT NULL,
    consumer_order_open_pad integer NOT NULL,
    consumer_order_close_pad integer NOT NULL,
    name character varying(100) NOT NULL,
    shortname character varying(4) NOT NULL,
    orientation_address character varying(255),
    rate_per_delivery integer NOT NULL,
    hourly_minimum integer NOT NULL,
    double_pay boolean NOT NULL,
    manual_assign_buffer integer NOT NULL,
    assignment_latency_coefficients text NOT NULL,
    html_color character varying(7) NOT NULL,
    activation_time timestamp with time zone NOT NULL,
    deactivation_time timestamp with time zone,
    min_scheduling_slots_per_window integer NOT NULL,
    cap_smoothing_enabled boolean NOT NULL,
    cap_planning_adjuster text NOT NULL,
    ideal_flfs text,
    sos_price_flf_threshold double precision,
    market_id integer NOT NULL,
    submarket_id integer NOT NULL
);


--
-- Name: starting_point_assignment_latency_stats; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE starting_point_assignment_latency_stats (
    id integer NOT NULL,
    active_date date NOT NULL,
    assignment_latency_mean double precision,
    assignment_latency_std double precision,
    assignment_latency_median double precision,
    delivery_count integer,
    starting_point_id integer NOT NULL
);


--
-- Name: starting_point_assignment_latency_stats_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE starting_point_assignment_latency_stats_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: starting_point_assignment_latency_stats_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE starting_point_assignment_latency_stats_id_seq OWNED BY starting_point_assignment_latency_stats.id;


--
-- Name: starting_point_batching_parameters; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE starting_point_batching_parameters (
    id integer NOT NULL,
    forced_batches_pickup_distance_span_meters integer,
    forced_batches_pickup_time_span_seconds integer,
    forced_batches_dropoff_distance_span_meters integer,
    forced_batches_maximum_batch_size integer,
    starting_point_id integer
);


--
-- Name: starting_point_batching_parameters_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE starting_point_batching_parameters_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: starting_point_batching_parameters_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE starting_point_batching_parameters_id_seq OWNED BY starting_point_batching_parameters.id;


--
-- Name: starting_point_delivery_duration_stats; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE starting_point_delivery_duration_stats (
    id integer NOT NULL,
    active_date date NOT NULL,
    flf_by_window text,
    delivery_duration_mean_by_window text,
    delivery_duration_median_by_window text,
    delivery_duration_std_by_window text,
    delivery_count_by_window text,
    delivery_duration_mean_without_r2c_by_window text,
    starting_point_id integer NOT NULL
);


--
-- Name: starting_point_delivery_duration_stats_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE starting_point_delivery_duration_stats_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: starting_point_delivery_duration_stats_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE starting_point_delivery_duration_stats_id_seq OWNED BY starting_point_delivery_duration_stats.id;


--
-- Name: starting_point_delivery_hours; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE starting_point_delivery_hours (
    id integer NOT NULL,
    day_index integer NOT NULL,
    start_time time without time zone NOT NULL,
    end_time time without time zone NOT NULL,
    closed boolean NOT NULL,
    drive_open_offset integer NOT NULL,
    starting_point_id integer NOT NULL
);


--
-- Name: starting_point_delivery_hours_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE starting_point_delivery_hours_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: starting_point_delivery_hours_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE starting_point_delivery_hours_id_seq OWNED BY starting_point_delivery_hours.id;


--
-- Name: starting_point_flf_thresholds; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE starting_point_flf_thresholds (
    id integer NOT NULL,
    warning_threshold double precision,
    dangerous_threshold double precision,
    critical_threshold double precision,
    starting_point_id integer
);


--
-- Name: starting_point_flf_thresholds_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE starting_point_flf_thresholds_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: starting_point_flf_thresholds_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE starting_point_flf_thresholds_id_seq OWNED BY starting_point_flf_thresholds.id;


--
-- Name: starting_point_geometry; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE starting_point_geometry (
    starting_point_id integer NOT NULL,
    geom geometry(MultiPolygon,4326)
);


--
-- Name: starting_point_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE starting_point_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: starting_point_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE starting_point_id_seq OWNED BY starting_point.id;


--
-- Name: starting_point_r2c_stats; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE starting_point_r2c_stats (
    id integer NOT NULL,
    active_date date NOT NULL,
    r2c_mean double precision,
    r2c_std double precision,
    r2c_median double precision,
    estimated_r2c_mean double precision,
    estimated_r2c_std double precision,
    estimated_r2c_median double precision,
    delivery_count integer,
    starting_point_id integer NOT NULL
);


--
-- Name: starting_point_r2c_stats_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE starting_point_r2c_stats_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: starting_point_r2c_stats_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE starting_point_r2c_stats_id_seq OWNED BY starting_point_r2c_stats.id;


--
-- Name: starting_point_set; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE starting_point_set (
    id integer NOT NULL,
    updated_at timestamp with time zone,
    sp_set_id integer NOT NULL,
    market_id integer NOT NULL,
    starting_point_id integer NOT NULL
);


--
-- Name: starting_point_set_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE starting_point_set_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: starting_point_set_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE starting_point_set_id_seq OWNED BY starting_point_set.id;


--
-- Name: store_confirmed_time_snapshot; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE store_confirmed_time_snapshot (
    id integer NOT NULL,
    metadata text,
    active_date date NOT NULL,
    created_at timestamp with time zone NOT NULL,
    order_place_queue_length integer,
    busy_server_count integer,
    active_order_placer_last_hour_count integer
);


--
-- Name: store_confirmed_time_snapshot_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE store_confirmed_time_snapshot_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: store_confirmed_time_snapshot_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE store_confirmed_time_snapshot_id_seq OWNED BY store_confirmed_time_snapshot.id;


--
-- Name: store_consumer_review; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE store_consumer_review (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    rating integer NOT NULL,
    title text,
    body text,
    show_to_consumer boolean NOT NULL,
    processed_at timestamp with time zone,
    store_id integer NOT NULL,
    consumer_id integer NOT NULL
);


--
-- Name: store_consumer_review_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE store_consumer_review_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: store_consumer_review_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE store_consumer_review_id_seq OWNED BY store_consumer_review.id;


--
-- Name: store_consumer_review_tag; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE store_consumer_review_tag (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    name text NOT NULL,
    friendly_name text NOT NULL
);


--
-- Name: store_consumer_review_tag_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE store_consumer_review_tag_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: store_consumer_review_tag_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE store_consumer_review_tag_id_seq OWNED BY store_consumer_review_tag.id;


--
-- Name: store_consumer_review_tag_link; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE store_consumer_review_tag_link (
    id integer NOT NULL,
    review_id integer NOT NULL,
    tag_id integer NOT NULL
);


--
-- Name: store_consumer_review_tag_link_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE store_consumer_review_tag_link_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: store_consumer_review_tag_link_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE store_consumer_review_tag_link_id_seq OWNED BY store_consumer_review_tag_link.id;


--
-- Name: store_delivery_duration_stats; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE store_delivery_duration_stats (
    id integer NOT NULL,
    active_date date NOT NULL,
    delivery_duration_mean_by_window text,
    delivery_duration_median_by_window text,
    delivery_duration_std_by_window text,
    delivery_count_by_window text,
    delivery_duration_mean_without_r2c_by_window text,
    store_id integer NOT NULL
);


--
-- Name: store_delivery_duration_stats_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE store_delivery_duration_stats_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: store_delivery_duration_stats_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE store_delivery_duration_stats_id_seq OWNED BY store_delivery_duration_stats.id;


--
-- Name: store_mastercard_data; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE store_mastercard_data (
    id integer NOT NULL,
    mid text NOT NULL,
    mname text,
    updated_at timestamp with time zone NOT NULL,
    store_id integer NOT NULL
);


--
-- Name: store_mastercard_data_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE store_mastercard_data_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: store_mastercard_data_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE store_mastercard_data_id_seq OWNED BY store_mastercard_data.id;


--
-- Name: store_netsuite_customer_link; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE store_netsuite_customer_link (
    store_id integer NOT NULL,
    netsuite_entity_id text NOT NULL,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: store_order_cart; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE store_order_cart (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    submitted_at timestamp with time zone,
    cancelled_at timestamp with time zone,
    fulfilled_at timestamp with time zone,
    omnivore_id text,
    merchant_supplied_id text,
    currency text,
    subtotal integer NOT NULL,
    tax_amount integer NOT NULL,
    subtotal_tax_amount integer,
    fees_tax_amount integer,
    tax_rate numeric(6,3) NOT NULL,
    service_fee integer NOT NULL,
    service_rate numeric(6,3) NOT NULL,
    extra_sos_delivery_fee integer,
    base_delivery_fee integer,
    delivery_fee integer,
    discount_amount integer,
    commission integer NOT NULL,
    commission_rate numeric(6,3) NOT NULL,
    flat_commission integer NOT NULL,
    commission_tax integer,
    is_reduced_commission boolean NOT NULL,
    is_consumer_pickup boolean,
    legacy_inflation_amount integer NOT NULL,
    tip_amount integer NOT NULL,
    is_bike_friendly boolean NOT NULL,
    is_bike_friendly_updated_at timestamp with time zone,
    min_age_requirement integer NOT NULL,
    min_age_requirement_updated_at timestamp with time zone,
    bcs_store_order_cart_created boolean,
    contains_alcohol boolean,
    menu_id integer,
    order_cart_id integer NOT NULL,
    store_id integer,
    delivery_id integer
);


--
-- Name: store_order_cart_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE store_order_cart_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: store_order_cart_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE store_order_cart_id_seq OWNED BY store_order_cart.id;


--
-- Name: store_order_place_latency_stats; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE store_order_place_latency_stats (
    id integer NOT NULL,
    active_date date NOT NULL,
    order_place_latency_count integer,
    order_place_latency_sum integer,
    order_place_latency_stddev double precision,
    order_place_latency_count_lunch_peak integer,
    order_place_latency_sum_lunch_peak integer,
    order_place_latency_stddev_lunch_peak double precision,
    order_place_latency_count_dinner_peak integer,
    order_place_latency_sum_dinner_peak integer,
    order_place_latency_stddev_dinner_peak double precision,
    order_place_latency_count_large_order integer,
    order_place_latency_sum_large_order integer,
    order_place_latency_stddev_large_order double precision,
    store_id integer NOT NULL
);


--
-- Name: store_order_place_latency_stats_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE store_order_place_latency_stats_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: store_order_place_latency_stats_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE store_order_place_latency_stats_id_seq OWNED BY store_order_place_latency_stats.id;


--
-- Name: store_point_of_sale_transaction; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE store_point_of_sale_transaction (
    created_at timestamp with time zone NOT NULL,
    delivery_id integer NOT NULL,
    store_transaction_id text NOT NULL
);


--
-- Name: stripe_bank_account; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE stripe_bank_account (
    id integer NOT NULL,
    stripe_id text NOT NULL,
    account_holder_name text NOT NULL,
    fingerprint text NOT NULL,
    last4 text NOT NULL,
    bank_name text NOT NULL,
    status text NOT NULL,
    active boolean NOT NULL,
    removed_at timestamp with time zone,
    stripe_customer_id integer NOT NULL
);


--
-- Name: stripe_bank_account_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE stripe_bank_account_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: stripe_bank_account_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE stripe_bank_account_id_seq OWNED BY stripe_bank_account.id;


--
-- Name: stripe_card; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE stripe_card (
    id integer NOT NULL,
    stripe_id character varying(50) NOT NULL,
    fingerprint character varying(200) NOT NULL,
    last4 character varying(4) NOT NULL,
    dynamic_last4 character varying(4) NOT NULL,
    exp_month character varying(2) NOT NULL,
    exp_year character varying(4) NOT NULL,
    type character varying(30) NOT NULL,
    country_of_origin text,
    zip_code text,
    created_at timestamp with time zone,
    removed_at timestamp with time zone,
    is_scanned boolean,
    dd_fingerprint character varying(200),
    active boolean NOT NULL,
    consumer_id integer,
    stripe_customer_id integer,
    external_stripe_customer_id text,
    tokenization_method text,
    address_line1_check character varying(50),
    address_zip_check character varying(50),
    validation_card_id integer
);


--
-- Name: stripe_card_event; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE stripe_card_event (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    event_type text NOT NULL,
    status text,
    error_code text NOT NULL,
    consumer_id integer,
    stripe_customer_id integer
);


--
-- Name: stripe_card_event_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE stripe_card_event_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: stripe_card_event_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE stripe_card_event_id_seq OWNED BY stripe_card_event.id;


--
-- Name: stripe_card_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE stripe_card_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: stripe_card_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE stripe_card_id_seq OWNED BY stripe_card.id;


--
-- Name: stripe_charge; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE stripe_charge (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    refunded_at timestamp with time zone,
    stripe_id character varying(50) NOT NULL,
    amount integer,
    amount_refunded integer,
    currency text,
    status text,
    error_reason text,
    additional_payment_info text,
    description text,
    idempotency_key text,
    card_id integer,
    charge_id integer NOT NULL,
    updated_at timestamp with time zone
);


--
-- Name: stripe_charge_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE stripe_charge_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: stripe_charge_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE stripe_charge_id_seq OWNED BY stripe_charge.id;


--
-- Name: stripe_customer; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE stripe_customer (
    id integer NOT NULL,
    stripe_id text NOT NULL,
    country_shortname text NOT NULL,
    owner_type text NOT NULL,
    owner_id integer NOT NULL,
    default_card text,
    default_source text,
    CONSTRAINT stripe_customer_owner_id_check CHECK ((owner_id >= 0))
);


--
-- Name: stripe_customer_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE stripe_customer_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: stripe_customer_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE stripe_customer_id_seq OWNED BY stripe_customer.id;


--
-- Name: stripe_dispute; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE stripe_dispute (
    id integer NOT NULL,
    stripe_dispute_id text NOT NULL,
    disputed_at timestamp with time zone NOT NULL,
    amount integer NOT NULL,
    fee integer NOT NULL,
    net integer NOT NULL,
    currency text,
    charged_at timestamp with time zone NOT NULL,
    reason text NOT NULL,
    status text NOT NULL,
    evidence_due_by timestamp with time zone NOT NULL,
    evidence_submitted_at timestamp with time zone,
    updated_at timestamp with time zone,
    stripe_card_id integer NOT NULL,
    stripe_charge_id integer NOT NULL
);


--
-- Name: stripe_dispute_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE stripe_dispute_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: stripe_dispute_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE stripe_dispute_id_seq OWNED BY stripe_dispute.id;


--
-- Name: stripe_managed_account; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE stripe_managed_account (
    id integer NOT NULL,
    stripe_id text NOT NULL,
    country_shortname text NOT NULL,
    stripe_last_updated_at timestamp with time zone,
    bank_account_last_updated_at timestamp with time zone,
    fingerprint text,
    default_bank_last_four text,
    default_bank_name text,
    verification_disabled_reason text,
    verification_due_by timestamp with time zone,
    verification_fields_needed text
);


--
-- Name: stripe_managed_account_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE stripe_managed_account_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: stripe_managed_account_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE stripe_managed_account_id_seq OWNED BY stripe_managed_account.id;


--
-- Name: stripe_recipient; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE stripe_recipient (
    id integer NOT NULL,
    stripe_id text NOT NULL,
    country_shortname text NOT NULL
);


--
-- Name: stripe_recipient_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE stripe_recipient_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: stripe_recipient_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE stripe_recipient_id_seq OWNED BY stripe_recipient.id;


--
-- Name: stripe_transfer; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE stripe_transfer (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    stripe_id character varying(50),
    stripe_request_id text,
    stripe_status character varying(10) NOT NULL,
    stripe_failure_code character varying(50),
    stripe_account_id text,
    stripe_account_type text,
    country_shortname text,
    bank_last_four text,
    bank_name text,
    transfer_id integer NOT NULL,
    submission_error_code text,
    submission_error_type text,
    submission_status text,
    submitted_at timestamp with time zone
);


--
-- Name: stripe_transfer_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE stripe_transfer_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: stripe_transfer_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE stripe_transfer_id_seq OWNED BY stripe_transfer.id;


--
-- Name: submarket; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE submarket (
    id integer NOT NULL,
    seo_fields jsonb,
    name character varying(100) NOT NULL,
    flf_migration_threshold numeric(5,2) NOT NULL,
    bikers_can_automigrate boolean NOT NULL,
    daily_caps_publish_time time without time zone NOT NULL,
    min_order_fee integer,
    min_order_subtotal integer,
    drinking_age integer,
    is_at_dasher_capacity boolean,
    max_drive_delivery_radius_in_meters integer,
    max_dropoff_address_distance_change integer,
    slug character varying(50) NOT NULL,
    launch_date date,
    launch_image character varying(100),
    launch_mailchimp_waitlist_id character varying(15) NOT NULL,
    launch_iterable_waitlist_id integer,
    use_virtual_orientation boolean NOT NULL,
    is_on_homepage boolean NOT NULL,
    is_active boolean NOT NULL,
    show_on_dasher_apply_page boolean NOT NULL,
    home_background_image character varying(100),
    homepage_order integer,
    extra_asap_pad integer NOT NULL,
    dasher_pay_campaign_constraints text NOT NULL,
    rating_warn_threshold double precision,
    rating_deactivate_threshold double precision,
    adjusted_r2c_coefficient numeric(5,4) NOT NULL,
    adjusted_r2c_exponent numeric(5,4) NOT NULL,
    accepting_vehicle_types text NOT NULL,
    ideal_flfs text NOT NULL,
    sos_price_flf_threshold double precision,
    referrer_amount integer,
    referree_amount integer,
    min_referree_order_subtotal integer,
    referree_promotion_id integer,
    referral_program_experiment_id integer,
    market_id integer NOT NULL,
    referral_program_id integer,
    CONSTRAINT submarket_min_referree_order_subtotal_check CHECK ((min_referree_order_subtotal >= 0)),
    CONSTRAINT submarket_referree_amount_check CHECK ((referree_amount >= 0)),
    CONSTRAINT submarket_referrer_amount_check CHECK ((referrer_amount >= 0))
);


--
-- Name: submarket_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE submarket_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: submarket_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE submarket_id_seq OWNED BY submarket.id;


--
-- Name: subnational_division; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE subnational_division (
    id integer NOT NULL,
    name character varying(100) NOT NULL,
    shortname character varying(4) NOT NULL,
    country_id integer NOT NULL
);


--
-- Name: subnational_division_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE subnational_division_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: subnational_division_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE subnational_division_id_seq OWNED BY subnational_division.id;


--
-- Name: support_delivery_banner; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE support_delivery_banner (
    id integer NOT NULL,
    delivery_type character varying(50) NOT NULL,
    content text NOT NULL,
    created_at timestamp with time zone NOT NULL,
    expires_at timestamp with time zone
);


--
-- Name: support_delivery_banner_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE support_delivery_banner_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: support_delivery_banner_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE support_delivery_banner_id_seq OWNED BY support_delivery_banner.id;


--
-- Name: support_salesforce_case_record; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE support_salesforce_case_record (
    id integer NOT NULL,
    case_number text NOT NULL,
    case_uid text,
    customer_type character varying(20) NOT NULL,
    case_status character varying(20) NOT NULL,
    case_origin character varying(20) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    delivery_id integer NOT NULL
);


--
-- Name: support_salesforce_case_record_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE support_salesforce_case_record_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: support_salesforce_case_record_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE support_salesforce_case_record_id_seq OWNED BY support_salesforce_case_record.id;


--
-- Name: transfer; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE transfer (
    id integer NOT NULL,
    recipient_id integer,
    subtotal integer NOT NULL,
    adjustments text NOT NULL,
    amount integer NOT NULL,
    currency text,
    created_at timestamp with time zone NOT NULL,
    submitted_at timestamp with time zone,
    deleted_at timestamp with time zone,
    method character varying(15) NOT NULL,
    manual_transfer_reason text,
    status text,
    status_code text,
    submitting_at timestamp with time zone,
    should_retry_on_failure boolean,
    statement_description text,
    created_by_id integer,
    deleted_by_id integer,
    payment_account_id integer,
    recipient_ct_id integer,
    submitted_by_id integer,
    CONSTRAINT transfer_recipient_id_check CHECK ((recipient_id >= 0))
);


--
-- Name: transfer_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE transfer_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: transfer_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE transfer_id_seq OWNED BY transfer.id;


--
-- Name: transfer_submission_lock; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE transfer_submission_lock (
    transfer_id integer NOT NULL,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: twilio_masking_number; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE twilio_masking_number (
    id integer NOT NULL,
    twilio_number_id integer NOT NULL
);


--
-- Name: twilio_masking_number_assignment; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE twilio_masking_number_assignment (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    deactivated_at timestamp with time zone,
    consumer_id integer,
    dasher_id integer,
    store_id integer,
    delivery_id integer NOT NULL,
    twilio_masking_number_id integer
);


--
-- Name: twilio_masking_number_assignment_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE twilio_masking_number_assignment_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: twilio_masking_number_assignment_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE twilio_masking_number_assignment_id_seq OWNED BY twilio_masking_number_assignment.id;


--
-- Name: twilio_masking_number_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE twilio_masking_number_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: twilio_masking_number_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE twilio_masking_number_id_seq OWNED BY twilio_masking_number.id;


--
-- Name: twilio_number; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE twilio_number (
    id integer NOT NULL,
    phone_sid character varying(34) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    phone_number character varying(128) NOT NULL,
    name character varying(20) NOT NULL,
    blocked_at timestamp with time zone,
    is_active boolean NOT NULL,
    is_callable boolean NOT NULL,
    is_textable boolean NOT NULL,
    country_id integer NOT NULL
);


--
-- Name: twilio_number_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE twilio_number_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: twilio_number_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE twilio_number_id_seq OWNED BY twilio_number.id;


--
-- Name: user; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE "user" (
    id integer NOT NULL,
    password character varying(128) NOT NULL,
    last_login timestamp with time zone,
    is_superuser boolean NOT NULL,
    email character varying(255) NOT NULL,
    is_staff boolean NOT NULL,
    is_active boolean NOT NULL,
    is_guest boolean NOT NULL,
    date_joined timestamp with time zone NOT NULL,
    week_joined timestamp with time zone NOT NULL,
    phone_number character varying(30) NOT NULL,
    first_name character varying(255) NOT NULL,
    last_name character varying(255) NOT NULL,
    auth_version integer,
    block_reason text,
    experiment_id uuid,
    bucket_key_override text,
    is_blacklisted boolean NOT NULL,
    is_whitelisted boolean,
    password_change_required boolean,
    password_changed_at timestamp with time zone,
    is_password_secure boolean,
    password_checked_at timestamp with time zone,
    identity_service_key bigint,
    dasher_id integer,
    guest_user_type_id integer,
    outgoing_number_id integer
);


--
-- Name: user_activation_change_event; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE user_activation_change_event (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    reason text,
    reason_type text,
    type text NOT NULL,
    changed_by_id integer NOT NULL,
    user_id integer NOT NULL
);


--
-- Name: user_activation_change_event_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE user_activation_change_event_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: user_activation_change_event_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE user_activation_change_event_id_seq OWNED BY user_activation_change_event.id;


--
-- Name: user_deactivation_source; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE user_deactivation_source (
    id integer NOT NULL,
    source_type text NOT NULL,
    description text NOT NULL,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: user_deactivation_source_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE user_deactivation_source_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: user_deactivation_source_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE user_deactivation_source_id_seq OWNED BY user_deactivation_source.id;


--
-- Name: user_device_fingerprint_link; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE user_device_fingerprint_link (
    id integer NOT NULL,
    source text,
    fingerprint_id integer NOT NULL,
    user_id integer NOT NULL
);


--
-- Name: user_device_fingerprint_link_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE user_device_fingerprint_link_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: user_device_fingerprint_link_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE user_device_fingerprint_link_id_seq OWNED BY user_device_fingerprint_link.id;


--
-- Name: user_group_admin ; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE "user_group_admin " (
    id integer NOT NULL,
    role text NOT NULL,
    group_id integer NOT NULL,
    user_id integer NOT NULL
);


--
-- Name: user_group_admin _id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE "user_group_admin _id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: user_group_admin _id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE "user_group_admin _id_seq" OWNED BY "user_group_admin ".id;


--
-- Name: user_groups; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE user_groups (
    id integer NOT NULL,
    user_id integer NOT NULL,
    group_id integer NOT NULL
);


--
-- Name: user_groups_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE user_groups_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: user_groups_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE user_groups_id_seq OWNED BY user_groups.id;


--
-- Name: user_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE user_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: user_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE user_id_seq OWNED BY "user".id;


--
-- Name: user_locale_preference; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE user_locale_preference (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    language text,
    user_id integer NOT NULL
);


--
-- Name: user_locale_preference_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE user_locale_preference_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: user_locale_preference_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE user_locale_preference_id_seq OWNED BY user_locale_preference.id;


--
-- Name: user_social_data; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE user_social_data (
    id integer NOT NULL,
    provider text NOT NULL,
    uid text NOT NULL,
    extra_data text NOT NULL,
    created_at timestamp with time zone,
    user_id integer NOT NULL
);


--
-- Name: user_social_data_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE user_social_data_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: user_social_data_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE user_social_data_id_seq OWNED BY user_social_data.id;


--
-- Name: user_user_permissions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE user_user_permissions (
    id integer NOT NULL,
    user_id integer NOT NULL,
    permission_id integer NOT NULL
);


--
-- Name: user_user_permissions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE user_user_permissions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: user_user_permissions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE user_user_permissions_id_seq OWNED BY user_user_permissions.id;


--
-- Name: value_delivery_fee_promotion; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE value_delivery_fee_promotion (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    value integer NOT NULL,
    delivery_fee integer NOT NULL,
    min_subtotal integer NOT NULL,
    CONSTRAINT value_delivery_fee_promotion_delivery_fee_check CHECK ((delivery_fee >= 0)),
    CONSTRAINT value_delivery_fee_promotion_min_subtotal_check CHECK ((min_subtotal >= 0)),
    CONSTRAINT value_delivery_fee_promotion_value_check CHECK ((value >= 0))
);


--
-- Name: value_delivery_fee_promotion_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE value_delivery_fee_promotion_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: value_delivery_fee_promotion_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE value_delivery_fee_promotion_id_seq OWNED BY value_delivery_fee_promotion.id;


--
-- Name: value_promotion; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE value_promotion (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    value integer NOT NULL,
    min_subtotal integer NOT NULL,
    CONSTRAINT value_promotion_min_subtotal_check CHECK ((min_subtotal >= 0)),
    CONSTRAINT value_promotion_value_check CHECK ((value >= 0))
);


--
-- Name: value_promotion_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE value_promotion_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: value_promotion_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE value_promotion_id_seq OWNED BY value_promotion.id;


--
-- Name: vanity_url; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE vanity_url (
    id integer NOT NULL,
    url character varying(50) NOT NULL,
    target character varying(50) NOT NULL,
    utm_source character varying(50) NOT NULL,
    utm_campaign character varying(50) NOT NULL,
    notes text NOT NULL,
    is_active boolean NOT NULL,
    created_at timestamp with time zone NOT NULL,
    utm_term_id integer NOT NULL
);


--
-- Name: vanity_url_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE vanity_url_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: vanity_url_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE vanity_url_id_seq OWNED BY vanity_url.id;


--
-- Name: vehicle_reservation; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE vehicle_reservation (
    id integer NOT NULL,
    dasher_id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    expires_at timestamp with time zone,
    security_deposit integer,
    deposit_paid_at timestamp with time zone,
    deposit_refunded_at timestamp with time zone,
    rental_id integer,
    country_id integer NOT NULL,
    charge_id integer
);


--
-- Name: vehicle_reservation_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE vehicle_reservation_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: vehicle_reservation_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE vehicle_reservation_id_seq OWNED BY vehicle_reservation.id;


--
-- Name: verification_attempt; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE verification_attempt (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    verification_type text NOT NULL,
    verification_code text,
    code_expiration timestamp with time zone,
    verification_attempt_count integer,
    consumer_verification_status_id integer NOT NULL,
    CONSTRAINT verification_attempt_verification_attempt_count_check CHECK ((verification_attempt_count >= 0))
);


--
-- Name: verification_attempt_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE verification_attempt_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: verification_attempt_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE verification_attempt_id_seq OWNED BY verification_attempt.id;


--
-- Name: version_client; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE version_client (
    id integer NOT NULL,
    name character varying(100) NOT NULL,
    min_version character varying(50) NOT NULL,
    current_version character varying(50) NOT NULL
);


--
-- Name: version_client_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE version_client_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: version_client_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE version_client_id_seq OWNED BY version_client.id;


--
-- Name: weather_forecast_model; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE weather_forecast_model (
    id integer NOT NULL,
    "current_date" date NOT NULL,
    forecast_date date NOT NULL,
    precip_probability text NOT NULL,
    precip_intensity text NOT NULL,
    weather_summary text NOT NULL,
    weather_json text NOT NULL,
    starting_point_id integer NOT NULL
);


--
-- Name: weather_forecast_model_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE weather_forecast_model_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: weather_forecast_model_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE weather_forecast_model_id_seq OWNED BY weather_forecast_model.id;


--
-- Name: weather_historical_model; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE weather_historical_model (
    id integer NOT NULL,
    past_date date NOT NULL,
    precip_intensity text NOT NULL,
    weather_summary text NOT NULL,
    weather_json text NOT NULL,
    starting_point_id integer NOT NULL
);


--
-- Name: weather_historical_model_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE weather_historical_model_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: weather_historical_model_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE weather_historical_model_id_seq OWNED BY weather_historical_model.id;


--
-- Name: web_deployment; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE web_deployment (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    env text NOT NULL,
    frontend_release_id text NOT NULL,
    backend_release_id text NOT NULL
);


--
-- Name: web_deployment_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE web_deployment_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: web_deployment_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE web_deployment_id_seq OWNED BY web_deployment.id;


--
-- Name: zendesk_template; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE zendesk_template (
    id integer NOT NULL,
    requester_name character varying(100) NOT NULL,
    requester_email character varying(100) NOT NULL,
    issue_symptom_field_id character varying(200) NOT NULL,
    subject_template character varying(200) NOT NULL,
    desc_template text NOT NULL,
    category_id integer NOT NULL
);


--
-- Name: zendesk_template_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE zendesk_template_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: zendesk_template_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE zendesk_template_id_seq OWNED BY zendesk_template.id;


--
-- Name: address id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY address ALTER COLUMN id SET DEFAULT nextval('address_id_seq'::regclass);


--
-- Name: address_place_tag_link id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY address_place_tag_link ALTER COLUMN id SET DEFAULT nextval('address_place_tag_link_id_seq'::regclass);


--
-- Name: analytics_businessconstants id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY analytics_businessconstants ALTER COLUMN id SET DEFAULT nextval('analytics_businessconstants_id_seq'::regclass);


--
-- Name: analytics_dailybusinessmetrics id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY analytics_dailybusinessmetrics ALTER COLUMN id SET DEFAULT nextval('analytics_dailybusinessmetrics_id_seq'::regclass);


--
-- Name: analytics_siteoutage id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY analytics_siteoutage ALTER COLUMN id SET DEFAULT nextval('analytics_siteoutage_id_seq'::regclass);


--
-- Name: app_deploy_app id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY app_deploy_app ALTER COLUMN id SET DEFAULT nextval('app_deploy_app_id_seq'::regclass);


--
-- Name: apple_notification_app id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY apple_notification_app ALTER COLUMN id SET DEFAULT nextval('apple_notification_app_id_seq'::regclass);


--
-- Name: attribution_data id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY attribution_data ALTER COLUMN id SET DEFAULT nextval('attribution_data_id_seq'::regclass);


--
-- Name: auth_group id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY auth_group ALTER COLUMN id SET DEFAULT nextval('auth_group_id_seq'::regclass);


--
-- Name: auth_group_permissions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY auth_group_permissions ALTER COLUMN id SET DEFAULT nextval('auth_group_permissions_id_seq'::regclass);


--
-- Name: auth_permission id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY auth_permission ALTER COLUMN id SET DEFAULT nextval('auth_permission_id_seq'::regclass);


--
-- Name: banned_ip_address id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY banned_ip_address ALTER COLUMN id SET DEFAULT nextval('banned_ip_address_id_seq'::regclass);


--
-- Name: base_price_sos_event id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY base_price_sos_event ALTER COLUMN id SET DEFAULT nextval('base_price_sos_event_id_seq'::regclass);


--
-- Name: blacklisted_consumer_address id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY blacklisted_consumer_address ALTER COLUMN id SET DEFAULT nextval('blacklisted_consumer_address_id_seq'::regclass);


--
-- Name: capacity_planning_evaluation id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY capacity_planning_evaluation ALTER COLUMN id SET DEFAULT nextval('capacity_planning_evaluation_id_seq'::regclass);


--
-- Name: card_acceptor id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY card_acceptor ALTER COLUMN id SET DEFAULT nextval('card_acceptor_id_seq'::regclass);


--
-- Name: card_acceptor_store_association id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY card_acceptor_store_association ALTER COLUMN id SET DEFAULT nextval('card_acceptor_store_association_id_seq'::regclass);


--
-- Name: cash_payment id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY cash_payment ALTER COLUMN id SET DEFAULT nextval('cash_payment_id_seq'::regclass);


--
-- Name: city id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY city ALTER COLUMN id SET DEFAULT nextval('city_id_seq'::regclass);


--
-- Name: communication_preferences_channel_link id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY communication_preferences_channel_link ALTER COLUMN id SET DEFAULT nextval('communication_preferences_channel_link_id_seq'::regclass);


--
-- Name: compensation_request id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY compensation_request ALTER COLUMN id SET DEFAULT nextval('compensation_request_id_seq'::regclass);


--
-- Name: consumer id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer ALTER COLUMN id SET DEFAULT nextval('consumer_id_seq'::regclass);


--
-- Name: consumer_account_credits id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_account_credits ALTER COLUMN id SET DEFAULT nextval('consumer_account_credits_id_seq'::regclass);


--
-- Name: consumer_account_credits_transaction id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_account_credits_transaction ALTER COLUMN id SET DEFAULT nextval('consumer_account_credits_transaction_id_seq'::regclass);


--
-- Name: consumer_address_link id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_address_link ALTER COLUMN id SET DEFAULT nextval('consumer_address_link_id_seq'::regclass);


--
-- Name: consumer_announcement id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_announcement ALTER COLUMN id SET DEFAULT nextval('consumer_announcement_id_seq'::regclass);


--
-- Name: consumer_announcement_district_link id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_announcement_district_link ALTER COLUMN id SET DEFAULT nextval('consumer_announcement_district_link_id_seq'::regclass);


--
-- Name: consumer_announcement_submarkets id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_announcement_submarkets ALTER COLUMN id SET DEFAULT nextval('consumer_announcement_submarkets_id_seq'::regclass);


--
-- Name: consumer_channel id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_channel ALTER COLUMN id SET DEFAULT nextval('consumer_channel_id_seq'::regclass);


--
-- Name: consumer_channel_submarkets id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_channel_submarkets ALTER COLUMN id SET DEFAULT nextval('consumer_channel_submarkets_id_seq'::regclass);


--
-- Name: consumer_charge id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_charge ALTER COLUMN id SET DEFAULT nextval('consumer_charge_id_seq'::regclass);


--
-- Name: consumer_communication_channel id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_communication_channel ALTER COLUMN id SET DEFAULT nextval('consumer_communication_channel_id_seq'::regclass);


--
-- Name: consumer_delivery_rating id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_delivery_rating ALTER COLUMN id SET DEFAULT nextval('consumer_delivery_rating_id_seq'::regclass);


--
-- Name: consumer_delivery_rating_category id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_delivery_rating_category ALTER COLUMN id SET DEFAULT nextval('consumer_delivery_rating_category_id_seq'::regclass);


--
-- Name: consumer_delivery_rating_category_link id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_delivery_rating_category_link ALTER COLUMN id SET DEFAULT nextval('consumer_delivery_rating_category_link_id_seq'::regclass);


--
-- Name: consumer_discount id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_discount ALTER COLUMN id SET DEFAULT nextval('consumer_discount_id_seq'::regclass);


--
-- Name: consumer_donation id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_donation ALTER COLUMN id SET DEFAULT nextval('consumer_donation_id_seq'::regclass);


--
-- Name: consumer_donation_recipient_link id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_donation_recipient_link ALTER COLUMN id SET DEFAULT nextval('consumer_donation_recipient_link_id_seq'::regclass);


--
-- Name: consumer_empty_store_list_request id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_empty_store_list_request ALTER COLUMN id SET DEFAULT nextval('consumer_empty_store_list_request_id_seq'::regclass);


--
-- Name: consumer_faq id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_faq ALTER COLUMN id SET DEFAULT nextval('consumer_faq_id_seq'::regclass);


--
-- Name: consumer_favorites id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_favorites ALTER COLUMN id SET DEFAULT nextval('consumer_favorites_id_seq'::regclass);


--
-- Name: consumer_fraud_info id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_fraud_info ALTER COLUMN id SET DEFAULT nextval('consumer_fraud_info_id_seq'::regclass);


--
-- Name: consumer_ios_devices id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_ios_devices ALTER COLUMN id SET DEFAULT nextval('consumer_ios_devices_id_seq'::regclass);


--
-- Name: consumer_preferences id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_preferences ALTER COLUMN id SET DEFAULT nextval('consumer_preferences_id_seq'::regclass);


--
-- Name: consumer_preferences_category_link id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_preferences_category_link ALTER COLUMN id SET DEFAULT nextval('consumer_preferences_category_link_id_seq'::regclass);


--
-- Name: consumer_profile_edit_history id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_profile_edit_history ALTER COLUMN id SET DEFAULT nextval('consumer_profile_edit_history_id_seq'::regclass);


--
-- Name: consumer_promotion id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_promotion ALTER COLUMN id SET DEFAULT nextval('consumer_promotion_id_seq'::regclass);


--
-- Name: consumer_promotion_campaign id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_promotion_campaign ALTER COLUMN id SET DEFAULT nextval('consumer_promotion_campaign_id_seq'::regclass);


--
-- Name: consumer_push_notification id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_push_notification ALTER COLUMN id SET DEFAULT nextval('consumer_push_notification_id_seq'::regclass);


--
-- Name: consumer_referral_link id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_referral_link ALTER COLUMN id SET DEFAULT nextval('consumer_referral_link_id_seq'::regclass);


--
-- Name: consumer_share id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_share ALTER COLUMN id SET DEFAULT nextval('consumer_share_id_seq'::regclass);


--
-- Name: consumer_store_request id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_store_request ALTER COLUMN id SET DEFAULT nextval('consumer_store_request_id_seq'::regclass);


--
-- Name: consumer_stripe_customer_link id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_stripe_customer_link ALTER COLUMN id SET DEFAULT nextval('consumer_stripe_customer_link_id_seq'::regclass);


--
-- Name: consumer_subscription id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_subscription ALTER COLUMN id SET DEFAULT nextval('consumer_subscription_id_seq'::regclass);


--
-- Name: consumer_subscription_plan id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_subscription_plan ALTER COLUMN id SET DEFAULT nextval('consumer_subscription_plan_id_seq'::regclass);


--
-- Name: consumer_subscription_plan_featured_location_link id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_subscription_plan_featured_location_link ALTER COLUMN id SET DEFAULT nextval('consumer_subscription_plan_featured_location_link_id_seq'::regclass);


--
-- Name: consumer_subscription_plan_promotion_info id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_subscription_plan_promotion_info ALTER COLUMN id SET DEFAULT nextval('consumer_subscription_plan_promotion_info_id_seq'::regclass);


--
-- Name: consumer_subscription_plan_promotion_infos id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_subscription_plan_promotion_infos ALTER COLUMN id SET DEFAULT nextval('consumer_subscription_plan_promotion_infos_id_seq'::regclass);


--
-- Name: consumer_subscription_plan_submarket_link id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_subscription_plan_submarket_link ALTER COLUMN id SET DEFAULT nextval('consumer_subscription_plan_submarket_link_id_seq'::regclass);


--
-- Name: consumer_subscription_plan_trial id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_subscription_plan_trial ALTER COLUMN id SET DEFAULT nextval('consumer_subscription_plan_trial_id_seq'::regclass);


--
-- Name: consumer_subscription_plan_trial_featured_location_link id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_subscription_plan_trial_featured_location_link ALTER COLUMN id SET DEFAULT nextval('consumer_subscription_plan_trial_featured_location_link_id_seq'::regclass);


--
-- Name: consumer_subscription_plan_trial_promotion_infos id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_subscription_plan_trial_promotion_infos ALTER COLUMN id SET DEFAULT nextval('consumer_subscription_plan_trial_promotion_infos_id_seq'::regclass);


--
-- Name: consumer_subscription_plan_trial_submarket_link id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_subscription_plan_trial_submarket_link ALTER COLUMN id SET DEFAULT nextval('consumer_subscription_plan_trial_submarket_link_id_seq'::regclass);


--
-- Name: consumer_subscription_unit id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_subscription_unit ALTER COLUMN id SET DEFAULT nextval('consumer_subscription_unit_id_seq'::regclass);


--
-- Name: consumer_survey id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_survey ALTER COLUMN id SET DEFAULT nextval('consumer_survey_id_seq'::regclass);


--
-- Name: consumer_survey_answer_option id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_survey_answer_option ALTER COLUMN id SET DEFAULT nextval('consumer_survey_answer_option_id_seq'::regclass);


--
-- Name: consumer_survey_question id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_survey_question ALTER COLUMN id SET DEFAULT nextval('consumer_survey_question_id_seq'::regclass);


--
-- Name: consumer_survey_question_response id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_survey_question_response ALTER COLUMN id SET DEFAULT nextval('consumer_survey_question_response_id_seq'::regclass);


--
-- Name: consumer_survey_response id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_survey_response ALTER COLUMN id SET DEFAULT nextval('consumer_survey_response_id_seq'::regclass);


--
-- Name: consumer_terms_of_service id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_terms_of_service ALTER COLUMN id SET DEFAULT nextval('consumer_terms_of_service_id_seq'::regclass);


--
-- Name: consumer_tos_link id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_tos_link ALTER COLUMN id SET DEFAULT nextval('consumer_tos_link_id_seq'::regclass);


--
-- Name: consumer_variable_pay id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_variable_pay ALTER COLUMN id SET DEFAULT nextval('consumer_variable_pay_id_seq'::regclass);


--
-- Name: core_image id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY core_image ALTER COLUMN id SET DEFAULT nextval('core_image_id_seq'::regclass);


--
-- Name: core_modelannotation id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY core_modelannotation ALTER COLUMN id SET DEFAULT nextval('core_modelannotation_id_seq'::regclass);


--
-- Name: country id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY country ALTER COLUMN id SET DEFAULT nextval('country_id_seq'::regclass);


--
-- Name: credit_refund_delivery_error id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY credit_refund_delivery_error ALTER COLUMN id SET DEFAULT nextval('credit_refund_delivery_error_id_seq'::regclass);


--
-- Name: credit_refund_error id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY credit_refund_error ALTER COLUMN id SET DEFAULT nextval('credit_refund_error_id_seq'::regclass);


--
-- Name: credit_refund_order_item_error id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY credit_refund_order_item_error ALTER COLUMN id SET DEFAULT nextval('credit_refund_order_item_error_id_seq'::regclass);


--
-- Name: curated_category id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY curated_category ALTER COLUMN id SET DEFAULT nextval('curated_category_id_seq'::regclass);


--
-- Name: curated_category_membership id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY curated_category_membership ALTER COLUMN id SET DEFAULT nextval('curated_category_membership_id_seq'::regclass);


--
-- Name: currency_exchange_rate id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY currency_exchange_rate ALTER COLUMN id SET DEFAULT nextval('currency_exchange_rate_id_seq'::regclass);


--
-- Name: dasher_capacity_model id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY dasher_capacity_model ALTER COLUMN id SET DEFAULT nextval('dasher_capacity_model_id_seq'::regclass);


--
-- Name: dasher_capacity_plan id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY dasher_capacity_plan ALTER COLUMN id SET DEFAULT nextval('dasher_capacity_plan_id_seq'::regclass);


--
-- Name: dasher_onboarding id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY dasher_onboarding ALTER COLUMN id SET DEFAULT nextval('dasher_onboarding_id_seq'::regclass);


--
-- Name: dasher_onboarding_type id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY dasher_onboarding_type ALTER COLUMN id SET DEFAULT nextval('dasher_onboarding_type_id_seq'::regclass);


--
-- Name: dd4b_expense_code id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY dd4b_expense_code ALTER COLUMN id SET DEFAULT nextval('dd4b_expense_code_id_seq'::regclass);


--
-- Name: delivery id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery ALTER COLUMN id SET DEFAULT nextval('delivery_id_seq'::regclass);


--
-- Name: delivery_assignment_constraint id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_assignment_constraint ALTER COLUMN id SET DEFAULT nextval('delivery_assignment_constraint_id_seq'::regclass);


--
-- Name: delivery_batch id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_batch ALTER COLUMN id SET DEFAULT nextval('delivery_batch_id_seq'::regclass);


--
-- Name: delivery_batch_membership id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_batch_membership ALTER COLUMN id SET DEFAULT nextval('delivery_batch_membership_id_seq'::regclass);


--
-- Name: delivery_cancellation_reason id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_cancellation_reason ALTER COLUMN id SET DEFAULT nextval('delivery_cancellation_reason_id_seq'::regclass);


--
-- Name: delivery_cancellation_reason_category id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_cancellation_reason_category ALTER COLUMN id SET DEFAULT nextval('delivery_cancellation_reason_category_id_seq'::regclass);


--
-- Name: delivery_catering_verification id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_catering_verification ALTER COLUMN id SET DEFAULT nextval('delivery_catering_verification_id_seq'::regclass);


--
-- Name: delivery_error_source id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_error_source ALTER COLUMN id SET DEFAULT nextval('delivery_error_source_id_seq'::regclass);


--
-- Name: delivery_event id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_event ALTER COLUMN id SET DEFAULT nextval('delivery_event_id_seq'::regclass);


--
-- Name: delivery_event_category id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_event_category ALTER COLUMN id SET DEFAULT nextval('delivery_event_category_id_seq'::regclass);


--
-- Name: delivery_fee_promotion id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_fee_promotion ALTER COLUMN id SET DEFAULT nextval('delivery_fee_promotion_id_seq'::regclass);


--
-- Name: delivery_funding id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_funding ALTER COLUMN id SET DEFAULT nextval('delivery_funding_id_seq'::regclass);


--
-- Name: delivery_gift id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_gift ALTER COLUMN id SET DEFAULT nextval('delivery_gift_id_seq'::regclass);


--
-- Name: delivery_growth_model id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_growth_model ALTER COLUMN id SET DEFAULT nextval('delivery_growth_model_id_seq'::regclass);


--
-- Name: delivery_growth_prediction id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_growth_prediction ALTER COLUMN id SET DEFAULT nextval('delivery_growth_prediction_id_seq'::regclass);


--
-- Name: delivery_issue id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_issue ALTER COLUMN id SET DEFAULT nextval('delivery_issue_id_seq'::regclass);


--
-- Name: delivery_item id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_item ALTER COLUMN id SET DEFAULT nextval('delivery_item_id_seq'::regclass);


--
-- Name: delivery_masking_number_assignment id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_masking_number_assignment ALTER COLUMN id SET DEFAULT nextval('delivery_masking_number_assignment_id_seq'::regclass);


--
-- Name: delivery_rating id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_rating ALTER COLUMN id SET DEFAULT nextval('delivery_rating_id_seq'::regclass);


--
-- Name: delivery_rating_category id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_rating_category ALTER COLUMN id SET DEFAULT nextval('delivery_rating_category_id_seq'::regclass);


--
-- Name: delivery_rating_category_link id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_rating_category_link ALTER COLUMN id SET DEFAULT nextval('delivery_rating_category_link_id_seq'::regclass);


--
-- Name: delivery_receipt id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_receipt ALTER COLUMN id SET DEFAULT nextval('delivery_receipt_id_seq'::regclass);


--
-- Name: delivery_recipient id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_recipient ALTER COLUMN id SET DEFAULT nextval('delivery_recipient_id_seq'::regclass);


--
-- Name: delivery_request id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_request ALTER COLUMN id SET DEFAULT nextval('delivery_request_id_seq'::regclass);


--
-- Name: delivery_request_submission_monitor id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_request_submission_monitor ALTER COLUMN id SET DEFAULT nextval('delivery_request_submission_monitor_id_seq'::regclass);


--
-- Name: delivery_set id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_set ALTER COLUMN id SET DEFAULT nextval('delivery_set_id_seq'::regclass);


--
-- Name: delivery_set_mapping id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_set_mapping ALTER COLUMN id SET DEFAULT nextval('delivery_set_mapping_id_seq'::regclass);


--
-- Name: depot id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY depot ALTER COLUMN id SET DEFAULT nextval('depot_id_seq'::regclass);


--
-- Name: device_fingerprint id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY device_fingerprint ALTER COLUMN id SET DEFAULT nextval('device_fingerprint_id_seq'::regclass);


--
-- Name: dispatch_error id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY dispatch_error ALTER COLUMN id SET DEFAULT nextval('dispatch_error_id_seq'::regclass);


--
-- Name: district id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY district ALTER COLUMN id SET DEFAULT nextval('district_id_seq'::regclass);


--
-- Name: district_starting_point_availability_override id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY district_starting_point_availability_override ALTER COLUMN id SET DEFAULT nextval('district_starting_point_availability_override_id_seq'::regclass);


--
-- Name: django_admin_log id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY django_admin_log ALTER COLUMN id SET DEFAULT nextval('django_admin_log_id_seq'::regclass);


--
-- Name: django_content_type id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY django_content_type ALTER COLUMN id SET DEFAULT nextval('django_content_type_id_seq'::regclass);


--
-- Name: django_migrations id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY django_migrations ALTER COLUMN id SET DEFAULT nextval('django_migrations_id_seq'::regclass);


--
-- Name: django_twilio_caller id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY django_twilio_caller ALTER COLUMN id SET DEFAULT nextval('django_twilio_caller_id_seq'::regclass);


--
-- Name: django_twilio_credential id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY django_twilio_credential ALTER COLUMN id SET DEFAULT nextval('django_twilio_credential_id_seq'::regclass);


--
-- Name: donation_recipient id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY donation_recipient ALTER COLUMN id SET DEFAULT nextval('donation_recipient_id_seq'::regclass);


--
-- Name: doordash_blacklistedemail id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY doordash_blacklistedemail ALTER COLUMN id SET DEFAULT nextval('doordash_blacklistedemail_id_seq'::regclass);


--
-- Name: doordash_blacklistedpaymentcard id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY doordash_blacklistedpaymentcard ALTER COLUMN id SET DEFAULT nextval('doordash_blacklistedpaymentcard_id_seq'::regclass);


--
-- Name: doordash_blacklistedphonenumber id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY doordash_blacklistedphonenumber ALTER COLUMN id SET DEFAULT nextval('doordash_blacklistedphonenumber_id_seq'::regclass);


--
-- Name: doordash_blacklisteduser id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY doordash_blacklisteduser ALTER COLUMN id SET DEFAULT nextval('doordash_blacklisteduser_id_seq'::regclass);


--
-- Name: doordash_employmentperiod id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY doordash_employmentperiod ALTER COLUMN id SET DEFAULT nextval('doordash_employmentperiod_id_seq'::regclass);


--
-- Name: doordash_orderitemsubstitutionevent id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY doordash_orderitemsubstitutionevent ALTER COLUMN id SET DEFAULT nextval('doordash_orderitemsubstitutionevent_id_seq'::regclass);


--
-- Name: drive_business_mapping id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY drive_business_mapping ALTER COLUMN id SET DEFAULT nextval('drive_business_mapping_id_seq'::regclass);


--
-- Name: drive_effort_based_pay_vars id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY drive_effort_based_pay_vars ALTER COLUMN id SET DEFAULT nextval('drive_effort_based_pay_vars_id_seq'::regclass);


--
-- Name: drive_order id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY drive_order ALTER COLUMN id SET DEFAULT nextval('drive_order_id_seq'::regclass);


--
-- Name: drive_store_catering_setup_instruction id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY drive_store_catering_setup_instruction ALTER COLUMN id SET DEFAULT nextval('drive_store_catering_setup_instruction_id_seq'::regclass);


--
-- Name: drive_webhook_event id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY drive_webhook_event ALTER COLUMN id SET DEFAULT nextval('drive_webhook_event_id_seq'::regclass);


--
-- Name: drive_webhook_subscription id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY drive_webhook_subscription ALTER COLUMN id SET DEFAULT nextval('drive_webhook_subscription_id_seq'::regclass);


--
-- Name: email_holdout_group id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY email_holdout_group ALTER COLUMN id SET DEFAULT nextval('email_holdout_group_id_seq'::regclass);


--
-- Name: email_notification id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY email_notification ALTER COLUMN id SET DEFAULT nextval('email_notification_id_seq'::regclass);


--
-- Name: email_preference id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY email_preference ALTER COLUMN id SET DEFAULT nextval('email_preference_id_seq'::regclass);


--
-- Name: email_verification_request id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY email_verification_request ALTER COLUMN id SET DEFAULT nextval('email_verification_request_id_seq'::regclass);


--
-- Name: employee_monthly_culture_shift id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY employee_monthly_culture_shift ALTER COLUMN id SET DEFAULT nextval('employee_monthly_culture_shift_id_seq'::regclass);


--
-- Name: estimate id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY estimate ALTER COLUMN id SET DEFAULT nextval('estimate_id_seq'::regclass);


--
-- Name: eta_prediction id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY eta_prediction ALTER COLUMN id SET DEFAULT nextval('eta_prediction_id_seq'::regclass);


--
-- Name: experiment2 id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY experiment2 ALTER COLUMN id SET DEFAULT nextval('experiment2_id_seq'::regclass);


--
-- Name: experiment_bucket_assignment id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY experiment_bucket_assignment ALTER COLUMN id SET DEFAULT nextval('experiment_bucket_assignment_id_seq'::regclass);


--
-- Name: experiment_distribution id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY experiment_distribution ALTER COLUMN id SET DEFAULT nextval('experiment_distribution_id_seq'::regclass);


--
-- Name: experiment_override id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY experiment_override ALTER COLUMN id SET DEFAULT nextval('experiment_override_id_seq'::regclass);


--
-- Name: experiment_user id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY experiment_user ALTER COLUMN id SET DEFAULT nextval('experiment_user_id_seq'::regclass);


--
-- Name: experiment_version id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY experiment_version ALTER COLUMN id SET DEFAULT nextval('experiment_version_id_seq'::regclass);


--
-- Name: external_request id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY external_request ALTER COLUMN id SET DEFAULT nextval('external_request_id_seq'::regclass);


--
-- Name: fraud_status id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY fraud_status ALTER COLUMN id SET DEFAULT nextval('fraud_status_id_seq'::regclass);


--
-- Name: free_delivery_promotion id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY free_delivery_promotion ALTER COLUMN id SET DEFAULT nextval('free_delivery_promotion_id_seq'::regclass);


--
-- Name: gift_code id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY gift_code ALTER COLUMN id SET DEFAULT nextval('gift_code_id_seq'::regclass);


--
-- Name: github_activity_metrics id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY github_activity_metrics ALTER COLUMN id SET DEFAULT nextval('github_activity_metrics_id_seq'::regclass);


--
-- Name: grab_pay_account id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY grab_pay_account ALTER COLUMN id SET DEFAULT nextval('grab_pay_account_id_seq'::regclass);


--
-- Name: grab_pay_charge id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY grab_pay_charge ALTER COLUMN id SET DEFAULT nextval('grab_pay_charge_id_seq'::regclass);


--
-- Name: grab_payment_account id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY grab_payment_account ALTER COLUMN id SET DEFAULT nextval('grab_payment_account_id_seq'::regclass);


--
-- Name: grab_transfer id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY grab_transfer ALTER COLUMN id SET DEFAULT nextval('grab_transfer_id_seq'::regclass);


--
-- Name: guest_user_type id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY guest_user_type ALTER COLUMN id SET DEFAULT nextval('guest_user_type_id_seq'::regclass);


--
-- Name: invoicing_group id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY invoicing_group ALTER COLUMN id SET DEFAULT nextval('invoicing_group_id_seq'::regclass);


--
-- Name: invoicing_group_membership id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY invoicing_group_membership ALTER COLUMN id SET DEFAULT nextval('invoicing_group_membership_id_seq'::regclass);


--
-- Name: invoicing_group_onboarding_rule id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY invoicing_group_onboarding_rule ALTER COLUMN id SET DEFAULT nextval('invoicing_group_onboarding_rule_id_seq'::regclass);


--
-- Name: ios_notifications_apnservice id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY ios_notifications_apnservice ALTER COLUMN id SET DEFAULT nextval('ios_notifications_apnservice_id_seq'::regclass);


--
-- Name: ios_notifications_device id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY ios_notifications_device ALTER COLUMN id SET DEFAULT nextval('ios_notifications_device_id_seq'::regclass);


--
-- Name: ios_notifications_device_users id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY ios_notifications_device_users ALTER COLUMN id SET DEFAULT nextval('ios_notifications_device_users_id_seq'::regclass);


--
-- Name: ios_notifications_feedbackservice id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY ios_notifications_feedbackservice ALTER COLUMN id SET DEFAULT nextval('ios_notifications_feedbackservice_id_seq'::regclass);


--
-- Name: ios_notifications_notification id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY ios_notifications_notification ALTER COLUMN id SET DEFAULT nextval('ios_notifications_notification_id_seq'::regclass);


--
-- Name: kill_switch_interval id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY kill_switch_interval ALTER COLUMN id SET DEFAULT nextval('kill_switch_interval_id_seq'::regclass);


--
-- Name: managed_account_transfer id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY managed_account_transfer ALTER COLUMN id SET DEFAULT nextval('managed_account_transfer_id_seq'::regclass);


--
-- Name: market id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY market ALTER COLUMN id SET DEFAULT nextval('market_id_seq'::regclass);


--
-- Name: market_special_hours id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY market_special_hours ALTER COLUMN id SET DEFAULT nextval('market_special_hours_id_seq'::regclass);


--
-- Name: marqeta_card_ownership id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY marqeta_card_ownership ALTER COLUMN id SET DEFAULT nextval('marqeta_card_ownership_id_seq'::regclass);


--
-- Name: marqeta_card_transition id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY marqeta_card_transition ALTER COLUMN id SET DEFAULT nextval('marqeta_card_transition_id_seq'::regclass);


--
-- Name: marqeta_decline_exemption id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY marqeta_decline_exemption ALTER COLUMN id SET DEFAULT nextval('marqeta_decline_exemption_id_seq'::regclass);


--
-- Name: marqeta_transaction id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY marqeta_transaction ALTER COLUMN id SET DEFAULT nextval('marqeta_transaction_id_seq'::regclass);


--
-- Name: marqeta_transaction_event id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY marqeta_transaction_event ALTER COLUMN id SET DEFAULT nextval('marqeta_transaction_event_id_seq'::regclass);


--
-- Name: mass_communication_status id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY mass_communication_status ALTER COLUMN id SET DEFAULT nextval('mass_communication_status_id_seq'::regclass);


--
-- Name: multi_promotion id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY multi_promotion ALTER COLUMN id SET DEFAULT nextval('multi_promotion_id_seq'::regclass);


--
-- Name: order id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY "order" ALTER COLUMN id SET DEFAULT nextval('order_id_seq'::regclass);


--
-- Name: order_cart id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY order_cart ALTER COLUMN id SET DEFAULT nextval('order_cart_id_seq'::regclass);


--
-- Name: order_cart_consumer_promotion_link id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY order_cart_consumer_promotion_link ALTER COLUMN id SET DEFAULT nextval('order_cart_consumer_promotion_link_id_seq'::regclass);


--
-- Name: order_cart_device_fingerprint_link id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY order_cart_device_fingerprint_link ALTER COLUMN id SET DEFAULT nextval('order_cart_device_fingerprint_link_id_seq'::regclass);


--
-- Name: order_cart_discount id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY order_cart_discount ALTER COLUMN id SET DEFAULT nextval('order_cart_discount_id_seq'::regclass);


--
-- Name: order_cart_discount_component id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY order_cart_discount_component ALTER COLUMN id SET DEFAULT nextval('order_cart_discount_component_id_seq'::regclass);


--
-- Name: order_cart_discount_component_source_type id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY order_cart_discount_component_source_type ALTER COLUMN id SET DEFAULT nextval('order_cart_discount_component_source_type_id_seq'::regclass);


--
-- Name: order_cart_escalation_reason id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY order_cart_escalation_reason ALTER COLUMN id SET DEFAULT nextval('order_cart_escalation_reason_id_seq'::regclass);


--
-- Name: order_cart_pricing_strategy id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY order_cart_pricing_strategy ALTER COLUMN id SET DEFAULT nextval('order_cart_pricing_strategy_id_seq'::regclass);


--
-- Name: order_item id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY order_item ALTER COLUMN id SET DEFAULT nextval('order_item_id_seq'::regclass);


--
-- Name: order_item_extra_option id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY order_item_extra_option ALTER COLUMN id SET DEFAULT nextval('order_item_extra_option_id_seq'::regclass);


--
-- Name: order_menu_option id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY order_menu_option ALTER COLUMN id SET DEFAULT nextval('order_menu_option_id_seq'::regclass);


--
-- Name: order_placer_queue_state id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY order_placer_queue_state ALTER COLUMN id SET DEFAULT nextval('order_placer_queue_state_id_seq'::regclass);


--
-- Name: payment_account id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY payment_account ALTER COLUMN id SET DEFAULT nextval('payment_account_id_seq'::regclass);


--
-- Name: payment_method id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY payment_method ALTER COLUMN id SET DEFAULT nextval('payment_method_id_seq'::regclass);


--
-- Name: percentage_promotion id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY percentage_promotion ALTER COLUMN id SET DEFAULT nextval('percentage_promotion_id_seq'::regclass);


--
-- Name: place_tag id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY place_tag ALTER COLUMN id SET DEFAULT nextval('place_tag_id_seq'::regclass);


--
-- Name: platform id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY platform ALTER COLUMN id SET DEFAULT nextval('platform_id_seq'::regclass);


--
-- Name: price_transparency_bucket_assignments id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY price_transparency_bucket_assignments ALTER COLUMN id SET DEFAULT nextval('price_transparency_bucket_assignments_id_seq'::regclass);


--
-- Name: promo_code id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY promo_code ALTER COLUMN id SET DEFAULT nextval('promo_code_id_seq'::regclass);


--
-- Name: promo_code_consumer_link id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY promo_code_consumer_link ALTER COLUMN id SET DEFAULT nextval('promo_code_consumer_link_id_seq'::regclass);


--
-- Name: promo_code_markets id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY promo_code_markets ALTER COLUMN id SET DEFAULT nextval('promo_code_markets_id_seq'::regclass);


--
-- Name: promo_code_submarket_link id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY promo_code_submarket_link ALTER COLUMN id SET DEFAULT nextval('promo_code_submarket_link_id_seq'::regclass);


--
-- Name: promotion_consumer_link id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY promotion_consumer_link ALTER COLUMN id SET DEFAULT nextval('promotion_consumer_link_id_seq'::regclass);


--
-- Name: promotion_featured_location_link id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY promotion_featured_location_link ALTER COLUMN id SET DEFAULT nextval('promotion_featured_location_link_id_seq'::regclass);


--
-- Name: promotion_place_tag_link id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY promotion_place_tag_link ALTER COLUMN id SET DEFAULT nextval('promotion_place_tag_link_id_seq'::regclass);


--
-- Name: promotion_redemption_event id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY promotion_redemption_event ALTER COLUMN id SET DEFAULT nextval('promotion_redemption_event_id_seq'::regclass);


--
-- Name: promotion_submarket_link id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY promotion_submarket_link ALTER COLUMN id SET DEFAULT nextval('promotion_submarket_link_id_seq'::regclass);


--
-- Name: promotions_featured_location id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY promotions_featured_location ALTER COLUMN id SET DEFAULT nextval('promotions_featured_location_id_seq'::regclass);


--
-- Name: real_time_supply_model id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY real_time_supply_model ALTER COLUMN id SET DEFAULT nextval('real_time_supply_model_id_seq'::regclass);


--
-- Name: real_time_supply_prediction id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY real_time_supply_prediction ALTER COLUMN id SET DEFAULT nextval('real_time_supply_prediction_id_seq'::regclass);


--
-- Name: realtime_demand_evaluation id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY realtime_demand_evaluation ALTER COLUMN id SET DEFAULT nextval('realtime_demand_evaluation_id_seq'::regclass);


--
-- Name: referral_programs id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY referral_programs ALTER COLUMN id SET DEFAULT nextval('referral_programs_id_seq'::regclass);


--
-- Name: region id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY region ALTER COLUMN id SET DEFAULT nextval('region_id_seq'::regclass);


--
-- Name: region_snapshot id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY region_snapshot ALTER COLUMN id SET DEFAULT nextval('region_snapshot_id_seq'::regclass);


--
-- Name: scheduled_caps_boost id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY scheduled_caps_boost ALTER COLUMN id SET DEFAULT nextval('scheduled_caps_boost_id_seq'::regclass);


--
-- Name: search_engine_store_feed id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY search_engine_store_feed ALTER COLUMN id SET DEFAULT nextval('search_engine_store_feed_id_seq'::regclass);


--
-- Name: seo_local_region id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY seo_local_region ALTER COLUMN id SET DEFAULT nextval('seo_local_region_id_seq'::regclass);


--
-- Name: shortened_url id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY shortened_url ALTER COLUMN id SET DEFAULT nextval('shortened_url_id_seq'::regclass);


--
-- Name: sms_help_message_status id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY sms_help_message_status ALTER COLUMN id SET DEFAULT nextval('sms_help_message_status_id_seq'::regclass);


--
-- Name: sms_opt_out_number id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY sms_opt_out_number ALTER COLUMN id SET DEFAULT nextval('sms_opt_out_number_id_seq'::regclass);


--
-- Name: starship_delivery_info id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY starship_delivery_info ALTER COLUMN id SET DEFAULT nextval('starship_delivery_info_id_seq'::regclass);


--
-- Name: starting_point id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY starting_point ALTER COLUMN id SET DEFAULT nextval('starting_point_id_seq'::regclass);


--
-- Name: starting_point_assignment_latency_stats id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY starting_point_assignment_latency_stats ALTER COLUMN id SET DEFAULT nextval('starting_point_assignment_latency_stats_id_seq'::regclass);


--
-- Name: starting_point_batching_parameters id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY starting_point_batching_parameters ALTER COLUMN id SET DEFAULT nextval('starting_point_batching_parameters_id_seq'::regclass);


--
-- Name: starting_point_delivery_duration_stats id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY starting_point_delivery_duration_stats ALTER COLUMN id SET DEFAULT nextval('starting_point_delivery_duration_stats_id_seq'::regclass);


--
-- Name: starting_point_delivery_hours id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY starting_point_delivery_hours ALTER COLUMN id SET DEFAULT nextval('starting_point_delivery_hours_id_seq'::regclass);


--
-- Name: starting_point_flf_thresholds id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY starting_point_flf_thresholds ALTER COLUMN id SET DEFAULT nextval('starting_point_flf_thresholds_id_seq'::regclass);


--
-- Name: starting_point_r2c_stats id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY starting_point_r2c_stats ALTER COLUMN id SET DEFAULT nextval('starting_point_r2c_stats_id_seq'::regclass);


--
-- Name: starting_point_set id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY starting_point_set ALTER COLUMN id SET DEFAULT nextval('starting_point_set_id_seq'::regclass);


--
-- Name: store_confirmed_time_snapshot id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY store_confirmed_time_snapshot ALTER COLUMN id SET DEFAULT nextval('store_confirmed_time_snapshot_id_seq'::regclass);


--
-- Name: store_consumer_review id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY store_consumer_review ALTER COLUMN id SET DEFAULT nextval('store_consumer_review_id_seq'::regclass);


--
-- Name: store_consumer_review_tag id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY store_consumer_review_tag ALTER COLUMN id SET DEFAULT nextval('store_consumer_review_tag_id_seq'::regclass);


--
-- Name: store_consumer_review_tag_link id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY store_consumer_review_tag_link ALTER COLUMN id SET DEFAULT nextval('store_consumer_review_tag_link_id_seq'::regclass);


--
-- Name: store_delivery_duration_stats id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY store_delivery_duration_stats ALTER COLUMN id SET DEFAULT nextval('store_delivery_duration_stats_id_seq'::regclass);


--
-- Name: store_mastercard_data id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY store_mastercard_data ALTER COLUMN id SET DEFAULT nextval('store_mastercard_data_id_seq'::regclass);


--
-- Name: store_order_cart id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY store_order_cart ALTER COLUMN id SET DEFAULT nextval('store_order_cart_id_seq'::regclass);


--
-- Name: store_order_place_latency_stats id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY store_order_place_latency_stats ALTER COLUMN id SET DEFAULT nextval('store_order_place_latency_stats_id_seq'::regclass);


--
-- Name: stripe_bank_account id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY stripe_bank_account ALTER COLUMN id SET DEFAULT nextval('stripe_bank_account_id_seq'::regclass);


--
-- Name: stripe_card id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY stripe_card ALTER COLUMN id SET DEFAULT nextval('stripe_card_id_seq'::regclass);


--
-- Name: stripe_card_event id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY stripe_card_event ALTER COLUMN id SET DEFAULT nextval('stripe_card_event_id_seq'::regclass);


--
-- Name: stripe_charge id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY stripe_charge ALTER COLUMN id SET DEFAULT nextval('stripe_charge_id_seq'::regclass);


--
-- Name: stripe_customer id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY stripe_customer ALTER COLUMN id SET DEFAULT nextval('stripe_customer_id_seq'::regclass);


--
-- Name: stripe_dispute id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY stripe_dispute ALTER COLUMN id SET DEFAULT nextval('stripe_dispute_id_seq'::regclass);


--
-- Name: stripe_managed_account id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY stripe_managed_account ALTER COLUMN id SET DEFAULT nextval('stripe_managed_account_id_seq'::regclass);


--
-- Name: stripe_recipient id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY stripe_recipient ALTER COLUMN id SET DEFAULT nextval('stripe_recipient_id_seq'::regclass);


--
-- Name: stripe_transfer id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY stripe_transfer ALTER COLUMN id SET DEFAULT nextval('stripe_transfer_id_seq'::regclass);


--
-- Name: submarket id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY submarket ALTER COLUMN id SET DEFAULT nextval('submarket_id_seq'::regclass);


--
-- Name: subnational_division id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY subnational_division ALTER COLUMN id SET DEFAULT nextval('subnational_division_id_seq'::regclass);


--
-- Name: support_delivery_banner id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY support_delivery_banner ALTER COLUMN id SET DEFAULT nextval('support_delivery_banner_id_seq'::regclass);


--
-- Name: support_salesforce_case_record id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY support_salesforce_case_record ALTER COLUMN id SET DEFAULT nextval('support_salesforce_case_record_id_seq'::regclass);


--
-- Name: transfer id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY transfer ALTER COLUMN id SET DEFAULT nextval('transfer_id_seq'::regclass);


--
-- Name: twilio_masking_number id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY twilio_masking_number ALTER COLUMN id SET DEFAULT nextval('twilio_masking_number_id_seq'::regclass);


--
-- Name: twilio_masking_number_assignment id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY twilio_masking_number_assignment ALTER COLUMN id SET DEFAULT nextval('twilio_masking_number_assignment_id_seq'::regclass);


--
-- Name: twilio_number id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY twilio_number ALTER COLUMN id SET DEFAULT nextval('twilio_number_id_seq'::regclass);


--
-- Name: user id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY "user" ALTER COLUMN id SET DEFAULT nextval('user_id_seq'::regclass);


--
-- Name: user_activation_change_event id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY user_activation_change_event ALTER COLUMN id SET DEFAULT nextval('user_activation_change_event_id_seq'::regclass);


--
-- Name: user_deactivation_source id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY user_deactivation_source ALTER COLUMN id SET DEFAULT nextval('user_deactivation_source_id_seq'::regclass);


--
-- Name: user_device_fingerprint_link id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY user_device_fingerprint_link ALTER COLUMN id SET DEFAULT nextval('user_device_fingerprint_link_id_seq'::regclass);


--
-- Name: user_group_admin  id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY "user_group_admin " ALTER COLUMN id SET DEFAULT nextval('"user_group_admin _id_seq"'::regclass);


--
-- Name: user_groups id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY user_groups ALTER COLUMN id SET DEFAULT nextval('user_groups_id_seq'::regclass);


--
-- Name: user_locale_preference id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY user_locale_preference ALTER COLUMN id SET DEFAULT nextval('user_locale_preference_id_seq'::regclass);


--
-- Name: user_social_data id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY user_social_data ALTER COLUMN id SET DEFAULT nextval('user_social_data_id_seq'::regclass);


--
-- Name: user_user_permissions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY user_user_permissions ALTER COLUMN id SET DEFAULT nextval('user_user_permissions_id_seq'::regclass);


--
-- Name: value_delivery_fee_promotion id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY value_delivery_fee_promotion ALTER COLUMN id SET DEFAULT nextval('value_delivery_fee_promotion_id_seq'::regclass);


--
-- Name: value_promotion id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY value_promotion ALTER COLUMN id SET DEFAULT nextval('value_promotion_id_seq'::regclass);


--
-- Name: vanity_url id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY vanity_url ALTER COLUMN id SET DEFAULT nextval('vanity_url_id_seq'::regclass);


--
-- Name: vehicle_reservation id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY vehicle_reservation ALTER COLUMN id SET DEFAULT nextval('vehicle_reservation_id_seq'::regclass);


--
-- Name: verification_attempt id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY verification_attempt ALTER COLUMN id SET DEFAULT nextval('verification_attempt_id_seq'::regclass);


--
-- Name: version_client id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY version_client ALTER COLUMN id SET DEFAULT nextval('version_client_id_seq'::regclass);


--
-- Name: weather_forecast_model id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY weather_forecast_model ALTER COLUMN id SET DEFAULT nextval('weather_forecast_model_id_seq'::regclass);


--
-- Name: weather_historical_model id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY weather_historical_model ALTER COLUMN id SET DEFAULT nextval('weather_historical_model_id_seq'::regclass);


--
-- Name: web_deployment id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY web_deployment ALTER COLUMN id SET DEFAULT nextval('web_deployment_id_seq'::regclass);


--
-- Name: zendesk_template id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY zendesk_template ALTER COLUMN id SET DEFAULT nextval('zendesk_template_id_seq'::regclass);


--
-- Name: address address_formatted_address_point_77f646c6_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY address
    ADD CONSTRAINT address_formatted_address_point_77f646c6_uniq UNIQUE (formatted_address, point);


--
-- Name: address address_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY address
    ADD CONSTRAINT address_pkey PRIMARY KEY (id);


--
-- Name: address_place_tag_link address_place_tag_link_address_id_place_tag_id_8891d625_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY address_place_tag_link
    ADD CONSTRAINT address_place_tag_link_address_id_place_tag_id_8891d625_uniq UNIQUE (address_id, place_tag_id);


--
-- Name: address_place_tag_link address_place_tag_link_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY address_place_tag_link
    ADD CONSTRAINT address_place_tag_link_pkey PRIMARY KEY (id);


--
-- Name: analytics_businessconstants analytics_businessconstants_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY analytics_businessconstants
    ADD CONSTRAINT analytics_businessconstants_pkey PRIMARY KEY (id);


--
-- Name: analytics_dailybusinessmetrics analytics_dailybusinessm_active_date_submarket_id_f406f21b_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY analytics_dailybusinessmetrics
    ADD CONSTRAINT analytics_dailybusinessm_active_date_submarket_id_f406f21b_uniq UNIQUE (active_date, submarket_id);


--
-- Name: analytics_dailybusinessmetrics analytics_dailybusinessmetrics_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY analytics_dailybusinessmetrics
    ADD CONSTRAINT analytics_dailybusinessmetrics_pkey PRIMARY KEY (id);


--
-- Name: analytics_siteoutage analytics_siteoutage_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY analytics_siteoutage
    ADD CONSTRAINT analytics_siteoutage_pkey PRIMARY KEY (id);


--
-- Name: api_key api_key_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY api_key
    ADD CONSTRAINT api_key_pkey PRIMARY KEY (key);


--
-- Name: app_deploy_app app_deploy_app_name_version_15dea9ff_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY app_deploy_app
    ADD CONSTRAINT app_deploy_app_name_version_15dea9ff_uniq UNIQUE (name, version);


--
-- Name: app_deploy_app app_deploy_app_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY app_deploy_app
    ADD CONSTRAINT app_deploy_app_pkey PRIMARY KEY (id);


--
-- Name: apple_notification_app apple_notification_app_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY apple_notification_app
    ADD CONSTRAINT apple_notification_app_pkey PRIMARY KEY (id);


--
-- Name: attribution_data attribution_data_object_type_object_id_4f7ced34_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY attribution_data
    ADD CONSTRAINT attribution_data_object_type_object_id_4f7ced34_uniq UNIQUE (object_type, object_id);


--
-- Name: attribution_data attribution_data_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY attribution_data
    ADD CONSTRAINT attribution_data_pkey PRIMARY KEY (id);


--
-- Name: auth_group auth_group_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY auth_group
    ADD CONSTRAINT auth_group_name_key UNIQUE (name);


--
-- Name: auth_group_permissions auth_group_permissions_group_id_permission_id_0cd325b0_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY auth_group_permissions
    ADD CONSTRAINT auth_group_permissions_group_id_permission_id_0cd325b0_uniq UNIQUE (group_id, permission_id);


--
-- Name: auth_group_permissions auth_group_permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY auth_group_permissions
    ADD CONSTRAINT auth_group_permissions_pkey PRIMARY KEY (id);


--
-- Name: auth_group auth_group_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY auth_group
    ADD CONSTRAINT auth_group_pkey PRIMARY KEY (id);


--
-- Name: auth_permission auth_permission_content_type_id_codename_01ab375a_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY auth_permission
    ADD CONSTRAINT auth_permission_content_type_id_codename_01ab375a_uniq UNIQUE (content_type_id, codename);


--
-- Name: auth_permission auth_permission_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY auth_permission
    ADD CONSTRAINT auth_permission_pkey PRIMARY KEY (id);


--
-- Name: authtoken_token authtoken_token_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY authtoken_token
    ADD CONSTRAINT authtoken_token_pkey PRIMARY KEY (key);


--
-- Name: authtoken_token authtoken_token_user_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY authtoken_token
    ADD CONSTRAINT authtoken_token_user_id_key UNIQUE (user_id);


--
-- Name: banned_ip_address banned_ip_address_ip_address_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY banned_ip_address
    ADD CONSTRAINT banned_ip_address_ip_address_key UNIQUE (ip_address);


--
-- Name: banned_ip_address banned_ip_address_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY banned_ip_address
    ADD CONSTRAINT banned_ip_address_pkey PRIMARY KEY (id);


--
-- Name: base_price_sos_event base_price_sos_event_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY base_price_sos_event
    ADD CONSTRAINT base_price_sos_event_pkey PRIMARY KEY (id);


--
-- Name: blacklisted_consumer_address blacklisted_consumer_address_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY blacklisted_consumer_address
    ADD CONSTRAINT blacklisted_consumer_address_pkey PRIMARY KEY (id);


--
-- Name: capacity_planning_evaluation capacity_planning_evalua_active_date_starting_poi_cd4bf12c_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY capacity_planning_evaluation
    ADD CONSTRAINT capacity_planning_evalua_active_date_starting_poi_cd4bf12c_uniq UNIQUE (active_date, starting_point_id);


--
-- Name: capacity_planning_evaluation capacity_planning_evaluation_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY capacity_planning_evaluation
    ADD CONSTRAINT capacity_planning_evaluation_pkey PRIMARY KEY (id);


--
-- Name: card_acceptor card_acceptor_mid_name_city_zip_code_state_7b4de677_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY card_acceptor
    ADD CONSTRAINT card_acceptor_mid_name_city_zip_code_state_7b4de677_uniq UNIQUE (mid, name, city, zip_code, state);


--
-- Name: card_acceptor card_acceptor_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY card_acceptor
    ADD CONSTRAINT card_acceptor_pkey PRIMARY KEY (id);


--
-- Name: card_acceptor_store_association card_acceptor_store_asso_card_acceptor_id_store_i_67bb9292_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY card_acceptor_store_association
    ADD CONSTRAINT card_acceptor_store_asso_card_acceptor_id_store_i_67bb9292_uniq UNIQUE (card_acceptor_id, store_id);


--
-- Name: card_acceptor_store_association card_acceptor_store_association_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY card_acceptor_store_association
    ADD CONSTRAINT card_acceptor_store_association_pkey PRIMARY KEY (id);


--
-- Name: cash_payment cash_payment_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY cash_payment
    ADD CONSTRAINT cash_payment_pkey PRIMARY KEY (id);


--
-- Name: city city_name_market_id_21c0b0fb_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY city
    ADD CONSTRAINT city_name_market_id_21c0b0fb_uniq UNIQUE (name, market_id);


--
-- Name: city city_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY city
    ADD CONSTRAINT city_pkey PRIMARY KEY (id);


--
-- Name: city city_shortname_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY city
    ADD CONSTRAINT city_shortname_key UNIQUE (shortname);


--
-- Name: city city_slug_market_id_fef0003a_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY city
    ADD CONSTRAINT city_slug_market_id_fef0003a_uniq UNIQUE (slug, market_id);


--
-- Name: communication_preferences_channel_link communication_preference_communication_preference_ac2573c3_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY communication_preferences_channel_link
    ADD CONSTRAINT communication_preference_communication_preference_ac2573c3_uniq UNIQUE (communication_preferences_id, communication_channel_id);


--
-- Name: communication_preferences_channel_link communication_preferences_channel_link_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY communication_preferences_channel_link
    ADD CONSTRAINT communication_preferences_channel_link_pkey PRIMARY KEY (id);


--
-- Name: compensation_request compensation_request_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY compensation_request
    ADD CONSTRAINT compensation_request_pkey PRIMARY KEY (id);


--
-- Name: consumer_account_credits consumer_account_credits_consumer_id_currency_8285b8bf_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_account_credits
    ADD CONSTRAINT consumer_account_credits_consumer_id_currency_8285b8bf_uniq UNIQUE (consumer_id, currency);


--
-- Name: consumer_account_credits consumer_account_credits_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_account_credits
    ADD CONSTRAINT consumer_account_credits_pkey PRIMARY KEY (id);


--
-- Name: consumer_account_credits_transaction consumer_account_credits_transaction_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_account_credits_transaction
    ADD CONSTRAINT consumer_account_credits_transaction_pkey PRIMARY KEY (id);


--
-- Name: consumer_address_link consumer_address_link_consumer_id_address_id_5216f8fe_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_address_link
    ADD CONSTRAINT consumer_address_link_consumer_id_address_id_5216f8fe_uniq UNIQUE (consumer_id, address_id);


--
-- Name: consumer_address_link consumer_address_link_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_address_link
    ADD CONSTRAINT consumer_address_link_pkey PRIMARY KEY (id);


--
-- Name: consumer_announcement_district_link consumer_announcement_di_consumer_announcement_id_82188aa0_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_announcement_district_link
    ADD CONSTRAINT consumer_announcement_di_consumer_announcement_id_82188aa0_uniq UNIQUE (consumer_announcement_id, district_id);


--
-- Name: consumer_announcement_district_link consumer_announcement_district_link_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_announcement_district_link
    ADD CONSTRAINT consumer_announcement_district_link_pkey PRIMARY KEY (id);


--
-- Name: consumer_announcement consumer_announcement_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_announcement
    ADD CONSTRAINT consumer_announcement_pkey PRIMARY KEY (id);


--
-- Name: consumer_announcement_submarkets consumer_announcement_su_consumerannouncement_id__04a7ce85_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_announcement_submarkets
    ADD CONSTRAINT consumer_announcement_su_consumerannouncement_id__04a7ce85_uniq UNIQUE (consumerannouncement_id, submarket_id);


--
-- Name: consumer_announcement_submarkets consumer_announcement_submarkets_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_announcement_submarkets
    ADD CONSTRAINT consumer_announcement_submarkets_pkey PRIMARY KEY (id);


--
-- Name: consumer_channel consumer_channel_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_channel
    ADD CONSTRAINT consumer_channel_name_key UNIQUE (name);


--
-- Name: consumer_channel consumer_channel_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_channel
    ADD CONSTRAINT consumer_channel_pkey PRIMARY KEY (id);


--
-- Name: consumer_channel_submarkets consumer_channel_submark_consumerchannel_id_subma_4e0d508b_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_channel_submarkets
    ADD CONSTRAINT consumer_channel_submark_consumerchannel_id_subma_4e0d508b_uniq UNIQUE (consumerchannel_id, submarket_id);


--
-- Name: consumer_channel_submarkets consumer_channel_submarkets_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_channel_submarkets
    ADD CONSTRAINT consumer_channel_submarkets_pkey PRIMARY KEY (id);


--
-- Name: consumer_charge consumer_charge_idempotency_key_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_charge
    ADD CONSTRAINT consumer_charge_idempotency_key_key UNIQUE (idempotency_key);


--
-- Name: consumer_charge consumer_charge_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_charge
    ADD CONSTRAINT consumer_charge_pkey PRIMARY KEY (id);


--
-- Name: consumer_communication_channel consumer_communication_channel_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_communication_channel
    ADD CONSTRAINT consumer_communication_channel_pkey PRIMARY KEY (id);


--
-- Name: consumer_communication_preferences consumer_communication_preferences_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_communication_preferences
    ADD CONSTRAINT consumer_communication_preferences_pkey PRIMARY KEY (consumer_id);


--
-- Name: consumer_delivery_rating_category_link consumer_delivery_rating_category_link_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_delivery_rating_category_link
    ADD CONSTRAINT consumer_delivery_rating_category_link_pkey PRIMARY KEY (id);


--
-- Name: consumer_delivery_rating_category consumer_delivery_rating_category_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_delivery_rating_category
    ADD CONSTRAINT consumer_delivery_rating_category_name_key UNIQUE (name);


--
-- Name: consumer_delivery_rating_category consumer_delivery_rating_category_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_delivery_rating_category
    ADD CONSTRAINT consumer_delivery_rating_category_pkey PRIMARY KEY (id);


--
-- Name: consumer_delivery_rating consumer_delivery_rating_delivery_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_delivery_rating
    ADD CONSTRAINT consumer_delivery_rating_delivery_id_key UNIQUE (delivery_id);


--
-- Name: consumer_delivery_rating consumer_delivery_rating_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_delivery_rating
    ADD CONSTRAINT consumer_delivery_rating_pkey PRIMARY KEY (id);


--
-- Name: consumer_delivery_rating_category_link consumer_delivery_rating_rating_id_category_id_26e74d66_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_delivery_rating_category_link
    ADD CONSTRAINT consumer_delivery_rating_rating_id_category_id_26e74d66_uniq UNIQUE (rating_id, category_id);


--
-- Name: consumer_discount consumer_discount_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_discount
    ADD CONSTRAINT consumer_discount_pkey PRIMARY KEY (id);


--
-- Name: consumer_donation consumer_donation_order_cart_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_donation
    ADD CONSTRAINT consumer_donation_order_cart_id_key UNIQUE (order_cart_id);


--
-- Name: consumer_donation consumer_donation_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_donation
    ADD CONSTRAINT consumer_donation_pkey PRIMARY KEY (id);


--
-- Name: consumer_donation_recipient_link consumer_donation_recipient_link_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_donation_recipient_link
    ADD CONSTRAINT consumer_donation_recipient_link_pkey PRIMARY KEY (id);


--
-- Name: consumer_empty_store_list_request consumer_empty_store_list_request_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_empty_store_list_request
    ADD CONSTRAINT consumer_empty_store_list_request_pkey PRIMARY KEY (id);


--
-- Name: consumer_faq consumer_faq_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_faq
    ADD CONSTRAINT consumer_faq_pkey PRIMARY KEY (id);


--
-- Name: consumer_favorites consumer_favorites_consumer_id_business_id_713213d0_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_favorites
    ADD CONSTRAINT consumer_favorites_consumer_id_business_id_713213d0_uniq UNIQUE (consumer_id, business_id);


--
-- Name: consumer_favorites consumer_favorites_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_favorites
    ADD CONSTRAINT consumer_favorites_pkey PRIMARY KEY (id);


--
-- Name: consumer_fraud_info consumer_fraud_info_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_fraud_info
    ADD CONSTRAINT consumer_fraud_info_pkey PRIMARY KEY (id);


--
-- Name: consumer_ios_devices consumer_ios_devices_consumer_id_device_id_885756cd_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_ios_devices
    ADD CONSTRAINT consumer_ios_devices_consumer_id_device_id_885756cd_uniq UNIQUE (consumer_id, device_id);


--
-- Name: consumer_ios_devices consumer_ios_devices_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_ios_devices
    ADD CONSTRAINT consumer_ios_devices_pkey PRIMARY KEY (id);


--
-- Name: consumer consumer_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer
    ADD CONSTRAINT consumer_pkey PRIMARY KEY (id);


--
-- Name: consumer_preferences_category_link consumer_preferences_cat_consumer_preferences_id__3c788a60_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_preferences_category_link
    ADD CONSTRAINT consumer_preferences_cat_consumer_preferences_id__3c788a60_uniq UNIQUE (consumer_preferences_id, category_name);


--
-- Name: consumer_preferences_category_link consumer_preferences_category_link_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_preferences_category_link
    ADD CONSTRAINT consumer_preferences_category_link_pkey PRIMARY KEY (id);


--
-- Name: consumer_preferences consumer_preferences_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_preferences
    ADD CONSTRAINT consumer_preferences_pkey PRIMARY KEY (id);


--
-- Name: consumer_profile_edit_history consumer_profile_edit_history_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_profile_edit_history
    ADD CONSTRAINT consumer_profile_edit_history_pkey PRIMARY KEY (id);


--
-- Name: consumer_promotion_campaign consumer_promotion_campaign_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_promotion_campaign
    ADD CONSTRAINT consumer_promotion_campaign_pkey PRIMARY KEY (id);


--
-- Name: consumer_promotion consumer_promotion_code_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_promotion
    ADD CONSTRAINT consumer_promotion_code_key UNIQUE (code);


--
-- Name: consumer_promotion consumer_promotion_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_promotion
    ADD CONSTRAINT consumer_promotion_pkey PRIMARY KEY (id);


--
-- Name: consumer_push_notification consumer_push_notification_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_push_notification
    ADD CONSTRAINT consumer_push_notification_pkey PRIMARY KEY (id);


--
-- Name: consumer consumer_referral_code_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer
    ADD CONSTRAINT consumer_referral_code_key UNIQUE (referral_code);


--
-- Name: consumer_referral_link consumer_referral_link_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_referral_link
    ADD CONSTRAINT consumer_referral_link_pkey PRIMARY KEY (id);


--
-- Name: consumer_referral_link consumer_referral_link_referree_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_referral_link
    ADD CONSTRAINT consumer_referral_link_referree_id_key UNIQUE (referree_id);


--
-- Name: consumer_referral_link consumer_referral_link_referrer_id_email_4ebf7989_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_referral_link
    ADD CONSTRAINT consumer_referral_link_referrer_id_email_4ebf7989_uniq UNIQUE (referrer_id, email);


--
-- Name: consumer_share consumer_share_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_share
    ADD CONSTRAINT consumer_share_pkey PRIMARY KEY (id);


--
-- Name: consumer_store_request consumer_store_request_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_store_request
    ADD CONSTRAINT consumer_store_request_pkey PRIMARY KEY (id);


--
-- Name: consumer_stripe_customer_link consumer_stripe_customer_consumer_id_country_code_6fefbed6_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_stripe_customer_link
    ADD CONSTRAINT consumer_stripe_customer_consumer_id_country_code_6fefbed6_uniq UNIQUE (consumer_id, country_code);


--
-- Name: consumer_stripe_customer_link consumer_stripe_customer_link_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_stripe_customer_link
    ADD CONSTRAINT consumer_stripe_customer_link_pkey PRIMARY KEY (id);


--
-- Name: consumer_subscription consumer_subscription_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_subscription
    ADD CONSTRAINT consumer_subscription_pkey PRIMARY KEY (id);


--
-- Name: consumer_subscription_plan_featured_location_link consumer_subscription_pl_consumer_subscription_pl_bdbe72b3_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_subscription_plan_featured_location_link
    ADD CONSTRAINT consumer_subscription_pl_consumer_subscription_pl_bdbe72b3_uniq UNIQUE (consumer_subscription_plan_id, featured_location_id);


--
-- Name: consumer_subscription_plan_trial_featured_location_link consumer_subscription_pl_consumer_subscription_pl_c014cacd_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_subscription_plan_trial_featured_location_link
    ADD CONSTRAINT consumer_subscription_pl_consumer_subscription_pl_c014cacd_uniq UNIQUE (consumer_subscription_plan_trial_id, featured_location_id);


--
-- Name: consumer_subscription_plan_trial_promotion_infos consumer_subscription_pl_consumersubscriptionplan_1f379c78_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_subscription_plan_trial_promotion_infos
    ADD CONSTRAINT consumer_subscription_pl_consumersubscriptionplan_1f379c78_uniq UNIQUE (consumersubscriptionplantrial_id, consumersubscriptionplanpromotioninfo_id);


--
-- Name: consumer_subscription_plan_promotion_infos consumer_subscription_pl_consumersubscriptionplan_46566ca7_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_subscription_plan_promotion_infos
    ADD CONSTRAINT consumer_subscription_pl_consumersubscriptionplan_46566ca7_uniq UNIQUE (consumersubscriptionplan_id, consumersubscriptionplanpromotioninfo_id);


--
-- Name: consumer_subscription_plan_submarket_link consumer_subscription_pl_submarket_id_consumer_su_766607e1_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_subscription_plan_submarket_link
    ADD CONSTRAINT consumer_subscription_pl_submarket_id_consumer_su_766607e1_uniq UNIQUE (submarket_id, consumer_subscription_plan_id);


--
-- Name: consumer_subscription_plan_trial_submarket_link consumer_subscription_pl_submarket_id_consumer_su_90d86024_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_subscription_plan_trial_submarket_link
    ADD CONSTRAINT consumer_subscription_pl_submarket_id_consumer_su_90d86024_uniq UNIQUE (submarket_id, consumer_subscription_plan_trial_id);


--
-- Name: consumer_subscription_plan_featured_location_link consumer_subscription_plan_featured_location_link_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_subscription_plan_featured_location_link
    ADD CONSTRAINT consumer_subscription_plan_featured_location_link_pkey PRIMARY KEY (id);


--
-- Name: consumer_subscription_plan consumer_subscription_plan_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_subscription_plan
    ADD CONSTRAINT consumer_subscription_plan_pkey PRIMARY KEY (id);


--
-- Name: consumer_subscription_plan_promotion_info consumer_subscription_plan_promotion_info_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_subscription_plan_promotion_info
    ADD CONSTRAINT consumer_subscription_plan_promotion_info_pkey PRIMARY KEY (id);


--
-- Name: consumer_subscription_plan_promotion_infos consumer_subscription_plan_promotion_infos_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_subscription_plan_promotion_infos
    ADD CONSTRAINT consumer_subscription_plan_promotion_infos_pkey PRIMARY KEY (id);


--
-- Name: consumer_subscription_plan consumer_subscription_plan_stripe_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_subscription_plan
    ADD CONSTRAINT consumer_subscription_plan_stripe_id_key UNIQUE (stripe_id);


--
-- Name: consumer_subscription_plan_submarket_link consumer_subscription_plan_submarket_link_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_subscription_plan_submarket_link
    ADD CONSTRAINT consumer_subscription_plan_submarket_link_pkey PRIMARY KEY (id);


--
-- Name: consumer_subscription_plan_trial_featured_location_link consumer_subscription_plan_trial_featured_location_link_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_subscription_plan_trial_featured_location_link
    ADD CONSTRAINT consumer_subscription_plan_trial_featured_location_link_pkey PRIMARY KEY (id);


--
-- Name: consumer_subscription_plan_trial consumer_subscription_plan_trial_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_subscription_plan_trial
    ADD CONSTRAINT consumer_subscription_plan_trial_pkey PRIMARY KEY (id);


--
-- Name: consumer_subscription_plan_trial_promotion_infos consumer_subscription_plan_trial_promotion_infos_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_subscription_plan_trial_promotion_infos
    ADD CONSTRAINT consumer_subscription_plan_trial_promotion_infos_pkey PRIMARY KEY (id);


--
-- Name: consumer_subscription_plan_trial_submarket_link consumer_subscription_plan_trial_submarket_link_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_subscription_plan_trial_submarket_link
    ADD CONSTRAINT consumer_subscription_plan_trial_submarket_link_pkey PRIMARY KEY (id);


--
-- Name: consumer_subscription consumer_subscription_stripe_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_subscription
    ADD CONSTRAINT consumer_subscription_stripe_id_key UNIQUE (stripe_id);


--
-- Name: consumer_subscription_unit consumer_subscription_unit_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_subscription_unit
    ADD CONSTRAINT consumer_subscription_unit_pkey PRIMARY KEY (id);


--
-- Name: consumer_subscription_unit consumer_subscription_unit_stripe_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_subscription_unit
    ADD CONSTRAINT consumer_subscription_unit_stripe_id_key UNIQUE (stripe_id);


--
-- Name: consumer_survey_answer_option consumer_survey_answer_option_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_survey_answer_option
    ADD CONSTRAINT consumer_survey_answer_option_pkey PRIMARY KEY (id);


--
-- Name: consumer_survey consumer_survey_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_survey
    ADD CONSTRAINT consumer_survey_pkey PRIMARY KEY (id);


--
-- Name: consumer_survey_question consumer_survey_question_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_survey_question
    ADD CONSTRAINT consumer_survey_question_pkey PRIMARY KEY (id);


--
-- Name: consumer_survey_question_response consumer_survey_question_response_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_survey_question_response
    ADD CONSTRAINT consumer_survey_question_response_pkey PRIMARY KEY (id);


--
-- Name: consumer_survey_response consumer_survey_response_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_survey_response
    ADD CONSTRAINT consumer_survey_response_pkey PRIMARY KEY (id);


--
-- Name: consumer_terms_of_service consumer_terms_of_service_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_terms_of_service
    ADD CONSTRAINT consumer_terms_of_service_pkey PRIMARY KEY (id);


--
-- Name: consumer_terms_of_service consumer_terms_of_service_version_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_terms_of_service
    ADD CONSTRAINT consumer_terms_of_service_version_key UNIQUE (version);


--
-- Name: consumer_tos_link consumer_tos_link_consumer_id_terms_of_service_id_2ca75e25_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_tos_link
    ADD CONSTRAINT consumer_tos_link_consumer_id_terms_of_service_id_2ca75e25_uniq UNIQUE (consumer_id, terms_of_service_id);


--
-- Name: consumer_tos_link consumer_tos_link_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_tos_link
    ADD CONSTRAINT consumer_tos_link_pkey PRIMARY KEY (id);


--
-- Name: consumer consumer_user_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer
    ADD CONSTRAINT consumer_user_id_key UNIQUE (user_id);


--
-- Name: consumer_variable_pay consumer_variable_pay_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_variable_pay
    ADD CONSTRAINT consumer_variable_pay_pkey PRIMARY KEY (id);


--
-- Name: consumer_verification_status consumer_verification_status_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_verification_status
    ADD CONSTRAINT consumer_verification_status_pkey PRIMARY KEY (consumer_id);


--
-- Name: core_image core_image_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY core_image
    ADD CONSTRAINT core_image_pkey PRIMARY KEY (id);


--
-- Name: core_modelannotation core_modelannotation_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY core_modelannotation
    ADD CONSTRAINT core_modelannotation_pkey PRIMARY KEY (id);


--
-- Name: core_modelannotation core_modelannotation_target_ct_id_target_id_a_b54a751e_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY core_modelannotation
    ADD CONSTRAINT core_modelannotation_target_ct_id_target_id_a_b54a751e_uniq UNIQUE (target_ct_id, target_id, annotation_type);


--
-- Name: country country_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY country
    ADD CONSTRAINT country_name_key UNIQUE (name);


--
-- Name: country country_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY country
    ADD CONSTRAINT country_pkey PRIMARY KEY (id);


--
-- Name: country country_shortname_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY country
    ADD CONSTRAINT country_shortname_key UNIQUE (shortname);


--
-- Name: credit_refund_delivery_error credit_refund_delivery_error_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY credit_refund_delivery_error
    ADD CONSTRAINT credit_refund_delivery_error_pkey PRIMARY KEY (id);


--
-- Name: credit_refund_error credit_refund_error_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY credit_refund_error
    ADD CONSTRAINT credit_refund_error_pkey PRIMARY KEY (id);


--
-- Name: credit_refund_order_item_error credit_refund_order_item_error_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY credit_refund_order_item_error
    ADD CONSTRAINT credit_refund_order_item_error_pkey PRIMARY KEY (id);


--
-- Name: curated_category curated_category_identifier_submarket_id_aac2affb_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY curated_category
    ADD CONSTRAINT curated_category_identifier_submarket_id_aac2affb_uniq UNIQUE (identifier, submarket_id);


--
-- Name: curated_category_membership curated_category_members_category_id_member_ct_id_15b8c02c_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY curated_category_membership
    ADD CONSTRAINT curated_category_members_category_id_member_ct_id_15b8c02c_uniq UNIQUE (category_id, member_ct_id, member_id, start_time);


--
-- Name: curated_category_membership curated_category_membership_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY curated_category_membership
    ADD CONSTRAINT curated_category_membership_pkey PRIMARY KEY (id);


--
-- Name: curated_category curated_category_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY curated_category
    ADD CONSTRAINT curated_category_pkey PRIMARY KEY (id);


--
-- Name: currency_exchange_rate currency_exchange_rate_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY currency_exchange_rate
    ADD CONSTRAINT currency_exchange_rate_pkey PRIMARY KEY (id);


--
-- Name: dasher_capacity_model dasher_capacity_model_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY dasher_capacity_model
    ADD CONSTRAINT dasher_capacity_model_pkey PRIMARY KEY (id);


--
-- Name: dasher_capacity_plan dasher_capacity_plan_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY dasher_capacity_plan
    ADD CONSTRAINT dasher_capacity_plan_pkey PRIMARY KEY (id);


--
-- Name: dasher_onboarding dasher_onboarding_dasher_id_onboarding_type_id_cb5292ad_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY dasher_onboarding
    ADD CONSTRAINT dasher_onboarding_dasher_id_onboarding_type_id_cb5292ad_uniq UNIQUE (dasher_id, onboarding_type_id);


--
-- Name: dasher_onboarding dasher_onboarding_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY dasher_onboarding
    ADD CONSTRAINT dasher_onboarding_pkey PRIMARY KEY (id);


--
-- Name: dasher_onboarding_type dasher_onboarding_type_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY dasher_onboarding_type
    ADD CONSTRAINT dasher_onboarding_type_pkey PRIMARY KEY (id);


--
-- Name: dd4b_expense_code dd4b_expense_code_organization_id_expense_code_439c3f6a_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY dd4b_expense_code
    ADD CONSTRAINT dd4b_expense_code_organization_id_expense_code_439c3f6a_uniq UNIQUE (organization_id, expense_code);


--
-- Name: dd4b_expense_code dd4b_expense_code_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY dd4b_expense_code
    ADD CONSTRAINT dd4b_expense_code_pkey PRIMARY KEY (id);


--
-- Name: delivery_assignment_constraint delivery_assignment_constraint_delivery_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_assignment_constraint
    ADD CONSTRAINT delivery_assignment_constraint_delivery_id_key UNIQUE (delivery_id);


--
-- Name: delivery_assignment_constraint delivery_assignment_constraint_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_assignment_constraint
    ADD CONSTRAINT delivery_assignment_constraint_pkey PRIMARY KEY (id);


--
-- Name: delivery_batch_membership delivery_batch_membership_batch_id_sort_index_3046d8ea_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_batch_membership
    ADD CONSTRAINT delivery_batch_membership_batch_id_sort_index_3046d8ea_uniq UNIQUE (batch_id, sort_index);


--
-- Name: delivery_batch_membership delivery_batch_membership_delivery_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_batch_membership
    ADD CONSTRAINT delivery_batch_membership_delivery_id_key UNIQUE (delivery_id);


--
-- Name: delivery_batch_membership delivery_batch_membership_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_batch_membership
    ADD CONSTRAINT delivery_batch_membership_pkey PRIMARY KEY (id);


--
-- Name: delivery_batch delivery_batch_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_batch
    ADD CONSTRAINT delivery_batch_pkey PRIMARY KEY (id);


--
-- Name: delivery_cancellation_reason_category delivery_cancellation_reason_category_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_cancellation_reason_category
    ADD CONSTRAINT delivery_cancellation_reason_category_name_key UNIQUE (name);


--
-- Name: delivery_cancellation_reason_category delivery_cancellation_reason_category_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_cancellation_reason_category
    ADD CONSTRAINT delivery_cancellation_reason_category_pkey PRIMARY KEY (id);


--
-- Name: delivery_cancellation_reason delivery_cancellation_reason_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_cancellation_reason
    ADD CONSTRAINT delivery_cancellation_reason_name_key UNIQUE (name);


--
-- Name: delivery_cancellation_reason delivery_cancellation_reason_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_cancellation_reason
    ADD CONSTRAINT delivery_cancellation_reason_pkey PRIMARY KEY (id);


--
-- Name: delivery_catering_verification delivery_catering_verification_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_catering_verification
    ADD CONSTRAINT delivery_catering_verification_pkey PRIMARY KEY (id);


--
-- Name: delivery_drive_info delivery_drive_info_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_drive_info
    ADD CONSTRAINT delivery_drive_info_pkey PRIMARY KEY (delivery_id);


--
-- Name: delivery_error_source delivery_error_source_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_error_source
    ADD CONSTRAINT delivery_error_source_pkey PRIMARY KEY (id);


--
-- Name: delivery_event_category delivery_event_category_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_event_category
    ADD CONSTRAINT delivery_event_category_name_key UNIQUE (name);


--
-- Name: delivery_event_category delivery_event_category_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_event_category
    ADD CONSTRAINT delivery_event_category_pkey PRIMARY KEY (id);


--
-- Name: delivery_event delivery_event_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_event
    ADD CONSTRAINT delivery_event_pkey PRIMARY KEY (id);


--
-- Name: delivery_fee_promotion delivery_fee_promotion_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_fee_promotion
    ADD CONSTRAINT delivery_fee_promotion_pkey PRIMARY KEY (id);


--
-- Name: delivery_funding delivery_funding_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_funding
    ADD CONSTRAINT delivery_funding_pkey PRIMARY KEY (id);


--
-- Name: delivery_gift delivery_gift_code_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_gift
    ADD CONSTRAINT delivery_gift_code_key UNIQUE (code);


--
-- Name: delivery_gift delivery_gift_delivery_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_gift
    ADD CONSTRAINT delivery_gift_delivery_id_key UNIQUE (delivery_id);


--
-- Name: delivery_gift delivery_gift_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_gift
    ADD CONSTRAINT delivery_gift_pkey PRIMARY KEY (id);


--
-- Name: delivery_growth_model delivery_growth_model_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_growth_model
    ADD CONSTRAINT delivery_growth_model_pkey PRIMARY KEY (id);


--
-- Name: delivery_growth_prediction delivery_growth_prediction_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_growth_prediction
    ADD CONSTRAINT delivery_growth_prediction_pkey PRIMARY KEY (id);


--
-- Name: delivery delivery_idempotency_key_e148c04d_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery
    ADD CONSTRAINT delivery_idempotency_key_e148c04d_uniq UNIQUE (idempotency_key);


--
-- Name: delivery_issue delivery_issue_event_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_issue
    ADD CONSTRAINT delivery_issue_event_id_key UNIQUE (event_id);


--
-- Name: delivery_issue delivery_issue_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_issue
    ADD CONSTRAINT delivery_issue_pkey PRIMARY KEY (id);


--
-- Name: delivery_issue delivery_issue_salesforce_case_uid_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_issue
    ADD CONSTRAINT delivery_issue_salesforce_case_uid_key UNIQUE (salesforce_case_uid);


--
-- Name: delivery_item delivery_item_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_item
    ADD CONSTRAINT delivery_item_pkey PRIMARY KEY (id);


--
-- Name: delivery_masking_number_assignment delivery_masking_number__twilio_masking_number_id_522f7b18_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_masking_number_assignment
    ADD CONSTRAINT delivery_masking_number__twilio_masking_number_id_522f7b18_uniq UNIQUE (twilio_masking_number_id, delivery_id, participants_type);


--
-- Name: delivery_masking_number_assignment delivery_masking_number_assignment_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_masking_number_assignment
    ADD CONSTRAINT delivery_masking_number_assignment_pkey PRIMARY KEY (id);


--
-- Name: delivery delivery_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery
    ADD CONSTRAINT delivery_pkey PRIMARY KEY (id);


--
-- Name: delivery delivery_public_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery
    ADD CONSTRAINT delivery_public_id_key UNIQUE (public_id);


--
-- Name: delivery_rating_category_link delivery_rating_category_link_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_rating_category_link
    ADD CONSTRAINT delivery_rating_category_link_pkey PRIMARY KEY (id);


--
-- Name: delivery_rating_category delivery_rating_category_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_rating_category
    ADD CONSTRAINT delivery_rating_category_pkey PRIMARY KEY (id);


--
-- Name: delivery_rating_category_link delivery_rating_category_rating_id_category_id_a2d0c136_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_rating_category_link
    ADD CONSTRAINT delivery_rating_category_rating_id_category_id_a2d0c136_uniq UNIQUE (rating_id, category_id);


--
-- Name: delivery_rating delivery_rating_delivery_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_rating
    ADD CONSTRAINT delivery_rating_delivery_id_key UNIQUE (delivery_id);


--
-- Name: delivery_rating delivery_rating_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_rating
    ADD CONSTRAINT delivery_rating_pkey PRIMARY KEY (id);


--
-- Name: delivery_receipt delivery_receipt_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_receipt
    ADD CONSTRAINT delivery_receipt_pkey PRIMARY KEY (id);


--
-- Name: delivery_recipient delivery_recipient_first_name_last_name_ema_17ba98ed_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_recipient
    ADD CONSTRAINT delivery_recipient_first_name_last_name_ema_17ba98ed_uniq UNIQUE (first_name, last_name, email, phone_number);


--
-- Name: delivery_recipient delivery_recipient_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_recipient
    ADD CONSTRAINT delivery_recipient_pkey PRIMARY KEY (id);


--
-- Name: delivery_request delivery_request_delivery_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_request
    ADD CONSTRAINT delivery_request_delivery_id_key UNIQUE (delivery_id);


--
-- Name: delivery_request delivery_request_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_request
    ADD CONSTRAINT delivery_request_pkey PRIMARY KEY (id);


--
-- Name: delivery_request_submission_monitor delivery_request_submission_monitor_key_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_request_submission_monitor
    ADD CONSTRAINT delivery_request_submission_monitor_key_key UNIQUE (key);


--
-- Name: delivery_request_submission_monitor delivery_request_submission_monitor_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_request_submission_monitor
    ADD CONSTRAINT delivery_request_submission_monitor_pkey PRIMARY KEY (id);


--
-- Name: delivery_set_mapping delivery_set_mapping_delivery_id_delivery_set_id_40cb0a97_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_set_mapping
    ADD CONSTRAINT delivery_set_mapping_delivery_id_delivery_set_id_40cb0a97_uniq UNIQUE (delivery_id, delivery_set_id);


--
-- Name: delivery_set_mapping delivery_set_mapping_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_set_mapping
    ADD CONSTRAINT delivery_set_mapping_pkey PRIMARY KEY (id);


--
-- Name: delivery_set delivery_set_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_set
    ADD CONSTRAINT delivery_set_pkey PRIMARY KEY (id);


--
-- Name: delivery_simulator delivery_simulator_drive_order_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_simulator
    ADD CONSTRAINT delivery_simulator_drive_order_id_key UNIQUE (drive_order_id);


--
-- Name: delivery_simulator delivery_simulator_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_simulator
    ADD CONSTRAINT delivery_simulator_pkey PRIMARY KEY (delivery_id);


--
-- Name: depot depot_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY depot
    ADD CONSTRAINT depot_pkey PRIMARY KEY (id);


--
-- Name: developer developer_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY developer
    ADD CONSTRAINT developer_pkey PRIMARY KEY (user_id);


--
-- Name: device_fingerprint device_fingerprint_fingerprint_fingerprint_type_0a116324_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY device_fingerprint
    ADD CONSTRAINT device_fingerprint_fingerprint_fingerprint_type_0a116324_uniq UNIQUE (fingerprint, fingerprint_type);


--
-- Name: device_fingerprint device_fingerprint_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY device_fingerprint
    ADD CONSTRAINT device_fingerprint_pkey PRIMARY KEY (id);


--
-- Name: dispatch_error dispatch_error_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY dispatch_error
    ADD CONSTRAINT dispatch_error_pkey PRIMARY KEY (id);


--
-- Name: dispatcher dispatcher_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY dispatcher
    ADD CONSTRAINT dispatcher_pkey PRIMARY KEY (user_id);


--
-- Name: district_geometry district_geometry_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY district_geometry
    ADD CONSTRAINT district_geometry_pkey PRIMARY KEY (district_id);


--
-- Name: district district_html_color_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY district
    ADD CONSTRAINT district_html_color_key UNIQUE (html_color);


--
-- Name: district district_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY district
    ADD CONSTRAINT district_name_key UNIQUE (name);


--
-- Name: district district_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY district
    ADD CONSTRAINT district_pkey PRIMARY KEY (id);


--
-- Name: district district_shortname_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY district
    ADD CONSTRAINT district_shortname_key UNIQUE (shortname);


--
-- Name: district_starting_point_availability_override district_starting_point__district_id_startingpoin_6a28bdb0_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY district_starting_point_availability_override
    ADD CONSTRAINT district_starting_point__district_id_startingpoin_6a28bdb0_uniq UNIQUE (district_id, startingpoint_id);


--
-- Name: district_starting_point_availability_override district_starting_point_availability_override_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY district_starting_point_availability_override
    ADD CONSTRAINT district_starting_point_availability_override_pkey PRIMARY KEY (id);


--
-- Name: django_admin_log django_admin_log_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY django_admin_log
    ADD CONSTRAINT django_admin_log_pkey PRIMARY KEY (id);


--
-- Name: django_content_type django_content_type_app_label_model_76bd3d3b_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY django_content_type
    ADD CONSTRAINT django_content_type_app_label_model_76bd3d3b_uniq UNIQUE (app_label, model);


--
-- Name: django_content_type django_content_type_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY django_content_type
    ADD CONSTRAINT django_content_type_pkey PRIMARY KEY (id);


--
-- Name: django_migrations django_migrations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY django_migrations
    ADD CONSTRAINT django_migrations_pkey PRIMARY KEY (id);


--
-- Name: django_session django_session_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY django_session
    ADD CONSTRAINT django_session_pkey PRIMARY KEY (session_key);


--
-- Name: django_twilio_caller django_twilio_caller_phone_number_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY django_twilio_caller
    ADD CONSTRAINT django_twilio_caller_phone_number_key UNIQUE (phone_number);


--
-- Name: django_twilio_caller django_twilio_caller_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY django_twilio_caller
    ADD CONSTRAINT django_twilio_caller_pkey PRIMARY KEY (id);


--
-- Name: django_twilio_credential django_twilio_credential_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY django_twilio_credential
    ADD CONSTRAINT django_twilio_credential_pkey PRIMARY KEY (id);


--
-- Name: django_twilio_credential django_twilio_credential_user_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY django_twilio_credential
    ADD CONSTRAINT django_twilio_credential_user_id_key UNIQUE (user_id);


--
-- Name: donation_recipient donation_recipient_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY donation_recipient
    ADD CONSTRAINT donation_recipient_name_key UNIQUE (name);


--
-- Name: donation_recipient donation_recipient_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY donation_recipient
    ADD CONSTRAINT donation_recipient_pkey PRIMARY KEY (id);


--
-- Name: doordash_blacklistedemail doordash_blacklistedemail_email_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY doordash_blacklistedemail
    ADD CONSTRAINT doordash_blacklistedemail_email_key UNIQUE (email);


--
-- Name: doordash_blacklistedemail doordash_blacklistedemail_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY doordash_blacklistedemail
    ADD CONSTRAINT doordash_blacklistedemail_pkey PRIMARY KEY (id);


--
-- Name: doordash_blacklistedpaymentcard doordash_blacklistedpaymentcard_fingerprint_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY doordash_blacklistedpaymentcard
    ADD CONSTRAINT doordash_blacklistedpaymentcard_fingerprint_key UNIQUE (fingerprint);


--
-- Name: doordash_blacklistedpaymentcard doordash_blacklistedpaymentcard_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY doordash_blacklistedpaymentcard
    ADD CONSTRAINT doordash_blacklistedpaymentcard_pkey PRIMARY KEY (id);


--
-- Name: doordash_blacklistedphonenumber doordash_blacklistedphonenumber_phone_number_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY doordash_blacklistedphonenumber
    ADD CONSTRAINT doordash_blacklistedphonenumber_phone_number_key UNIQUE (phone_number);


--
-- Name: doordash_blacklistedphonenumber doordash_blacklistedphonenumber_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY doordash_blacklistedphonenumber
    ADD CONSTRAINT doordash_blacklistedphonenumber_pkey PRIMARY KEY (id);


--
-- Name: doordash_blacklisteduser doordash_blacklisteduser_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY doordash_blacklisteduser
    ADD CONSTRAINT doordash_blacklisteduser_pkey PRIMARY KEY (id);


--
-- Name: doordash_blacklisteduser doordash_blacklisteduser_user_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY doordash_blacklisteduser
    ADD CONSTRAINT doordash_blacklisteduser_user_id_key UNIQUE (user_id);


--
-- Name: doordash_employmentperiod doordash_employmentperiod_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY doordash_employmentperiod
    ADD CONSTRAINT doordash_employmentperiod_pkey PRIMARY KEY (id);


--
-- Name: doordash_orderitemsubstitutionevent doordash_orderitemsubstitutionevent_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY doordash_orderitemsubstitutionevent
    ADD CONSTRAINT doordash_orderitemsubstitutionevent_pkey PRIMARY KEY (id);


--
-- Name: drive_business_mapping drive_business_mapping_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY drive_business_mapping
    ADD CONSTRAINT drive_business_mapping_pkey PRIMARY KEY (id);


--
-- Name: drive_delivery_identifier_mapping drive_delivery_identifie_store_id_external_id_82d42189_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY drive_delivery_identifier_mapping
    ADD CONSTRAINT drive_delivery_identifie_store_id_external_id_82d42189_uniq UNIQUE (store_id, external_id);


--
-- Name: drive_delivery_identifier_mapping drive_delivery_identifier_mapping_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY drive_delivery_identifier_mapping
    ADD CONSTRAINT drive_delivery_identifier_mapping_pkey PRIMARY KEY (delivery_id);


--
-- Name: drive_effort_based_pay_vars drive_effort_based_pay_vars_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY drive_effort_based_pay_vars
    ADD CONSTRAINT drive_effort_based_pay_vars_pkey PRIMARY KEY (id);


--
-- Name: drive_external_batch_id_mapping drive_external_batch_id_mapping_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY drive_external_batch_id_mapping
    ADD CONSTRAINT drive_external_batch_id_mapping_pkey PRIMARY KEY (delivery_id);


--
-- Name: drive_order drive_order_delivery_tracking_url_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY drive_order
    ADD CONSTRAINT drive_order_delivery_tracking_url_key UNIQUE (delivery_tracking_url);


--
-- Name: drive_order drive_order_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY drive_order
    ADD CONSTRAINT drive_order_pkey PRIMARY KEY (id);


--
-- Name: drive_order drive_order_public_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY drive_order
    ADD CONSTRAINT drive_order_public_id_key UNIQUE (public_id);


--
-- Name: drive_quote_acceptance drive_quote_acceptance_delivery_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY drive_quote_acceptance
    ADD CONSTRAINT drive_quote_acceptance_delivery_id_key UNIQUE (delivery_id);


--
-- Name: drive_quote_acceptance drive_quote_acceptance_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY drive_quote_acceptance
    ADD CONSTRAINT drive_quote_acceptance_pkey PRIMARY KEY (quote_id);


--
-- Name: drive_quote drive_quote_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY drive_quote
    ADD CONSTRAINT drive_quote_pkey PRIMARY KEY (quote_id);


--
-- Name: drive_store_catering_setup_instruction drive_store_catering_setup_instruction_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY drive_store_catering_setup_instruction
    ADD CONSTRAINT drive_store_catering_setup_instruction_pkey PRIMARY KEY (id);


--
-- Name: drive_store_id_mapping drive_store_id_mapping_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY drive_store_id_mapping
    ADD CONSTRAINT drive_store_id_mapping_pkey PRIMARY KEY (store_id);


--
-- Name: drive_webhook_event drive_webhook_event_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY drive_webhook_event
    ADD CONSTRAINT drive_webhook_event_pkey PRIMARY KEY (id);


--
-- Name: drive_webhook_subscription drive_webhook_subscripti_business_id_delivery_eve_0ce9130c_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY drive_webhook_subscription
    ADD CONSTRAINT drive_webhook_subscripti_business_id_delivery_eve_0ce9130c_uniq UNIQUE (business_id, delivery_event_category_id);


--
-- Name: drive_webhook_subscription drive_webhook_subscription_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY drive_webhook_subscription
    ADD CONSTRAINT drive_webhook_subscription_pkey PRIMARY KEY (id);


--
-- Name: email_holdout_group email_holdout_group_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY email_holdout_group
    ADD CONSTRAINT email_holdout_group_pkey PRIMARY KEY (id);


--
-- Name: email_notification email_notification_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY email_notification
    ADD CONSTRAINT email_notification_pkey PRIMARY KEY (id);


--
-- Name: email_preference email_preference_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY email_preference
    ADD CONSTRAINT email_preference_pkey PRIMARY KEY (id);


--
-- Name: email_verification_request email_verification_request_email_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY email_verification_request
    ADD CONSTRAINT email_verification_request_email_key UNIQUE (email);


--
-- Name: email_verification_request email_verification_request_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY email_verification_request
    ADD CONSTRAINT email_verification_request_pkey PRIMARY KEY (id);


--
-- Name: email_verification_request email_verification_request_user_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY email_verification_request
    ADD CONSTRAINT email_verification_request_user_id_key UNIQUE (user_id);


--
-- Name: employee_monthly_culture_shift employee_monthly_culture_shift_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY employee_monthly_culture_shift
    ADD CONSTRAINT employee_monthly_culture_shift_pkey PRIMARY KEY (id);


--
-- Name: employee employee_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY employee
    ADD CONSTRAINT employee_pkey PRIMARY KEY (user_id);


--
-- Name: estimate estimate_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY estimate
    ADD CONSTRAINT estimate_pkey PRIMARY KEY (id);


--
-- Name: eta_prediction eta_prediction_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY eta_prediction
    ADD CONSTRAINT eta_prediction_pkey PRIMARY KEY (id);


--
-- Name: experiment2 experiment2_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY experiment2
    ADD CONSTRAINT experiment2_name_key UNIQUE (name);


--
-- Name: experiment2 experiment2_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY experiment2
    ADD CONSTRAINT experiment2_pkey PRIMARY KEY (id);


--
-- Name: experiment_bucket_assignment experiment_bucket_assign_user_id_experiment_id_8db1c8f5_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY experiment_bucket_assignment
    ADD CONSTRAINT experiment_bucket_assign_user_id_experiment_id_8db1c8f5_uniq UNIQUE (user_id, experiment_id);


--
-- Name: experiment_bucket_assignment experiment_bucket_assignment_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY experiment_bucket_assignment
    ADD CONSTRAINT experiment_bucket_assignment_pkey PRIMARY KEY (id);


--
-- Name: experiment_distribution experiment_distribution_experiment_id_identifier_cbca4dc1_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY experiment_distribution
    ADD CONSTRAINT experiment_distribution_experiment_id_identifier_cbca4dc1_uniq UNIQUE (experiment_id, identifier);


--
-- Name: experiment_distribution experiment_distribution_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY experiment_distribution
    ADD CONSTRAINT experiment_distribution_pkey PRIMARY KEY (id);


--
-- Name: experiment_override experiment_override_experiment_id_user_id_52518733_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY experiment_override
    ADD CONSTRAINT experiment_override_experiment_id_user_id_52518733_uniq UNIQUE (experiment_id, user_id);


--
-- Name: experiment_override experiment_override_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY experiment_override
    ADD CONSTRAINT experiment_override_pkey PRIMARY KEY (id);


--
-- Name: experiment experiment_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY experiment
    ADD CONSTRAINT experiment_pkey PRIMARY KEY (id);


--
-- Name: experiment_user experiment_user_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY experiment_user
    ADD CONSTRAINT experiment_user_pkey PRIMARY KEY (id);


--
-- Name: experiment_user experiment_user_user_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY experiment_user
    ADD CONSTRAINT experiment_user_user_id_key UNIQUE (user_id);


--
-- Name: experiment_version experiment_version_experiment_id_version_7d3eb4e0_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY experiment_version
    ADD CONSTRAINT experiment_version_experiment_id_version_7d3eb4e0_uniq UNIQUE (experiment_id, version);


--
-- Name: experiment_version experiment_version_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY experiment_version
    ADD CONSTRAINT experiment_version_pkey PRIMARY KEY (id);


--
-- Name: external_request external_request_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY external_request
    ADD CONSTRAINT external_request_pkey PRIMARY KEY (id);


--
-- Name: fraud_status fraud_status_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY fraud_status
    ADD CONSTRAINT fraud_status_pkey PRIMARY KEY (id);


--
-- Name: free_delivery_promotion free_delivery_promotion_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY free_delivery_promotion
    ADD CONSTRAINT free_delivery_promotion_pkey PRIMARY KEY (id);


--
-- Name: gift_code gift_code_code_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY gift_code
    ADD CONSTRAINT gift_code_code_key UNIQUE (code);


--
-- Name: gift_code gift_code_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY gift_code
    ADD CONSTRAINT gift_code_pkey PRIMARY KEY (id);


--
-- Name: github_activity_metrics github_activity_metrics_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY github_activity_metrics
    ADD CONSTRAINT github_activity_metrics_pkey PRIMARY KEY (id);


--
-- Name: globalvars_gatekeeper globalvars_gatekeeper_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY globalvars_gatekeeper
    ADD CONSTRAINT globalvars_gatekeeper_pkey PRIMARY KEY (name);


--
-- Name: globalvars_variable globalvars_variable_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY globalvars_variable
    ADD CONSTRAINT globalvars_variable_pkey PRIMARY KEY (key);


--
-- Name: grab_pay_account grab_pay_account_consumer_id_bind_token_c1a55415_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY grab_pay_account
    ADD CONSTRAINT grab_pay_account_consumer_id_bind_token_c1a55415_uniq UNIQUE (consumer_id, bind_token);


--
-- Name: grab_pay_account grab_pay_account_idempotency_key_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY grab_pay_account
    ADD CONSTRAINT grab_pay_account_idempotency_key_key UNIQUE (idempotency_key);


--
-- Name: grab_pay_account grab_pay_account_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY grab_pay_account
    ADD CONSTRAINT grab_pay_account_pkey PRIMARY KEY (id);


--
-- Name: grab_pay_charge grab_pay_charge_idempotency_key_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY grab_pay_charge
    ADD CONSTRAINT grab_pay_charge_idempotency_key_key UNIQUE (idempotency_key);


--
-- Name: grab_pay_charge grab_pay_charge_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY grab_pay_charge
    ADD CONSTRAINT grab_pay_charge_pkey PRIMARY KEY (id);


--
-- Name: grab_payment_account grab_payment_account_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY grab_payment_account
    ADD CONSTRAINT grab_payment_account_pkey PRIMARY KEY (id);


--
-- Name: grab_transfer grab_transfer_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY grab_transfer
    ADD CONSTRAINT grab_transfer_pkey PRIMARY KEY (id);


--
-- Name: guest_user_type guest_user_type_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY guest_user_type
    ADD CONSTRAINT guest_user_type_pkey PRIMARY KEY (id);


--
-- Name: invoicing_group_membership invoicing_group_membership_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY invoicing_group_membership
    ADD CONSTRAINT invoicing_group_membership_pkey PRIMARY KEY (id);


--
-- Name: invoicing_group_membership invoicing_group_membership_store_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY invoicing_group_membership
    ADD CONSTRAINT invoicing_group_membership_store_id_key UNIQUE (store_id);


--
-- Name: invoicing_group_onboarding_rule invoicing_group_onboardi_entity_type_entity_id_ebe67897_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY invoicing_group_onboarding_rule
    ADD CONSTRAINT invoicing_group_onboardi_entity_type_entity_id_ebe67897_uniq UNIQUE (entity_type, entity_id);


--
-- Name: invoicing_group_onboarding_rule invoicing_group_onboarding_rule_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY invoicing_group_onboarding_rule
    ADD CONSTRAINT invoicing_group_onboarding_rule_pkey PRIMARY KEY (id);


--
-- Name: invoicing_group invoicing_group_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY invoicing_group
    ADD CONSTRAINT invoicing_group_pkey PRIMARY KEY (id);


--
-- Name: ios_notifications_apnservice ios_notifications_apnservice_name_hostname_4f159a73_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY ios_notifications_apnservice
    ADD CONSTRAINT ios_notifications_apnservice_name_hostname_4f159a73_uniq UNIQUE (name, hostname);


--
-- Name: ios_notifications_apnservice ios_notifications_apnservice_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY ios_notifications_apnservice
    ADD CONSTRAINT ios_notifications_apnservice_pkey PRIMARY KEY (id);


--
-- Name: ios_notifications_device ios_notifications_device_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY ios_notifications_device
    ADD CONSTRAINT ios_notifications_device_pkey PRIMARY KEY (id);


--
-- Name: ios_notifications_device ios_notifications_device_token_service_id_4f22986c_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY ios_notifications_device
    ADD CONSTRAINT ios_notifications_device_token_service_id_4f22986c_uniq UNIQUE (token, service_id);


--
-- Name: ios_notifications_device_users ios_notifications_device_users_device_id_user_id_489de4dc_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY ios_notifications_device_users
    ADD CONSTRAINT ios_notifications_device_users_device_id_user_id_489de4dc_uniq UNIQUE (device_id, user_id);


--
-- Name: ios_notifications_device_users ios_notifications_device_users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY ios_notifications_device_users
    ADD CONSTRAINT ios_notifications_device_users_pkey PRIMARY KEY (id);


--
-- Name: ios_notifications_feedbackservice ios_notifications_feedbackservice_name_hostname_2e283cf4_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY ios_notifications_feedbackservice
    ADD CONSTRAINT ios_notifications_feedbackservice_name_hostname_2e283cf4_uniq UNIQUE (name, hostname);


--
-- Name: ios_notifications_feedbackservice ios_notifications_feedbackservice_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY ios_notifications_feedbackservice
    ADD CONSTRAINT ios_notifications_feedbackservice_pkey PRIMARY KEY (id);


--
-- Name: ios_notifications_notification ios_notifications_notification_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY ios_notifications_notification
    ADD CONSTRAINT ios_notifications_notification_pkey PRIMARY KEY (id);


--
-- Name: kill_switch_interval kill_switch_interval_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY kill_switch_interval
    ADD CONSTRAINT kill_switch_interval_pkey PRIMARY KEY (id);


--
-- Name: managed_account_transfer managed_account_transfer_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY managed_account_transfer
    ADD CONSTRAINT managed_account_transfer_pkey PRIMARY KEY (id);


--
-- Name: managed_account_transfer managed_account_transfer_transfer_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY managed_account_transfer
    ADD CONSTRAINT managed_account_transfer_transfer_id_key UNIQUE (transfer_id);


--
-- Name: market market_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY market
    ADD CONSTRAINT market_name_key UNIQUE (name);


--
-- Name: market market_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY market
    ADD CONSTRAINT market_pkey PRIMARY KEY (id);


--
-- Name: market market_shortname_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY market
    ADD CONSTRAINT market_shortname_key UNIQUE (shortname);


--
-- Name: market_special_hours market_special_hours_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY market_special_hours
    ADD CONSTRAINT market_special_hours_pkey PRIMARY KEY (id);


--
-- Name: marqeta_card_ownership marqeta_card_ownership_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY marqeta_card_ownership
    ADD CONSTRAINT marqeta_card_ownership_pkey PRIMARY KEY (id);


--
-- Name: marqeta_card marqeta_card_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY marqeta_card
    ADD CONSTRAINT marqeta_card_pkey PRIMARY KEY (token);


--
-- Name: marqeta_card_transition marqeta_card_transition_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY marqeta_card_transition
    ADD CONSTRAINT marqeta_card_transition_pkey PRIMARY KEY (id);


--
-- Name: marqeta_decline_exemption marqeta_decline_exemption_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY marqeta_decline_exemption
    ADD CONSTRAINT marqeta_decline_exemption_pkey PRIMARY KEY (id);


--
-- Name: marqeta_transaction_event marqeta_transaction_event_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY marqeta_transaction_event
    ADD CONSTRAINT marqeta_transaction_event_pkey PRIMARY KEY (id);


--
-- Name: marqeta_transaction_event marqeta_transaction_event_token_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY marqeta_transaction_event
    ADD CONSTRAINT marqeta_transaction_event_token_key UNIQUE (token);


--
-- Name: marqeta_transaction marqeta_transaction_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY marqeta_transaction
    ADD CONSTRAINT marqeta_transaction_pkey PRIMARY KEY (id);


--
-- Name: marqeta_transaction marqeta_transaction_token_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY marqeta_transaction
    ADD CONSTRAINT marqeta_transaction_token_key UNIQUE (token);


--
-- Name: mass_communication_status mass_communication_status_message_uuid_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY mass_communication_status
    ADD CONSTRAINT mass_communication_status_message_uuid_key UNIQUE (message_uuid);


--
-- Name: mass_communication_status mass_communication_status_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY mass_communication_status
    ADD CONSTRAINT mass_communication_status_pkey PRIMARY KEY (id);


--
-- Name: multi_promotion multi_promotion_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY multi_promotion
    ADD CONSTRAINT multi_promotion_pkey PRIMARY KEY (id);


--
-- Name: order_cart_consumer_promotion_link order_cart_consumer_prom_order_cart_id_consumer_p_a8333afc_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY order_cart_consumer_promotion_link
    ADD CONSTRAINT order_cart_consumer_prom_order_cart_id_consumer_p_a8333afc_uniq UNIQUE (order_cart_id, consumer_promotion_id);


--
-- Name: order_cart_consumer_promotion_link order_cart_consumer_promotion_link_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY order_cart_consumer_promotion_link
    ADD CONSTRAINT order_cart_consumer_promotion_link_pkey PRIMARY KEY (id);


--
-- Name: order_cart_device_fingerprint_link order_cart_device_finger_order_cart_id_fingerprin_c55c1195_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY order_cart_device_fingerprint_link
    ADD CONSTRAINT order_cart_device_finger_order_cart_id_fingerprin_c55c1195_uniq UNIQUE (order_cart_id, fingerprint_id, source);


--
-- Name: order_cart_device_fingerprint_link order_cart_device_fingerprint_link_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY order_cart_device_fingerprint_link
    ADD CONSTRAINT order_cart_device_fingerprint_link_pkey PRIMARY KEY (id);


--
-- Name: order_cart_discount_component order_cart_discount_comp_order_cart_id_store_orde_40541022_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY order_cart_discount_component
    ADD CONSTRAINT order_cart_discount_comp_order_cart_id_store_orde_40541022_uniq UNIQUE (order_cart_id, store_order_cart_id, monetary_field, source_type_id, "group");


--
-- Name: order_cart_discount_component order_cart_discount_component_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY order_cart_discount_component
    ADD CONSTRAINT order_cart_discount_component_pkey PRIMARY KEY (id);


--
-- Name: order_cart_discount_component_source_type order_cart_discount_component_source_type_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY order_cart_discount_component_source_type
    ADD CONSTRAINT order_cart_discount_component_source_type_name_key UNIQUE (name);


--
-- Name: order_cart_discount_component_source_type order_cart_discount_component_source_type_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY order_cart_discount_component_source_type
    ADD CONSTRAINT order_cart_discount_component_source_type_pkey PRIMARY KEY (id);


--
-- Name: order_cart_discount order_cart_discount_order_cart_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY order_cart_discount
    ADD CONSTRAINT order_cart_discount_order_cart_id_key UNIQUE (order_cart_id);


--
-- Name: order_cart_discount order_cart_discount_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY order_cart_discount
    ADD CONSTRAINT order_cart_discount_pkey PRIMARY KEY (id);


--
-- Name: order_cart_escalation order_cart_escalation_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY order_cart_escalation
    ADD CONSTRAINT order_cart_escalation_pkey PRIMARY KEY (order_cart_id);


--
-- Name: order_cart_escalation_reason order_cart_escalation_reason_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY order_cart_escalation_reason
    ADD CONSTRAINT order_cart_escalation_reason_pkey PRIMARY KEY (id);


--
-- Name: order_cart_escalation order_cart_escalation_stripe_charge_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY order_cart_escalation
    ADD CONSTRAINT order_cart_escalation_stripe_charge_id_key UNIQUE (stripe_charge_id);


--
-- Name: order_cart order_cart_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY order_cart
    ADD CONSTRAINT order_cart_pkey PRIMARY KEY (id);


--
-- Name: order_cart_pricing_strategy order_cart_pricing_strategy_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY order_cart_pricing_strategy
    ADD CONSTRAINT order_cart_pricing_strategy_pkey PRIMARY KEY (id);


--
-- Name: order_cart_pricing_strategy order_cart_pricing_strategy_strategy_type_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY order_cart_pricing_strategy
    ADD CONSTRAINT order_cart_pricing_strategy_strategy_type_key UNIQUE (strategy_type);


--
-- Name: order_cart order_cart_url_code_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY order_cart
    ADD CONSTRAINT order_cart_url_code_key UNIQUE (url_code);


--
-- Name: order_item_extra_option order_item_extra_option_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY order_item_extra_option
    ADD CONSTRAINT order_item_extra_option_pkey PRIMARY KEY (id);


--
-- Name: order_item order_item_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY order_item
    ADD CONSTRAINT order_item_pkey PRIMARY KEY (id);


--
-- Name: order_menu_option order_menu_option_order_id_option_id_b1642d9c_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY order_menu_option
    ADD CONSTRAINT order_menu_option_order_id_option_id_b1642d9c_uniq UNIQUE (order_id, option_id);


--
-- Name: order_menu_option order_menu_option_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY order_menu_option
    ADD CONSTRAINT order_menu_option_pkey PRIMARY KEY (id);


--
-- Name: order order_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY "order"
    ADD CONSTRAINT order_pkey PRIMARY KEY (id);


--
-- Name: order_placer_queue_state order_placer_queue_state_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY order_placer_queue_state
    ADD CONSTRAINT order_placer_queue_state_pkey PRIMARY KEY (id);


--
-- Name: payment_account payment_account_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY payment_account
    ADD CONSTRAINT payment_account_pkey PRIMARY KEY (id);


--
-- Name: payment_method payment_method_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY payment_method
    ADD CONSTRAINT payment_method_pkey PRIMARY KEY (id);


--
-- Name: percentage_promotion percentage_promotion_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY percentage_promotion
    ADD CONSTRAINT percentage_promotion_pkey PRIMARY KEY (id);


--
-- Name: place_tag place_tag_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY place_tag
    ADD CONSTRAINT place_tag_name_key UNIQUE (name);


--
-- Name: place_tag place_tag_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY place_tag
    ADD CONSTRAINT place_tag_pkey PRIMARY KEY (id);


--
-- Name: platform platform_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY platform
    ADD CONSTRAINT platform_pkey PRIMARY KEY (id);


--
-- Name: price_transparency_bucket_assignments price_transparency_bucket_assignments_consumer_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY price_transparency_bucket_assignments
    ADD CONSTRAINT price_transparency_bucket_assignments_consumer_id_key UNIQUE (consumer_id);


--
-- Name: price_transparency_bucket_assignments price_transparency_bucket_assignments_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY price_transparency_bucket_assignments
    ADD CONSTRAINT price_transparency_bucket_assignments_pkey PRIMARY KEY (id);


--
-- Name: promo_code promo_code_code_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY promo_code
    ADD CONSTRAINT promo_code_code_key UNIQUE (code);


--
-- Name: promo_code_consumer_link promo_code_consumer_link_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY promo_code_consumer_link
    ADD CONSTRAINT promo_code_consumer_link_pkey PRIMARY KEY (id);


--
-- Name: promo_code_markets promo_code_markets_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY promo_code_markets
    ADD CONSTRAINT promo_code_markets_pkey PRIMARY KEY (id);


--
-- Name: promo_code_markets promo_code_markets_promocode_id_market_id_5d2b71b1_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY promo_code_markets
    ADD CONSTRAINT promo_code_markets_promocode_id_market_id_5d2b71b1_uniq UNIQUE (promocode_id, market_id);


--
-- Name: promo_code promo_code_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY promo_code
    ADD CONSTRAINT promo_code_pkey PRIMARY KEY (id);


--
-- Name: promo_code_submarket_link promo_code_submarket_lin_promo_code_id_submarket__24f09685_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY promo_code_submarket_link
    ADD CONSTRAINT promo_code_submarket_lin_promo_code_id_submarket__24f09685_uniq UNIQUE (promo_code_id, submarket_id);


--
-- Name: promo_code_submarket_link promo_code_submarket_link_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY promo_code_submarket_link
    ADD CONSTRAINT promo_code_submarket_link_pkey PRIMARY KEY (id);


--
-- Name: promotion_consumer_link promotion_consumer_link_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY promotion_consumer_link
    ADD CONSTRAINT promotion_consumer_link_pkey PRIMARY KEY (id);


--
-- Name: promotion_consumer_link promotion_consumer_link_promotion_id_consumer_id_c3a2af2a_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY promotion_consumer_link
    ADD CONSTRAINT promotion_consumer_link_promotion_id_consumer_id_c3a2af2a_uniq UNIQUE (promotion_id, consumer_id);


--
-- Name: promotion_featured_location_link promotion_featured_locat_promotion_id_featured_lo_5aa6aba7_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY promotion_featured_location_link
    ADD CONSTRAINT promotion_featured_locat_promotion_id_featured_lo_5aa6aba7_uniq UNIQUE (promotion_id, featured_location_id);


--
-- Name: promotion_featured_location_link promotion_featured_location_link_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY promotion_featured_location_link
    ADD CONSTRAINT promotion_featured_location_link_pkey PRIMARY KEY (id);


--
-- Name: promotion_place_tag_link promotion_place_tag_link_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY promotion_place_tag_link
    ADD CONSTRAINT promotion_place_tag_link_pkey PRIMARY KEY (id);


--
-- Name: promotion_place_tag_link promotion_place_tag_link_promotion_id_place_tag_i_c09481dc_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY promotion_place_tag_link
    ADD CONSTRAINT promotion_place_tag_link_promotion_id_place_tag_i_c09481dc_uniq UNIQUE (promotion_id, place_tag_id);


--
-- Name: promotion_redemption_event promotion_redemption_event_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY promotion_redemption_event
    ADD CONSTRAINT promotion_redemption_event_pkey PRIMARY KEY (id);


--
-- Name: promotion_submarket_link promotion_submarket_link_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY promotion_submarket_link
    ADD CONSTRAINT promotion_submarket_link_pkey PRIMARY KEY (id);


--
-- Name: promotion_submarket_link promotion_submarket_link_promotion_id_submarket_i_56d6cafa_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY promotion_submarket_link
    ADD CONSTRAINT promotion_submarket_link_promotion_id_submarket_i_56d6cafa_uniq UNIQUE (promotion_id, submarket_id);


--
-- Name: promotions_featured_location promotions_featured_location_name_e5582676_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY promotions_featured_location
    ADD CONSTRAINT promotions_featured_location_name_e5582676_uniq UNIQUE (name);


--
-- Name: promotions_featured_location promotions_featured_location_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY promotions_featured_location
    ADD CONSTRAINT promotions_featured_location_pkey PRIMARY KEY (id);


--
-- Name: real_time_supply_model real_time_supply_model_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY real_time_supply_model
    ADD CONSTRAINT real_time_supply_model_pkey PRIMARY KEY (id);


--
-- Name: real_time_supply_prediction real_time_supply_prediction_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY real_time_supply_prediction
    ADD CONSTRAINT real_time_supply_prediction_pkey PRIMARY KEY (id);


--
-- Name: realtime_demand_evaluation realtime_demand_evaluati_starting_point_id_active_c6961f1a_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY realtime_demand_evaluation
    ADD CONSTRAINT realtime_demand_evaluati_starting_point_id_active_c6961f1a_uniq UNIQUE (starting_point_id, active_date);


--
-- Name: realtime_demand_evaluation realtime_demand_evaluation_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY realtime_demand_evaluation
    ADD CONSTRAINT realtime_demand_evaluation_pkey PRIMARY KEY (id);


--
-- Name: referral_programs referral_programs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY referral_programs
    ADD CONSTRAINT referral_programs_pkey PRIMARY KEY (id);


--
-- Name: refresh_token refresh_token_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY refresh_token
    ADD CONSTRAINT refresh_token_pkey PRIMARY KEY (key);


--
-- Name: refresh_token refresh_token_user_id_app_336348f6_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY refresh_token
    ADD CONSTRAINT refresh_token_user_id_app_336348f6_uniq UNIQUE (user_id, app);


--
-- Name: region region_country_id_name_92becb4f_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY region
    ADD CONSTRAINT region_country_id_name_92becb4f_uniq UNIQUE (country_id, name);


--
-- Name: region region_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY region
    ADD CONSTRAINT region_pkey PRIMARY KEY (id);


--
-- Name: region region_shortname_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY region
    ADD CONSTRAINT region_shortname_key UNIQUE (shortname);


--
-- Name: region_snapshot region_snapshot_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY region_snapshot
    ADD CONSTRAINT region_snapshot_pkey PRIMARY KEY (id);


--
-- Name: scheduled_caps_boost scheduled_caps_boost_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY scheduled_caps_boost
    ADD CONSTRAINT scheduled_caps_boost_pkey PRIMARY KEY (id);


--
-- Name: search_engine_store_feed search_engine_store_feed_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY search_engine_store_feed
    ADD CONSTRAINT search_engine_store_feed_pkey PRIMARY KEY (id);


--
-- Name: search_engine_store_feed search_engine_store_feed_store_id_search_engine_f4545fd7_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY search_engine_store_feed
    ADD CONSTRAINT search_engine_store_feed_store_id_search_engine_f4545fd7_uniq UNIQUE (store_id, search_engine);


--
-- Name: seo_local_region seo_local_region_city_id_name_60f14a28_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY seo_local_region
    ADD CONSTRAINT seo_local_region_city_id_name_60f14a28_uniq UNIQUE (city_id, name);


--
-- Name: seo_local_region seo_local_region_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY seo_local_region
    ADD CONSTRAINT seo_local_region_pkey PRIMARY KEY (id);


--
-- Name: shortened_url shortened_url_expanded_url_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY shortened_url
    ADD CONSTRAINT shortened_url_expanded_url_key UNIQUE (expanded_url);


--
-- Name: shortened_url shortened_url_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY shortened_url
    ADD CONSTRAINT shortened_url_pkey PRIMARY KEY (id);


--
-- Name: shortened_url shortened_url_url_code_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY shortened_url
    ADD CONSTRAINT shortened_url_url_code_key UNIQUE (url_code);


--
-- Name: sms_help_message_status sms_help_message_status_phone_number_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY sms_help_message_status
    ADD CONSTRAINT sms_help_message_status_phone_number_key UNIQUE (phone_number);


--
-- Name: sms_help_message_status sms_help_message_status_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY sms_help_message_status
    ADD CONSTRAINT sms_help_message_status_pkey PRIMARY KEY (id);


--
-- Name: sms_opt_out_number sms_opt_out_number_phone_number_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY sms_opt_out_number
    ADD CONSTRAINT sms_opt_out_number_phone_number_key UNIQUE (phone_number);


--
-- Name: sms_opt_out_number sms_opt_out_number_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY sms_opt_out_number
    ADD CONSTRAINT sms_opt_out_number_pkey PRIMARY KEY (id);


--
-- Name: starship_delivery_info starship_delivery_info_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY starship_delivery_info
    ADD CONSTRAINT starship_delivery_info_pkey PRIMARY KEY (id);


--
-- Name: starship_delivery_info starship_delivery_info_tracking_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY starship_delivery_info
    ADD CONSTRAINT starship_delivery_info_tracking_key UNIQUE (tracking);


--
-- Name: starting_point_assignment_latency_stats starting_point_assignmen_active_date_starting_poi_46399105_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY starting_point_assignment_latency_stats
    ADD CONSTRAINT starting_point_assignmen_active_date_starting_poi_46399105_uniq UNIQUE (active_date, starting_point_id);


--
-- Name: starting_point_assignment_latency_stats starting_point_assignment_latency_stats_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY starting_point_assignment_latency_stats
    ADD CONSTRAINT starting_point_assignment_latency_stats_pkey PRIMARY KEY (id);


--
-- Name: starting_point_batching_parameters starting_point_batching_parameters_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY starting_point_batching_parameters
    ADD CONSTRAINT starting_point_batching_parameters_pkey PRIMARY KEY (id);


--
-- Name: starting_point_batching_parameters starting_point_batching_parameters_starting_point_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY starting_point_batching_parameters
    ADD CONSTRAINT starting_point_batching_parameters_starting_point_id_key UNIQUE (starting_point_id);


--
-- Name: starting_point_delivery_duration_stats starting_point_delivery__active_date_starting_poi_3f3c2545_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY starting_point_delivery_duration_stats
    ADD CONSTRAINT starting_point_delivery__active_date_starting_poi_3f3c2545_uniq UNIQUE (active_date, starting_point_id);


--
-- Name: starting_point_delivery_duration_stats starting_point_delivery_duration_stats_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY starting_point_delivery_duration_stats
    ADD CONSTRAINT starting_point_delivery_duration_stats_pkey PRIMARY KEY (id);


--
-- Name: starting_point_delivery_hours starting_point_delivery_hours_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY starting_point_delivery_hours
    ADD CONSTRAINT starting_point_delivery_hours_pkey PRIMARY KEY (id);


--
-- Name: starting_point_flf_thresholds starting_point_flf_thresholds_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY starting_point_flf_thresholds
    ADD CONSTRAINT starting_point_flf_thresholds_pkey PRIMARY KEY (id);


--
-- Name: starting_point_flf_thresholds starting_point_flf_thresholds_starting_point_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY starting_point_flf_thresholds
    ADD CONSTRAINT starting_point_flf_thresholds_starting_point_id_key UNIQUE (starting_point_id);


--
-- Name: starting_point_geometry starting_point_geometry_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY starting_point_geometry
    ADD CONSTRAINT starting_point_geometry_pkey PRIMARY KEY (starting_point_id);


--
-- Name: starting_point starting_point_html_color_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY starting_point
    ADD CONSTRAINT starting_point_html_color_key UNIQUE (html_color);


--
-- Name: starting_point starting_point_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY starting_point
    ADD CONSTRAINT starting_point_pkey PRIMARY KEY (id);


--
-- Name: starting_point_r2c_stats starting_point_r2c_stats_active_date_starting_poi_48173e40_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY starting_point_r2c_stats
    ADD CONSTRAINT starting_point_r2c_stats_active_date_starting_poi_48173e40_uniq UNIQUE (active_date, starting_point_id);


--
-- Name: starting_point_r2c_stats starting_point_r2c_stats_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY starting_point_r2c_stats
    ADD CONSTRAINT starting_point_r2c_stats_pkey PRIMARY KEY (id);


--
-- Name: starting_point_set starting_point_set_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY starting_point_set
    ADD CONSTRAINT starting_point_set_pkey PRIMARY KEY (id);


--
-- Name: starting_point_set starting_point_set_starting_point_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY starting_point_set
    ADD CONSTRAINT starting_point_set_starting_point_id_key UNIQUE (starting_point_id);


--
-- Name: starting_point starting_point_shortname_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY starting_point
    ADD CONSTRAINT starting_point_shortname_key UNIQUE (shortname);


--
-- Name: store_confirmed_time_snapshot store_confirmed_time_snapshot_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY store_confirmed_time_snapshot
    ADD CONSTRAINT store_confirmed_time_snapshot_pkey PRIMARY KEY (id);


--
-- Name: store_consumer_review store_consumer_review_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY store_consumer_review
    ADD CONSTRAINT store_consumer_review_pkey PRIMARY KEY (id);


--
-- Name: store_consumer_review_tag_link store_consumer_review_tag_link_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY store_consumer_review_tag_link
    ADD CONSTRAINT store_consumer_review_tag_link_pkey PRIMARY KEY (id);


--
-- Name: store_consumer_review_tag_link store_consumer_review_tag_link_review_id_tag_id_0314f1a2_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY store_consumer_review_tag_link
    ADD CONSTRAINT store_consumer_review_tag_link_review_id_tag_id_0314f1a2_uniq UNIQUE (review_id, tag_id);


--
-- Name: store_consumer_review_tag store_consumer_review_tag_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY store_consumer_review_tag
    ADD CONSTRAINT store_consumer_review_tag_name_key UNIQUE (name);


--
-- Name: store_consumer_review_tag store_consumer_review_tag_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY store_consumer_review_tag
    ADD CONSTRAINT store_consumer_review_tag_pkey PRIMARY KEY (id);


--
-- Name: store_delivery_duration_stats store_delivery_duration__active_date_store_id_670bc720_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY store_delivery_duration_stats
    ADD CONSTRAINT store_delivery_duration__active_date_store_id_670bc720_uniq UNIQUE (active_date, store_id);


--
-- Name: store_delivery_duration_stats store_delivery_duration_stats_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY store_delivery_duration_stats
    ADD CONSTRAINT store_delivery_duration_stats_pkey PRIMARY KEY (id);


--
-- Name: store_mastercard_data store_mastercard_data_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY store_mastercard_data
    ADD CONSTRAINT store_mastercard_data_pkey PRIMARY KEY (id);


--
-- Name: store_netsuite_customer_link store_netsuite_customer_link_netsuite_entity_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY store_netsuite_customer_link
    ADD CONSTRAINT store_netsuite_customer_link_netsuite_entity_id_key UNIQUE (netsuite_entity_id);


--
-- Name: store_netsuite_customer_link store_netsuite_customer_link_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY store_netsuite_customer_link
    ADD CONSTRAINT store_netsuite_customer_link_pkey PRIMARY KEY (store_id);


--
-- Name: store_order_cart store_order_cart_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY store_order_cart
    ADD CONSTRAINT store_order_cart_pkey PRIMARY KEY (id);


--
-- Name: store_order_place_latency_stats store_order_place_latenc_active_date_store_id_2531c788_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY store_order_place_latency_stats
    ADD CONSTRAINT store_order_place_latenc_active_date_store_id_2531c788_uniq UNIQUE (active_date, store_id);


--
-- Name: store_order_place_latency_stats store_order_place_latency_stats_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY store_order_place_latency_stats
    ADD CONSTRAINT store_order_place_latency_stats_pkey PRIMARY KEY (id);


--
-- Name: store_point_of_sale_transaction store_point_of_sale_transaction_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY store_point_of_sale_transaction
    ADD CONSTRAINT store_point_of_sale_transaction_pkey PRIMARY KEY (delivery_id);


--
-- Name: stripe_bank_account stripe_bank_account_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY stripe_bank_account
    ADD CONSTRAINT stripe_bank_account_pkey PRIMARY KEY (id);


--
-- Name: stripe_bank_account stripe_bank_account_stripe_id_account_holder_9dcc496b_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY stripe_bank_account
    ADD CONSTRAINT stripe_bank_account_stripe_id_account_holder_9dcc496b_uniq UNIQUE (stripe_id, account_holder_name, fingerprint, last4);


--
-- Name: stripe_card stripe_card_consumer_id_fingerprint__89a36c3f_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY stripe_card
    ADD CONSTRAINT stripe_card_consumer_id_fingerprint__89a36c3f_uniq UNIQUE (consumer_id, fingerprint, exp_year, exp_month, stripe_id);


--
-- Name: stripe_card_event stripe_card_event_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY stripe_card_event
    ADD CONSTRAINT stripe_card_event_pkey PRIMARY KEY (id);


--
-- Name: stripe_card stripe_card_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY stripe_card
    ADD CONSTRAINT stripe_card_pkey PRIMARY KEY (id);


--
-- Name: stripe_card stripe_card_stripe_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY stripe_card
    ADD CONSTRAINT stripe_card_stripe_id_key UNIQUE (stripe_id);


--
-- Name: stripe_charge stripe_charge_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY stripe_charge
    ADD CONSTRAINT stripe_charge_pkey PRIMARY KEY (id);


--
-- Name: stripe_customer stripe_customer_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY stripe_customer
    ADD CONSTRAINT stripe_customer_pkey PRIMARY KEY (id);


--
-- Name: stripe_dispute stripe_dispute_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY stripe_dispute
    ADD CONSTRAINT stripe_dispute_pkey PRIMARY KEY (id);


--
-- Name: stripe_dispute stripe_dispute_stripe_dispute_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY stripe_dispute
    ADD CONSTRAINT stripe_dispute_stripe_dispute_id_key UNIQUE (stripe_dispute_id);


--
-- Name: stripe_managed_account stripe_managed_account_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY stripe_managed_account
    ADD CONSTRAINT stripe_managed_account_pkey PRIMARY KEY (id);


--
-- Name: stripe_recipient stripe_recipient_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY stripe_recipient
    ADD CONSTRAINT stripe_recipient_pkey PRIMARY KEY (id);


--
-- Name: stripe_transfer stripe_transfer_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY stripe_transfer
    ADD CONSTRAINT stripe_transfer_pkey PRIMARY KEY (id);


--
-- Name: submarket submarket_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY submarket
    ADD CONSTRAINT submarket_name_key UNIQUE (name);


--
-- Name: submarket submarket_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY submarket
    ADD CONSTRAINT submarket_pkey PRIMARY KEY (id);


--
-- Name: submarket submarket_slug_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY submarket
    ADD CONSTRAINT submarket_slug_key UNIQUE (slug);


--
-- Name: subnational_division subnational_division_country_id_name_3680da79_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY subnational_division
    ADD CONSTRAINT subnational_division_country_id_name_3680da79_uniq UNIQUE (country_id, name);


--
-- Name: subnational_division subnational_division_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY subnational_division
    ADD CONSTRAINT subnational_division_pkey PRIMARY KEY (id);


--
-- Name: subnational_division subnational_division_shortname_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY subnational_division
    ADD CONSTRAINT subnational_division_shortname_key UNIQUE (shortname);


--
-- Name: support_delivery_banner support_delivery_banner_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY support_delivery_banner
    ADD CONSTRAINT support_delivery_banner_pkey PRIMARY KEY (id);


--
-- Name: support_salesforce_case_record support_salesforce_case_record_case_number_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY support_salesforce_case_record
    ADD CONSTRAINT support_salesforce_case_record_case_number_key UNIQUE (case_number);


--
-- Name: support_salesforce_case_record support_salesforce_case_record_case_uid_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY support_salesforce_case_record
    ADD CONSTRAINT support_salesforce_case_record_case_uid_key UNIQUE (case_uid);


--
-- Name: support_salesforce_case_record support_salesforce_case_record_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY support_salesforce_case_record
    ADD CONSTRAINT support_salesforce_case_record_pkey PRIMARY KEY (id);


--
-- Name: transfer transfer_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY transfer
    ADD CONSTRAINT transfer_pkey PRIMARY KEY (id);


--
-- Name: transfer_submission_lock transfer_submission_lock_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY transfer_submission_lock
    ADD CONSTRAINT transfer_submission_lock_pkey PRIMARY KEY (transfer_id);


--
-- Name: twilio_masking_number_assignment twilio_masking_number_as_twilio_masking_number_id_a5f6ba9d_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY twilio_masking_number_assignment
    ADD CONSTRAINT twilio_masking_number_as_twilio_masking_number_id_a5f6ba9d_uniq UNIQUE (twilio_masking_number_id, delivery_id);


--
-- Name: twilio_masking_number_assignment twilio_masking_number_assignment_delivery_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY twilio_masking_number_assignment
    ADD CONSTRAINT twilio_masking_number_assignment_delivery_id_key UNIQUE (delivery_id);


--
-- Name: twilio_masking_number_assignment twilio_masking_number_assignment_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY twilio_masking_number_assignment
    ADD CONSTRAINT twilio_masking_number_assignment_pkey PRIMARY KEY (id);


--
-- Name: twilio_masking_number twilio_masking_number_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY twilio_masking_number
    ADD CONSTRAINT twilio_masking_number_pkey PRIMARY KEY (id);


--
-- Name: twilio_masking_number twilio_masking_number_twilio_number_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY twilio_masking_number
    ADD CONSTRAINT twilio_masking_number_twilio_number_id_key UNIQUE (twilio_number_id);


--
-- Name: twilio_number twilio_number_phone_sid_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY twilio_number
    ADD CONSTRAINT twilio_number_phone_sid_key UNIQUE (phone_sid);


--
-- Name: twilio_number twilio_number_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY twilio_number
    ADD CONSTRAINT twilio_number_pkey PRIMARY KEY (id);


--
-- Name: user_activation_change_event user_activation_change_event_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY user_activation_change_event
    ADD CONSTRAINT user_activation_change_event_pkey PRIMARY KEY (id);


--
-- Name: user_deactivation_source user_deactivation_source_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY user_deactivation_source
    ADD CONSTRAINT user_deactivation_source_pkey PRIMARY KEY (id);


--
-- Name: user_device_fingerprint_link user_device_fingerprint_link_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY user_device_fingerprint_link
    ADD CONSTRAINT user_device_fingerprint_link_pkey PRIMARY KEY (id);


--
-- Name: user user_email_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY "user"
    ADD CONSTRAINT user_email_key UNIQUE (email);


--
-- Name: user_group_admin  user_group_admin _pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY "user_group_admin "
    ADD CONSTRAINT "user_group_admin _pkey" PRIMARY KEY (id);


--
-- Name: user_groups user_groups_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY user_groups
    ADD CONSTRAINT user_groups_pkey PRIMARY KEY (id);


--
-- Name: user_groups user_groups_user_id_group_id_40beef00_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY user_groups
    ADD CONSTRAINT user_groups_user_id_group_id_40beef00_uniq UNIQUE (user_id, group_id);


--
-- Name: user_locale_preference user_locale_preference_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY user_locale_preference
    ADD CONSTRAINT user_locale_preference_pkey PRIMARY KEY (id);


--
-- Name: user_locale_preference user_locale_preference_user_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY user_locale_preference
    ADD CONSTRAINT user_locale_preference_user_id_key UNIQUE (user_id);


--
-- Name: user user_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY "user"
    ADD CONSTRAINT user_pkey PRIMARY KEY (id);


--
-- Name: user_social_data user_social_data_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY user_social_data
    ADD CONSTRAINT user_social_data_pkey PRIMARY KEY (id);


--
-- Name: user_social_data user_social_data_provider_uid_ca7dea22_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY user_social_data
    ADD CONSTRAINT user_social_data_provider_uid_ca7dea22_uniq UNIQUE (provider, uid);


--
-- Name: user_user_permissions user_user_permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY user_user_permissions
    ADD CONSTRAINT user_user_permissions_pkey PRIMARY KEY (id);


--
-- Name: user_user_permissions user_user_permissions_user_id_permission_id_7dc6e2e0_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY user_user_permissions
    ADD CONSTRAINT user_user_permissions_user_id_permission_id_7dc6e2e0_uniq UNIQUE (user_id, permission_id);


--
-- Name: value_delivery_fee_promotion value_delivery_fee_promotion_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY value_delivery_fee_promotion
    ADD CONSTRAINT value_delivery_fee_promotion_pkey PRIMARY KEY (id);


--
-- Name: value_promotion value_promotion_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY value_promotion
    ADD CONSTRAINT value_promotion_pkey PRIMARY KEY (id);


--
-- Name: vanity_url vanity_url_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY vanity_url
    ADD CONSTRAINT vanity_url_pkey PRIMARY KEY (id);


--
-- Name: vanity_url vanity_url_url_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY vanity_url
    ADD CONSTRAINT vanity_url_url_key UNIQUE (url);


--
-- Name: vehicle_reservation vehicle_reservation_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY vehicle_reservation
    ADD CONSTRAINT vehicle_reservation_pkey PRIMARY KEY (id);


--
-- Name: verification_attempt verification_attempt_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY verification_attempt
    ADD CONSTRAINT verification_attempt_pkey PRIMARY KEY (id);


--
-- Name: version_client version_client_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY version_client
    ADD CONSTRAINT version_client_name_key UNIQUE (name);


--
-- Name: version_client version_client_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY version_client
    ADD CONSTRAINT version_client_pkey PRIMARY KEY (id);


--
-- Name: weather_forecast_model weather_forecast_model_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY weather_forecast_model
    ADD CONSTRAINT weather_forecast_model_pkey PRIMARY KEY (id);


--
-- Name: weather_historical_model weather_historical_model_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY weather_historical_model
    ADD CONSTRAINT weather_historical_model_pkey PRIMARY KEY (id);


--
-- Name: web_deployment web_deployment_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY web_deployment
    ADD CONSTRAINT web_deployment_pkey PRIMARY KEY (id);


--
-- Name: zendesk_template zendesk_template_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY zendesk_template
    ADD CONSTRAINT zendesk_template_pkey PRIMARY KEY (id);


--
-- Name: address_city_6160790c; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX address_city_6160790c ON address USING btree (city);


--
-- Name: address_city_6160790c_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX address_city_6160790c_like ON address USING btree (city varchar_pattern_ops);


--
-- Name: address_formatted_address_dd79a150; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX address_formatted_address_dd79a150 ON address USING btree (formatted_address);


--
-- Name: address_formatted_address_dd79a150_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX address_formatted_address_dd79a150_like ON address USING btree (formatted_address text_pattern_ops);


--
-- Name: address_place_tag_link_address_id_ae51d061; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX address_place_tag_link_address_id_ae51d061 ON address_place_tag_link USING btree (address_id);


--
-- Name: address_place_tag_link_place_tag_id_712329ce; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX address_place_tag_link_place_tag_id_712329ce ON address_place_tag_link USING btree (place_tag_id);


--
-- Name: address_point_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX address_point_id ON address USING gist (point);


--
-- Name: address_zip_code_f34876a0; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX address_zip_code_f34876a0 ON address USING btree (zip_code);


--
-- Name: address_zip_code_f34876a0_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX address_zip_code_f34876a0_like ON address USING btree (zip_code varchar_pattern_ops);


--
-- Name: analytics_dailybusinessmetrics_constants_id_2974c16a; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX analytics_dailybusinessmetrics_constants_id_2974c16a ON analytics_dailybusinessmetrics USING btree (constants_id);


--
-- Name: analytics_dailybusinessmetrics_submarket_id_e1047c59; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX analytics_dailybusinessmetrics_submarket_id_e1047c59 ON analytics_dailybusinessmetrics USING btree (submarket_id);


--
-- Name: analytics_siteoutage_reported_by_id_a2669100; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX analytics_siteoutage_reported_by_id_a2669100 ON analytics_siteoutage USING btree (reported_by_id);


--
-- Name: api_key_key_59dfb287_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_key_key_59dfb287_like ON api_key USING btree (key text_pattern_ops);


--
-- Name: api_key_user_id_2b8305f7; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_key_user_id_2b8305f7 ON api_key USING btree (user_id);


--
-- Name: app_deploy_app_name_c5a46c1f; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX app_deploy_app_name_c5a46c1f ON app_deploy_app USING btree (name);


--
-- Name: app_deploy_app_name_c5a46c1f_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX app_deploy_app_name_c5a46c1f_like ON app_deploy_app USING btree (name varchar_pattern_ops);


--
-- Name: auth_group_name_a6ea08ec_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX auth_group_name_a6ea08ec_like ON auth_group USING btree (name varchar_pattern_ops);


--
-- Name: auth_group_permissions_group_id_b120cbf9; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX auth_group_permissions_group_id_b120cbf9 ON auth_group_permissions USING btree (group_id);


--
-- Name: auth_group_permissions_permission_id_84c5c92e; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX auth_group_permissions_permission_id_84c5c92e ON auth_group_permissions USING btree (permission_id);


--
-- Name: auth_permission_content_type_id_2f476e4b; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX auth_permission_content_type_id_2f476e4b ON auth_permission USING btree (content_type_id);


--
-- Name: authtoken_token_key_10f0b77e_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX authtoken_token_key_10f0b77e_like ON authtoken_token USING btree (key varchar_pattern_ops);


--
-- Name: base_price_sos_event_created_at_25f206a9; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX base_price_sos_event_created_at_25f206a9 ON base_price_sos_event USING btree (created_at);


--
-- Name: base_price_sos_event_created_by_id_a58bf6f5; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX base_price_sos_event_created_by_id_a58bf6f5 ON base_price_sos_event USING btree (created_by_id);


--
-- Name: base_price_sos_event_deactivated_by_id_4171e2ec; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX base_price_sos_event_deactivated_by_id_4171e2ec ON base_price_sos_event USING btree (deactivated_by_id);


--
-- Name: base_price_sos_event_starting_point_id_832e226a; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX base_price_sos_event_starting_point_id_832e226a ON base_price_sos_event USING btree (starting_point_id);


--
-- Name: blacklisted_consumer_address_address_id_51560641; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX blacklisted_consumer_address_address_id_51560641 ON blacklisted_consumer_address USING btree (address_id);


--
-- Name: blacklisted_consumer_address_blacklisted_by_id_14eff977; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX blacklisted_consumer_address_blacklisted_by_id_14eff977 ON blacklisted_consumer_address USING btree (blacklisted_by_id);


--
-- Name: blacklisted_consumer_address_blacklisted_user_id_04605c3b; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX blacklisted_consumer_address_blacklisted_user_id_04605c3b ON blacklisted_consumer_address USING btree (blacklisted_user_id);


--
-- Name: capacity_planning_evaluation_capacity_plan_id_9407e181; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX capacity_planning_evaluation_capacity_plan_id_9407e181 ON capacity_planning_evaluation USING btree (capacity_plan_id);


--
-- Name: capacity_planning_evaluation_starting_point_id_c6cc5e66; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX capacity_planning_evaluation_starting_point_id_c6cc5e66 ON capacity_planning_evaluation USING btree (starting_point_id);


--
-- Name: card_acceptor_blacklisted_by_id_d670df09; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX card_acceptor_blacklisted_by_id_d670df09 ON card_acceptor USING btree (blacklisted_by_id);


--
-- Name: card_acceptor_store_association_card_acceptor_id_dbb4aebc; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX card_acceptor_store_association_card_acceptor_id_dbb4aebc ON card_acceptor_store_association USING btree (card_acceptor_id);


--
-- Name: card_acceptor_store_association_manually_checked_by_id_09ed4c02; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX card_acceptor_store_association_manually_checked_by_id_09ed4c02 ON card_acceptor_store_association USING btree (manually_checked_by_id);


--
-- Name: card_acceptor_store_association_store_id_06d4166e; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX card_acceptor_store_association_store_id_06d4166e ON card_acceptor_store_association USING btree (store_id);


--
-- Name: cash_payment_charge_id_1dfacd37; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX cash_payment_charge_id_1dfacd37 ON cash_payment USING btree (charge_id);


--
-- Name: city_center_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX city_center_id ON city USING gist (center);


--
-- Name: city_market_id_c4f221c6; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX city_market_id_c4f221c6 ON city USING btree (market_id);


--
-- Name: city_shortname_52debd7f_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX city_shortname_52debd7f_like ON city USING btree (shortname varchar_pattern_ops);


--
-- Name: city_submarket_id_fbf91eee; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX city_submarket_id_fbf91eee ON city USING btree (submarket_id);


--
-- Name: communication_preferences__communication_channel_id_6fa91fb7; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX communication_preferences__communication_channel_id_6fa91fb7 ON communication_preferences_channel_link USING btree (communication_channel_id);


--
-- Name: communication_preferences__communication_preferences__d7553f67; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX communication_preferences__communication_preferences__d7553f67 ON communication_preferences_channel_link USING btree (communication_preferences_id);


--
-- Name: compensation_request_approved_by_id_c0af7cfe; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX compensation_request_approved_by_id_c0af7cfe ON compensation_request USING btree (approved_by_id);


--
-- Name: compensation_request_delivery_id_a1cddd8f; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX compensation_request_delivery_id_a1cddd8f ON compensation_request USING btree (delivery_id);


--
-- Name: compensation_request_error_id_f3456ea5; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX compensation_request_error_id_f3456ea5 ON compensation_request USING btree (error_id);


--
-- Name: consumer_account_credits_consumer_id_215b277e; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_account_credits_consumer_id_215b277e ON consumer_account_credits USING btree (consumer_id);


--
-- Name: consumer_account_credits_transaction_consumer_id_3e00f437; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_account_credits_transaction_consumer_id_3e00f437 ON consumer_account_credits_transaction USING btree (consumer_id);


--
-- Name: consumer_address_link_address_id_15eb8998; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_address_link_address_id_15eb8998 ON consumer_address_link USING btree (address_id);


--
-- Name: consumer_address_link_consumer_id_9e837860; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_address_link_consumer_id_9e837860 ON consumer_address_link USING btree (consumer_id);


--
-- Name: consumer_address_link_is_active_436adea4; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_address_link_is_active_436adea4 ON consumer_address_link USING btree (is_active);


--
-- Name: consumer_address_link_manual_point_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_address_link_manual_point_id ON consumer_address_link USING gist (manual_point);


--
-- Name: consumer_announcement_dist_consumer_announcement_id_112506de; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_announcement_dist_consumer_announcement_id_112506de ON consumer_announcement_district_link USING btree (consumer_announcement_id);


--
-- Name: consumer_announcement_district_link_district_id_8146d646; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_announcement_district_link_district_id_8146d646 ON consumer_announcement_district_link USING btree (district_id);


--
-- Name: consumer_announcement_subm_consumerannouncement_id_55b4b7c8; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_announcement_subm_consumerannouncement_id_55b4b7c8 ON consumer_announcement_submarkets USING btree (consumerannouncement_id);


--
-- Name: consumer_announcement_submarkets_submarket_id_b15c6a4d; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_announcement_submarkets_submarket_id_b15c6a4d ON consumer_announcement_submarkets USING btree (submarket_id);


--
-- Name: consumer_channel_name_b7caa8bc_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_channel_name_b7caa8bc_like ON consumer_channel USING btree (name varchar_pattern_ops);


--
-- Name: consumer_channel_submarkets_consumerchannel_id_5611af6b; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_channel_submarkets_consumerchannel_id_5611af6b ON consumer_channel_submarkets USING btree (consumerchannel_id);


--
-- Name: consumer_channel_submarkets_submarket_id_38f61a4e; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_channel_submarkets_submarket_id_38f61a4e ON consumer_channel_submarkets USING btree (submarket_id);


--
-- Name: consumer_charge_consumer_id_f883f7d3; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_charge_consumer_id_f883f7d3 ON consumer_charge USING btree (consumer_id);


--
-- Name: consumer_charge_country_id_7f5bd302; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_charge_country_id_7f5bd302 ON consumer_charge USING btree (country_id);


--
-- Name: consumer_charge_idempotency_key_f582490e_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_charge_idempotency_key_f582490e_like ON consumer_charge USING btree (idempotency_key varchar_pattern_ops);


--
-- Name: consumer_charge_issue_id_a06f09e1; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_charge_issue_id_a06f09e1 ON consumer_charge USING btree (issue_id);


--
-- Name: consumer_charge_target_ct_id_11e8fa7a; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_charge_target_ct_id_11e8fa7a ON consumer_charge USING btree (target_ct_id);


--
-- Name: consumer_charge_target_id_e175367d; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_charge_target_id_e175367d ON consumer_charge USING btree (target_id);


--
-- Name: consumer_communication_channel_name_9d6978ef; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_communication_channel_name_9d6978ef ON consumer_communication_channel USING btree (name);


--
-- Name: consumer_communication_channel_name_9d6978ef_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_communication_channel_name_9d6978ef_like ON consumer_communication_channel USING btree (name text_pattern_ops);


--
-- Name: consumer_communication_pre_email_holdout_group_id_a0759447; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_communication_pre_email_holdout_group_id_a0759447 ON consumer_communication_preferences USING btree (email_holdout_group_id);


--
-- Name: consumer_communication_preferences_email_preference_id_ef0dd076; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_communication_preferences_email_preference_id_ef0dd076 ON consumer_communication_preferences USING btree (email_preference_id);


--
-- Name: consumer_default_address_id_87d263cb; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_default_address_id_87d263cb ON consumer USING btree (default_address_id);


--
-- Name: consumer_default_card_id_97fb8f90; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_default_card_id_97fb8f90 ON consumer USING btree (default_card_id);


--
-- Name: consumer_default_country_id_b520b701; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_default_country_id_b520b701 ON consumer USING btree (default_country_id);


--
-- Name: consumer_delivery_rating_category_link_category_id_5af94e46; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_delivery_rating_category_link_category_id_5af94e46 ON consumer_delivery_rating_category_link USING btree (category_id);


--
-- Name: consumer_delivery_rating_category_link_rating_id_bd05f5e0; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_delivery_rating_category_link_rating_id_bd05f5e0 ON consumer_delivery_rating_category_link USING btree (rating_id);


--
-- Name: consumer_delivery_rating_category_name_5a87a099_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_delivery_rating_category_name_5a87a099_like ON consumer_delivery_rating_category USING btree (name text_pattern_ops);


--
-- Name: consumer_delivery_rating_store_id_d133db01; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_delivery_rating_store_id_d133db01 ON consumer_delivery_rating USING btree (store_id);


--
-- Name: consumer_donation_donation_recipient_id_4c17af96; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_donation_donation_recipient_id_4c17af96 ON consumer_donation USING btree (donation_recipient_id);


--
-- Name: consumer_donation_recipient_link_consumer_id_78196bf1; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_donation_recipient_link_consumer_id_78196bf1 ON consumer_donation_recipient_link USING btree (consumer_id);


--
-- Name: consumer_donation_recipient_link_donation_recipient_id_614e7e8b; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_donation_recipient_link_donation_recipient_id_614e7e8b ON consumer_donation_recipient_link USING btree (donation_recipient_id);


--
-- Name: consumer_donation_recipient_link_is_active_7a53b571; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_donation_recipient_link_is_active_7a53b571 ON consumer_donation_recipient_link USING btree (is_active);


--
-- Name: consumer_empty_store_list_request_location_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_empty_store_list_request_location_id ON consumer_empty_store_list_request USING gist (location);


--
-- Name: consumer_favorites_business_id_1d5a28d6; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_favorites_business_id_1d5a28d6 ON consumer_favorites USING btree (business_id);


--
-- Name: consumer_favorites_consumer_id_b8025142; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_favorites_consumer_id_b8025142 ON consumer_favorites USING btree (consumer_id);


--
-- Name: consumer_fraud_info_charge_id_2fe7309f; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_fraud_info_charge_id_2fe7309f ON consumer_fraud_info USING btree (charge_id);


--
-- Name: consumer_fraud_info_consumer_id_67b2996b; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_fraud_info_consumer_id_67b2996b ON consumer_fraud_info USING btree (consumer_id);


--
-- Name: consumer_fraud_info_order_cart_id_f6c1ff83; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_fraud_info_order_cart_id_f6c1ff83 ON consumer_fraud_info USING btree (order_cart_id);


--
-- Name: consumer_ios_devices_consumer_id_7cfc75c3; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_ios_devices_consumer_id_7cfc75c3 ON consumer_ios_devices USING btree (consumer_id);


--
-- Name: consumer_ios_devices_device_id_7b82b206; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_ios_devices_device_id_7b82b206 ON consumer_ios_devices USING btree (device_id);


--
-- Name: consumer_last_delivery_time_8959f256; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_last_delivery_time_8959f256 ON consumer USING btree (last_delivery_time);


--
-- Name: consumer_preferences_categ_consumer_preferences_id_56712347; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_preferences_categ_consumer_preferences_id_56712347 ON consumer_preferences_category_link USING btree (consumer_preferences_id);


--
-- Name: consumer_preferences_consumer_id_8f55d6a0; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_preferences_consumer_id_8f55d6a0 ON consumer_preferences USING btree (consumer_id);


--
-- Name: consumer_profile_edit_history_consumer_id_325aaed0; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_profile_edit_history_consumer_id_325aaed0 ON consumer_profile_edit_history USING btree (consumer_id);


--
-- Name: consumer_promotion_campaign_store_id_a9dc2aca; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_promotion_campaign_store_id_a9dc2aca ON consumer_promotion_campaign USING btree (store_id);


--
-- Name: consumer_promotion_channel_id_47a407fa; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_promotion_channel_id_47a407fa ON consumer_promotion USING btree (channel_id);


--
-- Name: consumer_promotion_code_e83ec56c_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_promotion_code_e83ec56c_like ON consumer_promotion USING btree (code text_pattern_ops);


--
-- Name: consumer_promotion_consumer_promotion_campaign_id_ed9a6a8b; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_promotion_consumer_promotion_campaign_id_ed9a6a8b ON consumer_promotion USING btree (consumer_promotion_campaign_id);


--
-- Name: consumer_push_notification_cancelled_by_server_b081fde1; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_push_notification_cancelled_by_server_b081fde1 ON consumer_push_notification USING btree (cancelled_by_server);


--
-- Name: consumer_push_notification_consumer_id_057a5299; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_push_notification_consumer_id_057a5299 ON consumer_push_notification USING btree (consumer_id);


--
-- Name: consumer_push_notification_scheduled_time_cc80fe7c; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_push_notification_scheduled_time_cc80fe7c ON consumer_push_notification USING btree (scheduled_time);


--
-- Name: consumer_push_notification_sent_time_728ea959; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_push_notification_sent_time_728ea959 ON consumer_push_notification USING btree (sent_time);


--
-- Name: consumer_referral_code_120e99ca_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_referral_code_120e99ca_like ON consumer USING btree (referral_code varchar_pattern_ops);


--
-- Name: consumer_referral_link_referrer_id_3158f718; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_referral_link_referrer_id_3158f718 ON consumer_referral_link USING btree (referrer_id);


--
-- Name: consumer_sanitized_email_8beb2028; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_sanitized_email_8beb2028 ON consumer USING btree (sanitized_email);


--
-- Name: consumer_sanitized_email_8beb2028_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_sanitized_email_8beb2028_like ON consumer USING btree (sanitized_email varchar_pattern_ops);


--
-- Name: consumer_share_consumer_id_6608e820; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_share_consumer_id_6608e820 ON consumer_share USING btree (consumer_id);


--
-- Name: consumer_store_request_consumer_id_d20471be; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_store_request_consumer_id_d20471be ON consumer_store_request USING btree (consumer_id);


--
-- Name: consumer_store_request_requested_store_id_7721a835; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_store_request_requested_store_id_7721a835 ON consumer_store_request USING btree (requested_store_id);


--
-- Name: consumer_store_request_requested_store_type_92fff26d; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_store_request_requested_store_type_92fff26d ON consumer_store_request USING btree (requested_store_type);


--
-- Name: consumer_store_request_requested_store_type_92fff26d_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_store_request_requested_store_type_92fff26d_like ON consumer_store_request USING btree (requested_store_type text_pattern_ops);


--
-- Name: consumer_stripe_country_id_b02ababd; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_stripe_country_id_b02ababd ON consumer USING btree (stripe_country_id);


--
-- Name: consumer_subscription_consumer_id_07bf3b1e; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_subscription_consumer_id_07bf3b1e ON consumer_subscription USING btree (consumer_id);


--
-- Name: consumer_subscription_consumer_subscription_plan_id_0c1de937; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_subscription_consumer_subscription_plan_id_0c1de937 ON consumer_subscription USING btree (consumer_subscription_plan_id);


--
-- Name: consumer_subscription_plan_consumer_discount_id_446bf1cb; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_subscription_plan_consumer_discount_id_446bf1cb ON consumer_subscription_plan USING btree (consumer_discount_id);


--
-- Name: consumer_subscription_plan_consumer_subscription_plan_0219faf2; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_subscription_plan_consumer_subscription_plan_0219faf2 ON consumer_subscription_plan_trial_featured_location_link USING btree (consumer_subscription_plan_trial_id);


--
-- Name: consumer_subscription_plan_consumer_subscription_plan_326e6aa9; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_subscription_plan_consumer_subscription_plan_326e6aa9 ON consumer_subscription_plan_trial USING btree (consumer_subscription_plan_id);


--
-- Name: consumer_subscription_plan_consumer_subscription_plan_adc2ead7; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_subscription_plan_consumer_subscription_plan_adc2ead7 ON consumer_subscription_plan_submarket_link USING btree (consumer_subscription_plan_id);


--
-- Name: consumer_subscription_plan_consumer_subscription_plan_bdb1ee39; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_subscription_plan_consumer_subscription_plan_bdb1ee39 ON consumer_subscription_plan_trial_submarket_link USING btree (consumer_subscription_plan_trial_id);


--
-- Name: consumer_subscription_plan_consumer_subscription_plan_c706f1bb; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_subscription_plan_consumer_subscription_plan_c706f1bb ON consumer_subscription_plan_featured_location_link USING btree (consumer_subscription_plan_id);


--
-- Name: consumer_subscription_plan_consumersubscriptionplan_i_cc43dac5; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_subscription_plan_consumersubscriptionplan_i_cc43dac5 ON consumer_subscription_plan_promotion_infos USING btree (consumersubscriptionplan_id);


--
-- Name: consumer_subscription_plan_consumersubscriptionplanpr_8b6b4757; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_subscription_plan_consumersubscriptionplanpr_8b6b4757 ON consumer_subscription_plan_trial_promotion_infos USING btree (consumersubscriptionplanpromotioninfo_id);


--
-- Name: consumer_subscription_plan_consumersubscriptionplanpr_ff102a4f; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_subscription_plan_consumersubscriptionplanpr_ff102a4f ON consumer_subscription_plan_promotion_infos USING btree (consumersubscriptionplanpromotioninfo_id);


--
-- Name: consumer_subscription_plan_consumersubscriptionplantr_d9451a7c; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_subscription_plan_consumersubscriptionplantr_d9451a7c ON consumer_subscription_plan_trial_promotion_infos USING btree (consumersubscriptionplantrial_id);


--
-- Name: consumer_subscription_plan_end_time_1eb21edc; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_subscription_plan_end_time_1eb21edc ON consumer_subscription_plan USING btree (end_time);


--
-- Name: consumer_subscription_plan_featured_location_id_3ec5f5bf; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_subscription_plan_featured_location_id_3ec5f5bf ON consumer_subscription_plan_trial_featured_location_link USING btree (featured_location_id);


--
-- Name: consumer_subscription_plan_featured_location_id_a543f4b7; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_subscription_plan_featured_location_id_a543f4b7 ON consumer_subscription_plan_featured_location_link USING btree (featured_location_id);


--
-- Name: consumer_subscription_plan_is_accepting_new_subscribe_f720aba6; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_subscription_plan_is_accepting_new_subscribe_f720aba6 ON consumer_subscription_plan USING btree (is_accepting_new_subscribers);


--
-- Name: consumer_subscription_plan_stripe_id_ddde9b59_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_subscription_plan_stripe_id_ddde9b59_like ON consumer_subscription_plan USING btree (stripe_id text_pattern_ops);


--
-- Name: consumer_subscription_plan_submarket_id_f1c91ebc; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_subscription_plan_submarket_id_f1c91ebc ON consumer_subscription_plan_trial_submarket_link USING btree (submarket_id);


--
-- Name: consumer_subscription_plan_submarket_link_submarket_id_f94cc73c; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_subscription_plan_submarket_link_submarket_id_f94cc73c ON consumer_subscription_plan_submarket_link USING btree (submarket_id);


--
-- Name: consumer_subscription_stripe_id_15c2d259_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_subscription_stripe_id_15c2d259_like ON consumer_subscription USING btree (stripe_id text_pattern_ops);


--
-- Name: consumer_subscription_subscription_status_9f5d3ca8; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_subscription_subscription_status_9f5d3ca8 ON consumer_subscription USING btree (subscription_status);


--
-- Name: consumer_subscription_subscription_status_9f5d3ca8_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_subscription_subscription_status_9f5d3ca8_like ON consumer_subscription USING btree (subscription_status text_pattern_ops);


--
-- Name: consumer_subscription_unit_charge_id_453633df; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_subscription_unit_charge_id_453633df ON consumer_subscription_unit USING btree (charge_id);


--
-- Name: consumer_subscription_unit_consumer_subscription_id_6d0f0b4c; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_subscription_unit_consumer_subscription_id_6d0f0b4c ON consumer_subscription_unit USING btree (consumer_subscription_id);


--
-- Name: consumer_subscription_unit_stripe_id_78eb8ff4_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_subscription_unit_stripe_id_78eb8ff4_like ON consumer_subscription_unit USING btree (stripe_id text_pattern_ops);


--
-- Name: consumer_survey_answer_option_survey_question_id_1f759b96; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_survey_answer_option_survey_question_id_1f759b96 ON consumer_survey_answer_option USING btree (survey_question_id);


--
-- Name: consumer_survey_question_r_survey_answer_option_id_48082598; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_survey_question_r_survey_answer_option_id_48082598 ON consumer_survey_question_response USING btree (survey_answer_option_id);


--
-- Name: consumer_survey_question_response_survey_question_id_9ab71de7; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_survey_question_response_survey_question_id_9ab71de7 ON consumer_survey_question_response USING btree (survey_question_id);


--
-- Name: consumer_survey_question_response_survey_response_id_3aba90d2; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_survey_question_response_survey_response_id_3aba90d2 ON consumer_survey_question_response USING btree (survey_response_id);


--
-- Name: consumer_survey_question_survey_id_9d4fc6bf; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_survey_question_survey_id_9d4fc6bf ON consumer_survey_question USING btree (survey_id);


--
-- Name: consumer_survey_response_consumer_id_bcd1a9f2; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_survey_response_consumer_id_bcd1a9f2 ON consumer_survey_response USING btree (consumer_id);


--
-- Name: consumer_survey_response_survey_id_9aa1b2e0; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_survey_response_survey_id_9aa1b2e0 ON consumer_survey_response USING btree (survey_id);


--
-- Name: consumer_terms_of_service_version_e98efca8_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_terms_of_service_version_e98efca8_like ON consumer_terms_of_service USING btree (version text_pattern_ops);


--
-- Name: consumer_tos_link_consumer_id_232c8014; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_tos_link_consumer_id_232c8014 ON consumer_tos_link USING btree (consumer_id);


--
-- Name: consumer_tos_link_terms_of_service_id_72cf09a8; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_tos_link_terms_of_service_id_72cf09a8 ON consumer_tos_link USING btree (terms_of_service_id);


--
-- Name: consumer_variable_pay_consumer_id_81feb784; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_variable_pay_consumer_id_81feb784 ON consumer_variable_pay USING btree (consumer_id);


--
-- Name: consumer_variable_pay_delivery_id_0d5acb36; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_variable_pay_delivery_id_0d5acb36 ON consumer_variable_pay USING btree (delivery_id);


--
-- Name: consumer_variable_pay_district_id_4c5ed7af; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX consumer_variable_pay_district_id_4c5ed7af ON consumer_variable_pay USING btree (district_id);


--
-- Name: core_image_target_ct_id_5fe8deb4; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX core_image_target_ct_id_5fe8deb4 ON core_image USING btree (target_ct_id);


--
-- Name: core_modelannotation_target_ct_id_e5fbc600; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX core_modelannotation_target_ct_id_e5fbc600 ON core_modelannotation USING btree (target_ct_id);


--
-- Name: country_name_0a984f2a_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX country_name_0a984f2a_like ON country USING btree (name varchar_pattern_ops);


--
-- Name: country_shortname_c9e2149d_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX country_shortname_c9e2149d_like ON country USING btree (shortname varchar_pattern_ops);


--
-- Name: credit_refund_delivery_error_credit_refund_error_id_b0f07a11; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX credit_refund_delivery_error_credit_refund_error_id_b0f07a11 ON credit_refund_delivery_error USING btree (credit_refund_error_id);


--
-- Name: credit_refund_error_dispatch_error_id_00e71bf8; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX credit_refund_error_dispatch_error_id_00e71bf8 ON credit_refund_error USING btree (dispatch_error_id);


--
-- Name: credit_refund_order_item_error_credit_refund_error_id_14917bed; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX credit_refund_order_item_error_credit_refund_error_id_14917bed ON credit_refund_order_item_error USING btree (credit_refund_error_id);


--
-- Name: curated_category_end_time_b23a3d6d; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX curated_category_end_time_b23a3d6d ON curated_category USING btree (end_time);


--
-- Name: curated_category_membership_category_id_41178a87; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX curated_category_membership_category_id_41178a87 ON curated_category_membership USING btree (category_id);


--
-- Name: curated_category_membership_end_time_7022dc72; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX curated_category_membership_end_time_7022dc72 ON curated_category_membership USING btree (end_time);


--
-- Name: curated_category_membership_member_ct_id_3dd2c4aa; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX curated_category_membership_member_ct_id_3dd2c4aa ON curated_category_membership USING btree (member_ct_id);


--
-- Name: curated_category_membership_start_time_2fba273b; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX curated_category_membership_start_time_2fba273b ON curated_category_membership USING btree (start_time);


--
-- Name: curated_category_start_time_6f75d988; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX curated_category_start_time_6f75d988 ON curated_category USING btree (start_time);


--
-- Name: curated_category_submarket_id_572c346b; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX curated_category_submarket_id_572c346b ON curated_category USING btree (submarket_id);


--
-- Name: dasher_capacity_model_starting_point_id_6e9ea3b7; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX dasher_capacity_model_starting_point_id_6e9ea3b7 ON dasher_capacity_model USING btree (starting_point_id);


--
-- Name: dasher_capacity_plan_active_date_f338ebc9; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX dasher_capacity_plan_active_date_f338ebc9 ON dasher_capacity_plan USING btree (active_date);


--
-- Name: dasher_capacity_plan_model_id_99f6f073; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX dasher_capacity_plan_model_id_99f6f073 ON dasher_capacity_plan USING btree (model_id);


--
-- Name: dasher_capacity_plan_starting_point_id_d549d44e; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX dasher_capacity_plan_starting_point_id_d549d44e ON dasher_capacity_plan USING btree (starting_point_id);


--
-- Name: dasher_onboarding_dasher_id_64f69b83; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX dasher_onboarding_dasher_id_64f69b83 ON dasher_onboarding USING btree (dasher_id);


--
-- Name: dasher_onboarding_onboarding_type_id_9631d696; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX dasher_onboarding_onboarding_type_id_9631d696 ON dasher_onboarding USING btree (onboarding_type_id);


--
-- Name: dd4b_expense_code_organization_id_is_active_4c21b44f_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX dd4b_expense_code_organization_id_is_active_4c21b44f_idx ON dd4b_expense_code USING btree (organization_id, is_active);


--
-- Name: delivery_active_date_d9e5ba88; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_active_date_d9e5ba88 ON delivery USING btree (active_date);


--
-- Name: delivery_actual_delivery_time_b4fa8714; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_actual_delivery_time_b4fa8714 ON delivery USING btree (actual_delivery_time);


--
-- Name: delivery_batch_created_at_2dc28585; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_batch_created_at_2dc28585 ON delivery_batch USING btree (created_at);


--
-- Name: delivery_batch_id_3847577c; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_batch_id_3847577c ON delivery USING btree (batch_id);


--
-- Name: delivery_batch_membership_batch_id_76f3bd57; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_batch_membership_batch_id_76f3bd57 ON delivery_batch_membership USING btree (batch_id);


--
-- Name: delivery_batch_membership_created_at_dce83a6e; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_batch_membership_created_at_dce83a6e ON delivery_batch_membership USING btree (created_at);


--
-- Name: delivery_cancellation_reason_category_id_32c42b4e; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_cancellation_reason_category_id_32c42b4e ON delivery_cancellation_reason USING btree (category_id);


--
-- Name: delivery_cancellation_reason_category_name_479e2306_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_cancellation_reason_category_name_479e2306_like ON delivery_cancellation_reason_category USING btree (name text_pattern_ops);


--
-- Name: delivery_cancellation_reason_name_2235bd3f_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_cancellation_reason_name_2235bd3f_like ON delivery_cancellation_reason USING btree (name text_pattern_ops);


--
-- Name: delivery_cancelled_at_dd3593d7; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_cancelled_at_dd3593d7 ON delivery USING btree (cancelled_at);


--
-- Name: delivery_cancelled_at_is_from_par_7d562165_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_cancelled_at_is_from_par_7d562165_idx ON delivery USING btree (cancelled_at, is_from_partner_store, actual_delivery_time);


--
-- Name: delivery_catering_verification_delivery_id_d1e178aa; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_catering_verification_delivery_id_d1e178aa ON delivery_catering_verification USING btree (delivery_id);


--
-- Name: delivery_created_at_4120b2df; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_created_at_4120b2df ON delivery USING btree (created_at);


--
-- Name: delivery_creator_id_7736d344; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_creator_id_7736d344 ON delivery USING btree (creator_id);


--
-- Name: delivery_delivery_address_id_ecb3baf7; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_delivery_address_id_ecb3baf7 ON delivery USING btree (delivery_address_id);


--
-- Name: delivery_drive_info_is_return_delivery_4e9a7715; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_drive_info_is_return_delivery_4e9a7715 ON delivery_drive_info USING btree (is_return_delivery);


--
-- Name: delivery_drive_info_is_route_based_f512faec; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_drive_info_is_route_based_f512faec ON delivery_drive_info USING btree (is_route_based);


--
-- Name: delivery_drive_info_return_delivery_id_7f23ea7c; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_drive_info_return_delivery_id_7f23ea7c ON delivery_drive_info USING btree (return_delivery_id);


--
-- Name: delivery_drive_info_searchable_f9a86b7e; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_drive_info_searchable_f9a86b7e ON delivery_drive_info USING btree (searchable);


--
-- Name: delivery_drive_info_searchable_f9a86b7e_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_drive_info_searchable_f9a86b7e_like ON delivery_drive_info USING btree (searchable text_pattern_ops);


--
-- Name: delivery_eta_prediction_id_4d88bf57; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_eta_prediction_id_4d88bf57 ON delivery USING btree (eta_prediction_id);


--
-- Name: delivery_event_category_id_c39cda48; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_event_category_id_c39cda48 ON delivery_event USING btree (category_id);


--
-- Name: delivery_event_category_name_01175d09_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_event_category_name_01175d09_like ON delivery_event_category USING btree (name varchar_pattern_ops);


--
-- Name: delivery_event_created_by_id_2c294d4a; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_event_created_by_id_2c294d4a ON delivery_event USING btree (created_by_id);


--
-- Name: delivery_event_delivery_id_411a5819; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_event_delivery_id_411a5819 ON delivery_event USING btree (delivery_id);


--
-- Name: delivery_funding_created_by_id_bffc87f1; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_funding_created_by_id_bffc87f1 ON delivery_funding USING btree (created_by_id);


--
-- Name: delivery_funding_delivery_id_c25e09f3; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_funding_delivery_id_c25e09f3 ON delivery_funding USING btree (delivery_id);


--
-- Name: delivery_gift_code_379e78ad_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_gift_code_379e78ad_like ON delivery_gift USING btree (code varchar_pattern_ops);


--
-- Name: delivery_gift_consumer_id_9a6db8c3; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_gift_consumer_id_9a6db8c3 ON delivery_gift USING btree (consumer_id);


--
-- Name: delivery_growth_model_starting_point_id_8d0d7cd2; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_growth_model_starting_point_id_8d0d7cd2 ON delivery_growth_model USING btree (starting_point_id);


--
-- Name: delivery_growth_prediction_growth_model_id_10399c53; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_growth_prediction_growth_model_id_10399c53 ON delivery_growth_prediction USING btree (growth_model_id);


--
-- Name: delivery_growth_prediction_starting_point_id_3bda6847; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_growth_prediction_starting_point_id_3bda6847 ON delivery_growth_prediction USING btree (starting_point_id);


--
-- Name: delivery_idempotency_key_e148c04d_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_idempotency_key_e148c04d_like ON delivery USING btree (idempotency_key text_pattern_ops);


--
-- Name: delivery_is_asap_b25d5306; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_is_asap_b25d5306 ON delivery USING btree (is_asap);


--
-- Name: delivery_is_from_partner_store_5bc911f8; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_is_from_partner_store_5bc911f8 ON delivery USING btree (is_from_partner_store);


--
-- Name: delivery_is_from_store_to_us_7cff94ad; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_is_from_store_to_us_7cff94ad ON delivery USING btree (is_from_store_to_us);


--
-- Name: delivery_is_preassign_9f4e920d; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_is_preassign_9f4e920d ON delivery USING btree (is_preassign);


--
-- Name: delivery_is_preassignable_6ae5aacb; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_is_preassignable_6ae5aacb ON delivery USING btree (is_preassignable);


--
-- Name: delivery_is_test_1125656f; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_is_test_1125656f ON delivery USING btree (is_test);


--
-- Name: delivery_issue_claimed_by_id_529f5739; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_issue_claimed_by_id_529f5739 ON delivery_issue USING btree (claimed_by_id);


--
-- Name: delivery_issue_created_at_4156bed7; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_issue_created_at_4156bed7 ON delivery_issue USING btree (created_at);


--
-- Name: delivery_issue_created_by_id_9d83b02f; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_issue_created_by_id_9d83b02f ON delivery_issue USING btree (created_by_id);


--
-- Name: delivery_issue_resolved_by_id_e01555ff; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_issue_resolved_by_id_e01555ff ON delivery_issue USING btree (resolved_by_id);


--
-- Name: delivery_issue_salesforce_case_uid_5bd67374_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_issue_salesforce_case_uid_5bd67374_like ON delivery_issue USING btree (salesforce_case_uid text_pattern_ops);


--
-- Name: delivery_item_delivery_id_da8a61b2; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_item_delivery_id_da8a61b2 ON delivery_item USING btree (delivery_id);


--
-- Name: delivery_item_drive_order_id_31691705; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_item_drive_order_id_31691705 ON delivery_item USING btree (drive_order_id);


--
-- Name: delivery_market_a5ec6297; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_market_a5ec6297 ON delivery USING btree (market);


--
-- Name: delivery_masking_number_as_twilio_masking_number_id_c4158fd5; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_masking_number_as_twilio_masking_number_id_c4158fd5 ON delivery_masking_number_assignment USING btree (twilio_masking_number_id);


--
-- Name: delivery_masking_number_assignment_created_at_4ca82c80; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_masking_number_assignment_created_at_4ca82c80 ON delivery_masking_number_assignment USING btree (created_at);


--
-- Name: delivery_masking_number_assignment_delivery_id_f16cd30b; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_masking_number_assignment_delivery_id_f16cd30b ON delivery_masking_number_assignment USING btree (delivery_id);


--
-- Name: delivery_merchant_transaction_id_39abe73b; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_merchant_transaction_id_39abe73b ON delivery USING btree (merchant_transaction_id);


--
-- Name: delivery_order_cart_id_2ecde47c; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_order_cart_id_2ecde47c ON delivery USING btree (order_cart_id);


--
-- Name: delivery_parent_delivery_id_06f70b4c; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_parent_delivery_id_06f70b4c ON delivery USING btree (parent_delivery_id);


--
-- Name: delivery_pickup_address_id_932b9067; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_pickup_address_id_932b9067 ON delivery USING btree (pickup_address_id);


--
-- Name: delivery_proactive_monitoring_required_a7e89eea; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_proactive_monitoring_required_a7e89eea ON delivery USING btree (proactive_monitoring_required);


--
-- Name: delivery_public_id_964d91a3_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_public_id_964d91a3_like ON delivery USING btree (public_id varchar_pattern_ops);


--
-- Name: delivery_quoted_delivery_time_1dd0597c; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_quoted_delivery_time_1dd0597c ON delivery USING btree (quoted_delivery_time);


--
-- Name: delivery_rating_category_link_category_id_48d0e88b; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_rating_category_link_category_id_48d0e88b ON delivery_rating_category_link USING btree (category_id);


--
-- Name: delivery_rating_category_link_rating_id_0d7544c0; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_rating_category_link_rating_id_0d7544c0 ON delivery_rating_category_link USING btree (rating_id);


--
-- Name: delivery_rating_dasher_id_0425d0a8; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_rating_dasher_id_0425d0a8 ON delivery_rating USING btree (dasher_id);


--
-- Name: delivery_receipt_dasher_creator_id_86517722; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_receipt_dasher_creator_id_86517722 ON delivery_receipt USING btree (dasher_creator_id);


--
-- Name: delivery_receipt_delivery_id_a9e6037c; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_receipt_delivery_id_a9e6037c ON delivery_receipt USING btree (delivery_id);


--
-- Name: delivery_receipt_transaction_id_4eac6077; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_receipt_transaction_id_4eac6077 ON delivery_receipt USING btree (transaction_id);


--
-- Name: delivery_request_created_at_c2653f83; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_request_created_at_c2653f83 ON delivery_request USING btree (created_at);


--
-- Name: delivery_request_creator_id_66f35496; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_request_creator_id_66f35496 ON delivery_request USING btree (creator_id);


--
-- Name: delivery_request_dropoff_address_id_ce0e432a; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_request_dropoff_address_id_ce0e432a ON delivery_request USING btree (dropoff_address_id);


--
-- Name: delivery_request_order_cart_id_4231d4bf; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_request_order_cart_id_4231d4bf ON delivery_request USING btree (order_cart_id);


--
-- Name: delivery_request_pickup_address_id_885fd4cf; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_request_pickup_address_id_885fd4cf ON delivery_request USING btree (pickup_address_id);


--
-- Name: delivery_request_store_id_766984b2; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_request_store_id_766984b2 ON delivery_request USING btree (store_id);


--
-- Name: delivery_request_submission_monitor_created_at_0c344185; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_request_submission_monitor_created_at_0c344185 ON delivery_request_submission_monitor USING btree (created_at);


--
-- Name: delivery_request_submission_monitor_key_a0afeb39_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_request_submission_monitor_key_a0afeb39_like ON delivery_request_submission_monitor USING btree (key text_pattern_ops);


--
-- Name: delivery_set_created_at_f2da9992; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_set_created_at_f2da9992 ON delivery_set USING btree (created_at);


--
-- Name: delivery_set_earliest_pickup_time_342cea4a; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_set_earliest_pickup_time_342cea4a ON delivery_set USING btree (earliest_pickup_time);


--
-- Name: delivery_set_latest_delivery_time_7287d612; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_set_latest_delivery_time_7287d612 ON delivery_set USING btree (latest_delivery_time);


--
-- Name: delivery_set_mapping_delivery_id_789a6854; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_set_mapping_delivery_id_789a6854 ON delivery_set_mapping USING btree (delivery_id);


--
-- Name: delivery_set_mapping_delivery_set_id_0772fa27; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_set_mapping_delivery_set_id_0772fa27 ON delivery_set_mapping USING btree (delivery_set_id);


--
-- Name: delivery_set_market_id_40fa7218; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_set_market_id_40fa7218 ON delivery_set USING btree (market_id);


--
-- Name: delivery_shift_id_ecd388a3; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_shift_id_ecd388a3 ON delivery USING btree (shift_id);


--
-- Name: delivery_should_be_manually_assigned_a78bae21; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_should_be_manually_assigned_a78bae21 ON delivery USING btree (should_be_manually_assigned);


--
-- Name: delivery_simulator_business_id_62306718; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_simulator_business_id_62306718 ON delivery_simulator USING btree (business_id);


--
-- Name: delivery_simulator_store_id_2c80964f; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_simulator_store_id_2c80964f ON delivery_simulator USING btree (store_id);


--
-- Name: delivery_source_15d51481; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_source_15d51481 ON delivery USING btree (source);


--
-- Name: delivery_source_15d51481_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_source_15d51481_like ON delivery USING btree (source text_pattern_ops);


--
-- Name: delivery_store_id_7e9dfa4f; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_store_id_7e9dfa4f ON delivery USING btree (store_id);


--
-- Name: delivery_store_order_cart_id_eba87cdc; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_store_order_cart_id_eba87cdc ON delivery USING btree (store_order_cart_id);


--
-- Name: delivery_submarket_31dec55a; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_submarket_31dec55a ON delivery USING btree (submarket);


--
-- Name: delivery_transfer_id_f20358da; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX delivery_transfer_id_f20358da ON delivery USING btree (transfer_id);


--
-- Name: developer_business_id_a939214d; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX developer_business_id_a939214d ON developer USING btree (business_id);


--
-- Name: device_fingerprint_block_reason_b292686a; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX device_fingerprint_block_reason_b292686a ON device_fingerprint USING btree (block_reason);


--
-- Name: device_fingerprint_block_reason_b292686a_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX device_fingerprint_block_reason_b292686a_like ON device_fingerprint USING btree (block_reason text_pattern_ops);


--
-- Name: device_fingerprint_created_at_5b9c852d; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX device_fingerprint_created_at_5b9c852d ON device_fingerprint USING btree (created_at);


--
-- Name: dispatch_error_created_by_id_284b4e65; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX dispatch_error_created_by_id_284b4e65 ON dispatch_error USING btree (created_by_id);


--
-- Name: dispatch_error_delivery_id_c4483737; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX dispatch_error_delivery_id_c4483737 ON dispatch_error USING btree (delivery_id);


--
-- Name: dispatch_error_order_id_d817ddfe; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX dispatch_error_order_id_d817ddfe ON dispatch_error USING btree (order_id);


--
-- Name: dispatch_error_shift_id_5568aba6; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX dispatch_error_shift_id_5568aba6 ON dispatch_error USING btree (shift_id);


--
-- Name: dispatch_error_transaction_id_ce71a344; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX dispatch_error_transaction_id_ce71a344 ON dispatch_error USING btree (transaction_id);


--
-- Name: district_city_id_9a75808c; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX district_city_id_9a75808c ON district USING btree (city_id);


--
-- Name: district_geometry_geom_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX district_geometry_geom_id ON district_geometry USING gist (geom);


--
-- Name: district_html_color_c5afacdc_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX district_html_color_c5afacdc_like ON district USING btree (html_color varchar_pattern_ops);


--
-- Name: district_market_id_c618bbcd; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX district_market_id_c618bbcd ON district USING btree (market_id);


--
-- Name: district_name_839f005c_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX district_name_839f005c_like ON district USING btree (name varchar_pattern_ops);


--
-- Name: district_shortname_5d68a65e_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX district_shortname_5d68a65e_like ON district USING btree (shortname varchar_pattern_ops);


--
-- Name: district_starting_point_av_district_id_9b8309ee; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX district_starting_point_av_district_id_9b8309ee ON district_starting_point_availability_override USING btree (district_id);


--
-- Name: district_starting_point_av_startingpoint_id_a4cce1af; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX district_starting_point_av_startingpoint_id_a4cce1af ON district_starting_point_availability_override USING btree (startingpoint_id);


--
-- Name: district_submarket_id_bd85af85; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX district_submarket_id_bd85af85 ON district USING btree (submarket_id);


--
-- Name: django_admin_log_content_type_id_c4bce8eb; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX django_admin_log_content_type_id_c4bce8eb ON django_admin_log USING btree (content_type_id);


--
-- Name: django_admin_log_user_id_c564eba6; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX django_admin_log_user_id_c564eba6 ON django_admin_log USING btree (user_id);


--
-- Name: django_session_expire_date_a5c62663; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX django_session_expire_date_a5c62663 ON django_session USING btree (expire_date);


--
-- Name: django_session_session_key_c0390e0f_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX django_session_session_key_c0390e0f_like ON django_session USING btree (session_key varchar_pattern_ops);


--
-- Name: django_twilio_caller_phone_number_6a9cca42_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX django_twilio_caller_phone_number_6a9cca42_like ON django_twilio_caller USING btree (phone_number varchar_pattern_ops);


--
-- Name: donation_recipient_is_active_9e87be73; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX donation_recipient_is_active_9e87be73 ON donation_recipient USING btree (is_active);


--
-- Name: donation_recipient_name_3bc85d73_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX donation_recipient_name_3bc85d73_like ON donation_recipient USING btree (name text_pattern_ops);


--
-- Name: doordash_blacklistedemail_blacklisted_by_id_272dddf6; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX doordash_blacklistedemail_blacklisted_by_id_272dddf6 ON doordash_blacklistedemail USING btree (blacklisted_by_id);


--
-- Name: doordash_blacklistedemail_blacklisted_user_id_7a7521f8; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX doordash_blacklistedemail_blacklisted_user_id_7a7521f8 ON doordash_blacklistedemail USING btree (blacklisted_user_id);


--
-- Name: doordash_blacklistedemail_email_898f27a3_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX doordash_blacklistedemail_email_898f27a3_like ON doordash_blacklistedemail USING btree (email varchar_pattern_ops);


--
-- Name: doordash_blacklistedpaymentcard_blacklisted_by_id_2be3ac32; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX doordash_blacklistedpaymentcard_blacklisted_by_id_2be3ac32 ON doordash_blacklistedpaymentcard USING btree (blacklisted_by_id);


--
-- Name: doordash_blacklistedpaymentcard_blacklisted_user_id_30514b12; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX doordash_blacklistedpaymentcard_blacklisted_user_id_30514b12 ON doordash_blacklistedpaymentcard USING btree (blacklisted_user_id);


--
-- Name: doordash_blacklistedpaymentcard_fingerprint_a4d10722_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX doordash_blacklistedpaymentcard_fingerprint_a4d10722_like ON doordash_blacklistedpaymentcard USING btree (fingerprint text_pattern_ops);


--
-- Name: doordash_blacklistedphonenumber_blacklisted_by_id_171c12d7; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX doordash_blacklistedphonenumber_blacklisted_by_id_171c12d7 ON doordash_blacklistedphonenumber USING btree (blacklisted_by_id);


--
-- Name: doordash_blacklistedphonenumber_blacklisted_user_id_520a249c; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX doordash_blacklistedphonenumber_blacklisted_user_id_520a249c ON doordash_blacklistedphonenumber USING btree (blacklisted_user_id);


--
-- Name: doordash_blacklistedphonenumber_phone_number_81282592_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX doordash_blacklistedphonenumber_phone_number_81282592_like ON doordash_blacklistedphonenumber USING btree (phone_number varchar_pattern_ops);


--
-- Name: doordash_blacklisteduser_blacklisted_by_id_c86af4ff; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX doordash_blacklisteduser_blacklisted_by_id_c86af4ff ON doordash_blacklisteduser USING btree (blacklisted_by_id);


--
-- Name: doordash_blacklisteduser_deactivation_source_id_895ea495; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX doordash_blacklisteduser_deactivation_source_id_895ea495 ON doordash_blacklisteduser USING btree (deactivation_source_id);


--
-- Name: doordash_employmentperiod_employee_id_8043d60a; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX doordash_employmentperiod_employee_id_8043d60a ON doordash_employmentperiod USING btree (employee_id);


--
-- Name: doordash_orderitemsubstitu_replaced_order_item_id_f4ef9c96; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX doordash_orderitemsubstitu_replaced_order_item_id_f4ef9c96 ON doordash_orderitemsubstitutionevent USING btree (replaced_order_item_id);


--
-- Name: doordash_orderitemsubstitutionevent_order_item_id_6b894c7c; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX doordash_orderitemsubstitutionevent_order_item_id_6b894c7c ON doordash_orderitemsubstitutionevent USING btree (order_item_id);


--
-- Name: drive_business_mapping_brand_name_source_e406e061_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX drive_business_mapping_brand_name_source_e406e061_idx ON drive_business_mapping USING btree (brand_name, source);


--
-- Name: drive_business_mapping_business_id_19eca09a; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX drive_business_mapping_business_id_19eca09a ON drive_business_mapping USING btree (business_id);


--
-- Name: drive_business_mapping_developer_id_2e81c45f; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX drive_business_mapping_developer_id_2e81c45f ON drive_business_mapping USING btree (developer_id);


--
-- Name: drive_delivery_identifier_mapping_created_at_fec5ee19; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX drive_delivery_identifier_mapping_created_at_fec5ee19 ON drive_delivery_identifier_mapping USING btree (created_at);


--
-- Name: drive_delivery_identifier_mapping_external_id_5549f0ae; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX drive_delivery_identifier_mapping_external_id_5549f0ae ON drive_delivery_identifier_mapping USING btree (external_id);


--
-- Name: drive_delivery_identifier_mapping_external_id_5549f0ae_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX drive_delivery_identifier_mapping_external_id_5549f0ae_like ON drive_delivery_identifier_mapping USING btree (external_id text_pattern_ops);


--
-- Name: drive_delivery_identifier_mapping_store_id_131d616d; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX drive_delivery_identifier_mapping_store_id_131d616d ON drive_delivery_identifier_mapping USING btree (store_id);


--
-- Name: drive_effort_based_pay_vars_submarket_id_e0820c7c; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX drive_effort_based_pay_vars_submarket_id_e0820c7c ON drive_effort_based_pay_vars USING btree (submarket_id);


--
-- Name: drive_external_batch_id_mapping_created_at_cbea386f; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX drive_external_batch_id_mapping_created_at_cbea386f ON drive_external_batch_id_mapping USING btree (created_at);


--
-- Name: drive_external_batch_id_mapping_external_batch_id_88c4b2a1; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX drive_external_batch_id_mapping_external_batch_id_88c4b2a1 ON drive_external_batch_id_mapping USING btree (external_batch_id);


--
-- Name: drive_external_batch_id_mapping_external_batch_id_88c4b2a1_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX drive_external_batch_id_mapping_external_batch_id_88c4b2a1_like ON drive_external_batch_id_mapping USING btree (external_batch_id text_pattern_ops);


--
-- Name: drive_order_cancelled_at_8679b7ef; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX drive_order_cancelled_at_8679b7ef ON drive_order USING btree (cancelled_at);


--
-- Name: drive_order_delivery_id_1e5de019; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX drive_order_delivery_id_1e5de019 ON drive_order USING btree (delivery_id);


--
-- Name: drive_order_delivery_tracking_url_849b98e8_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX drive_order_delivery_tracking_url_849b98e8_like ON drive_order USING btree (delivery_tracking_url text_pattern_ops);


--
-- Name: drive_order_external_delivery_id_e64ddb7f; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX drive_order_external_delivery_id_e64ddb7f ON drive_order USING btree (external_delivery_id);


--
-- Name: drive_order_external_delivery_id_e64ddb7f_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX drive_order_external_delivery_id_e64ddb7f_like ON drive_order USING btree (external_delivery_id text_pattern_ops);


--
-- Name: drive_order_quoted_delivery_time_cdfc8e3e; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX drive_order_quoted_delivery_time_cdfc8e3e ON drive_order USING btree (quoted_delivery_time);


--
-- Name: drive_order_return_delivery_id_22dd27f5; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX drive_order_return_delivery_id_22dd27f5 ON drive_order USING btree (return_delivery_id);


--
-- Name: drive_order_store_id_and_external_delivery_id_uniq; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX drive_order_store_id_and_external_delivery_id_uniq ON drive_order USING btree (store_id, external_delivery_id) WHERE (cancelled_at IS NULL);


--
-- Name: drive_order_store_id_created_at_5ee96fe4_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX drive_order_store_id_created_at_5ee96fe4_idx ON drive_order USING btree (store_id, created_at);


--
-- Name: drive_quote_created_at_2eca0249; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX drive_quote_created_at_2eca0249 ON drive_quote USING btree (created_at);


--
-- Name: drive_store_catering_setup_instruction_created_at_60d3a1ca; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX drive_store_catering_setup_instruction_created_at_60d3a1ca ON drive_store_catering_setup_instruction USING btree (created_at);


--
-- Name: drive_store_catering_setup_instruction_store_id_2bcaef5a; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX drive_store_catering_setup_instruction_store_id_2bcaef5a ON drive_store_catering_setup_instruction USING btree (store_id);


--
-- Name: drive_store_id_mapping_business_id_589c30c5; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX drive_store_id_mapping_business_id_589c30c5 ON drive_store_id_mapping USING btree (business_id);


--
-- Name: drive_store_id_mapping_external_store_id_bb2b375f; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX drive_store_id_mapping_external_store_id_bb2b375f ON drive_store_id_mapping USING btree (external_store_id);


--
-- Name: drive_store_id_mapping_external_store_id_bb2b375f_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX drive_store_id_mapping_external_store_id_bb2b375f_like ON drive_store_id_mapping USING btree (external_store_id text_pattern_ops);


--
-- Name: drive_webhook_event_business_id_fa693da4; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX drive_webhook_event_business_id_fa693da4 ON drive_webhook_event USING btree (business_id);


--
-- Name: drive_webhook_event_delivery_event_category_id_58b3c187; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX drive_webhook_event_delivery_event_category_id_58b3c187 ON drive_webhook_event USING btree (delivery_event_category_id);


--
-- Name: drive_webhook_event_delivery_id_c9f83017; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX drive_webhook_event_delivery_id_c9f83017 ON drive_webhook_event USING btree (delivery_id);


--
-- Name: drive_webhook_subscription_business_id_63d2422c; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX drive_webhook_subscription_business_id_63d2422c ON drive_webhook_subscription USING btree (business_id);


--
-- Name: drive_webhook_subscription_delivery_event_category_id_7bcb9a6e; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX drive_webhook_subscription_delivery_event_category_id_7bcb9a6e ON drive_webhook_subscription USING btree (delivery_event_category_id);


--
-- Name: email_holdout_group_name_ce93188a; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX email_holdout_group_name_ce93188a ON email_holdout_group USING btree (name);


--
-- Name: email_holdout_group_name_ce93188a_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX email_holdout_group_name_ce93188a_like ON email_holdout_group USING btree (name text_pattern_ops);


--
-- Name: email_notification_issue_id_b3d9705a; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX email_notification_issue_id_b3d9705a ON email_notification USING btree (issue_id);


--
-- Name: email_notification_target_ct_id_3b0b1c23; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX email_notification_target_ct_id_3b0b1c23 ON email_notification USING btree (target_ct_id);


--
-- Name: email_preference_name_95ff6323; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX email_preference_name_95ff6323 ON email_preference USING btree (name);


--
-- Name: email_preference_name_95ff6323_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX email_preference_name_95ff6323_like ON email_preference USING btree (name text_pattern_ops);


--
-- Name: email_verification_request_email_4a66ff4e_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX email_verification_request_email_4a66ff4e_like ON email_verification_request USING btree (email text_pattern_ops);


--
-- Name: email_verification_request_token_0ff28bc2; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX email_verification_request_token_0ff28bc2 ON email_verification_request USING btree (token);


--
-- Name: email_verification_request_token_0ff28bc2_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX email_verification_request_token_0ff28bc2_like ON email_verification_request USING btree (token text_pattern_ops);


--
-- Name: employee_manager_id_54b357b6; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX employee_manager_id_54b357b6 ON employee USING btree (manager_id);


--
-- Name: employee_monthly_culture_shift_approved_by_id_65edf07f; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX employee_monthly_culture_shift_approved_by_id_65edf07f ON employee_monthly_culture_shift USING btree (approved_by_id);


--
-- Name: employee_monthly_culture_shift_employee_id_0fd1279f; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX employee_monthly_culture_shift_employee_id_0fd1279f ON employee_monthly_culture_shift USING btree (employee_id);


--
-- Name: employee_monthly_culture_shift_rejected_by_id_59ef7ddb; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX employee_monthly_culture_shift_rejected_by_id_59ef7ddb ON employee_monthly_culture_shift USING btree (rejected_by_id);


--
-- Name: estimate_delivery_id_f56306fe; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX estimate_delivery_id_f56306fe ON estimate USING btree (delivery_id);


--
-- Name: estimate_start_time_a02a00c9; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX estimate_start_time_a02a00c9 ON estimate USING btree (start_time);


--
-- Name: estimate_target_name_3c08253c; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX estimate_target_name_3c08253c ON estimate USING btree (target_name);


--
-- Name: estimate_target_name_3c08253c_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX estimate_target_name_3c08253c_like ON estimate USING btree (target_name varchar_pattern_ops);


--
-- Name: eta_prediction_delivery_id_4eee67c5; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX eta_prediction_delivery_id_4eee67c5 ON eta_prediction USING btree (delivery_id);


--
-- Name: eta_prediction_estimated_pickup_time_15c7bce7; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX eta_prediction_estimated_pickup_time_15c7bce7 ON eta_prediction USING btree (estimated_pickup_time);


--
-- Name: eta_prediction_is_asap_ffc4a3fb; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX eta_prediction_is_asap_ffc4a3fb ON eta_prediction USING btree (is_asap);


--
-- Name: eta_prediction_manual_pickup_time_de8830cb; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX eta_prediction_manual_pickup_time_de8830cb ON eta_prediction USING btree (manual_pickup_time);


--
-- Name: eta_prediction_order_cart_id_2df47e92; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX eta_prediction_order_cart_id_2df47e92 ON eta_prediction USING btree (order_cart_id);


--
-- Name: eta_prediction_quoted_delivery_time_fd4e4eea; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX eta_prediction_quoted_delivery_time_fd4e4eea ON eta_prediction USING btree (quoted_delivery_time);


--
-- Name: experiment2_name_f3ecbd60_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX experiment2_name_f3ecbd60_like ON experiment2 USING btree (name varchar_pattern_ops);


--
-- Name: experiment2_owner_id_5a2d472d; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX experiment2_owner_id_5a2d472d ON experiment2 USING btree (owner_id);


--
-- Name: experiment2_updated_at_e5ca8f58; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX experiment2_updated_at_e5ca8f58 ON experiment2 USING btree (updated_at);


--
-- Name: experiment_bucket_assignment_created_at_bd81d9d3; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX experiment_bucket_assignment_created_at_bd81d9d3 ON experiment_bucket_assignment USING btree (created_at);


--
-- Name: experiment_bucket_assignment_experiment_id_0b18fe1a; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX experiment_bucket_assignment_experiment_id_0b18fe1a ON experiment_bucket_assignment USING btree (experiment_id);


--
-- Name: experiment_bucket_assignment_last_accessed_at_fa9b9401; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX experiment_bucket_assignment_last_accessed_at_fa9b9401 ON experiment_bucket_assignment USING btree (last_accessed_at);


--
-- Name: experiment_bucket_assignment_user_id_b57a07cd; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX experiment_bucket_assignment_user_id_b57a07cd ON experiment_bucket_assignment USING btree (user_id);


--
-- Name: experiment_distribution_experiment_id_0eec6552; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX experiment_distribution_experiment_id_0eec6552 ON experiment_distribution USING btree (experiment_id);


--
-- Name: experiment_override_experiment_id_871b7c0b; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX experiment_override_experiment_id_871b7c0b ON experiment_override USING btree (experiment_id);


--
-- Name: experiment_override_user_id_29066c65; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX experiment_override_user_id_29066c65 ON experiment_override USING btree (user_id);


--
-- Name: experiment_version_created_at_ec0987c3; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX experiment_version_created_at_ec0987c3 ON experiment_version USING btree (created_at);


--
-- Name: experiment_version_experiment_id_85cce31c; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX experiment_version_experiment_id_85cce31c ON experiment_version USING btree (experiment_id);


--
-- Name: experiment_version_last_activated_at_1e420f82; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX experiment_version_last_activated_at_1e420f82 ON experiment_version USING btree (last_activated_at);


--
-- Name: experiment_version_updated_at_381b6948; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX experiment_version_updated_at_381b6948 ON experiment_version USING btree (updated_at);


--
-- Name: fraud_status_created_at_7e961de6; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fraud_status_created_at_7e961de6 ON fraud_status USING btree (created_at);


--
-- Name: fraud_status_entity_id_entity_type_9b40d7ca_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX fraud_status_entity_id_entity_type_9b40d7ca_idx ON fraud_status USING btree (entity_id, entity_type);


--
-- Name: gift_code_code_69d54a75_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX gift_code_code_69d54a75_like ON gift_code USING btree (code varchar_pattern_ops);


--
-- Name: gift_code_creator_id_43de49a3; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX gift_code_creator_id_43de49a3 ON gift_code USING btree (creator_id);


--
-- Name: gift_code_redeemer_id_7d769552; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX gift_code_redeemer_id_7d769552 ON gift_code USING btree (redeemer_id);


--
-- Name: globalvars_gatekeeper_name_6cddb816_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX globalvars_gatekeeper_name_6cddb816_like ON globalvars_gatekeeper USING btree (name varchar_pattern_ops);


--
-- Name: globalvars_variable_key_a18674e3_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX globalvars_variable_key_a18674e3_like ON globalvars_variable USING btree (key varchar_pattern_ops);


--
-- Name: grab_pay_account_consumer_id_5d60f2b4; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX grab_pay_account_consumer_id_5d60f2b4 ON grab_pay_account USING btree (consumer_id);


--
-- Name: grab_pay_account_idempotency_key_0f7c872f_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX grab_pay_account_idempotency_key_0f7c872f_like ON grab_pay_account USING btree (idempotency_key text_pattern_ops);


--
-- Name: grab_pay_charge_charge_id_85d087d0; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX grab_pay_charge_charge_id_85d087d0 ON grab_pay_charge USING btree (charge_id);


--
-- Name: grab_pay_charge_grab_pay_account_id_338932cc; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX grab_pay_charge_grab_pay_account_id_338932cc ON grab_pay_charge USING btree (grab_pay_account_id);


--
-- Name: grab_pay_charge_idempotency_key_46040a0e_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX grab_pay_charge_idempotency_key_46040a0e_like ON grab_pay_charge USING btree (idempotency_key text_pattern_ops);


--
-- Name: grab_payment_account_safe_id_160ce401; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX grab_payment_account_safe_id_160ce401 ON grab_payment_account USING btree (safe_id);


--
-- Name: grab_payment_account_safe_id_160ce401_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX grab_payment_account_safe_id_160ce401_like ON grab_payment_account USING btree (safe_id text_pattern_ops);


--
-- Name: grab_transfer_grab_pay_transfer_id_81822b6b; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX grab_transfer_grab_pay_transfer_id_81822b6b ON grab_transfer USING btree (grab_pay_transfer_id);


--
-- Name: grab_transfer_grab_pay_transfer_id_81822b6b_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX grab_transfer_grab_pay_transfer_id_81822b6b_like ON grab_transfer USING btree (grab_pay_transfer_id varchar_pattern_ops);


--
-- Name: grab_transfer_idempotency_key_24964e23; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX grab_transfer_idempotency_key_24964e23 ON grab_transfer USING btree (idempotency_key);


--
-- Name: grab_transfer_idempotency_key_24964e23_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX grab_transfer_idempotency_key_24964e23_like ON grab_transfer USING btree (idempotency_key text_pattern_ops);


--
-- Name: grab_transfer_original_grab_pay_transfer_id_a105b2b2; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX grab_transfer_original_grab_pay_transfer_id_a105b2b2 ON grab_transfer USING btree (original_grab_pay_transfer_id);


--
-- Name: grab_transfer_original_grab_pay_transfer_id_a105b2b2_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX grab_transfer_original_grab_pay_transfer_id_a105b2b2_like ON grab_transfer USING btree (original_grab_pay_transfer_id text_pattern_ops);


--
-- Name: grab_transfer_transfer_id_a0a525c2; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX grab_transfer_transfer_id_a0a525c2 ON grab_transfer USING btree (transfer_id);


--
-- Name: invoicing_group_membership_invoicing_group_id_f47521fb; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX invoicing_group_membership_invoicing_group_id_f47521fb ON invoicing_group_membership USING btree (invoicing_group_id);


--
-- Name: invoicing_group_onboarding_rule_invoicing_group_id_b471e097; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX invoicing_group_onboarding_rule_invoicing_group_id_b471e097 ON invoicing_group_onboarding_rule USING btree (invoicing_group_id);


--
-- Name: ios_notifications_device_service_id_d82269bf; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ios_notifications_device_service_id_d82269bf ON ios_notifications_device USING btree (service_id);


--
-- Name: ios_notifications_device_users_device_id_d0bddd71; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ios_notifications_device_users_device_id_d0bddd71 ON ios_notifications_device_users USING btree (device_id);


--
-- Name: ios_notifications_device_users_user_id_c84b371e; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ios_notifications_device_users_user_id_c84b371e ON ios_notifications_device_users USING btree (user_id);


--
-- Name: ios_notifications_feedbackservice_apn_service_id_2db1f5ae; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ios_notifications_feedbackservice_apn_service_id_2db1f5ae ON ios_notifications_feedbackservice USING btree (apn_service_id);


--
-- Name: ios_notifications_notification_service_id_a25fb97e; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ios_notifications_notification_service_id_a25fb97e ON ios_notifications_notification USING btree (service_id);


--
-- Name: kill_switch_interval_killed_by_id_ed281167; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX kill_switch_interval_killed_by_id_ed281167 ON kill_switch_interval USING btree (killed_by_id);


--
-- Name: kill_switch_interval_starting_point_id_8d2b568e; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX kill_switch_interval_starting_point_id_8d2b568e ON kill_switch_interval USING btree (starting_point_id);


--
-- Name: kill_switch_interval_unkilled_by_id_1624bdc7; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX kill_switch_interval_unkilled_by_id_1624bdc7 ON kill_switch_interval USING btree (unkilled_by_id);


--
-- Name: managed_account_transfer_account_ct_id_94a5852f; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX managed_account_transfer_account_ct_id_94a5852f ON managed_account_transfer USING btree (account_ct_id);


--
-- Name: managed_account_transfer_payment_account_id_18c55c14; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX managed_account_transfer_payment_account_id_18c55c14 ON managed_account_transfer USING btree (payment_account_id);


--
-- Name: market_bounds_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX market_bounds_id ON market USING gist (bounds);


--
-- Name: market_center_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX market_center_id ON market USING gist (center);


--
-- Name: market_country_id_d94abd98; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX market_country_id_d94abd98 ON market USING btree (country_id);


--
-- Name: market_name_d6c6496a_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX market_name_d6c6496a_like ON market USING btree (name varchar_pattern_ops);


--
-- Name: market_region_id_c8b496df; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX market_region_id_c8b496df ON market USING btree (region_id);


--
-- Name: market_shortname_01bafce3_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX market_shortname_01bafce3_like ON market USING btree (shortname varchar_pattern_ops);


--
-- Name: market_special_hours_market_id_fd60d9f6; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX market_special_hours_market_id_fd60d9f6 ON market_special_hours USING btree (market_id);


--
-- Name: market_subnational_division_id_f438906a; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX market_subnational_division_id_f438906a ON market USING btree (subnational_division_id);


--
-- Name: market_virtual_orientation_slide_deck_bikes_only_id_fb7ac097; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX market_virtual_orientation_slide_deck_bikes_only_id_fb7ac097 ON market USING btree (virtual_orientation_slide_deck_bikes_only_id);


--
-- Name: market_virtual_orientation_slide_deck_id_9a66014b; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX market_virtual_orientation_slide_deck_id_9a66014b ON market USING btree (virtual_orientation_slide_deck_id);


--
-- Name: marqeta_card_ownership_card_id_b7e17995; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX marqeta_card_ownership_card_id_b7e17995 ON marqeta_card_ownership USING btree (card_id);


--
-- Name: marqeta_card_ownership_card_id_b7e17995_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX marqeta_card_ownership_card_id_b7e17995_like ON marqeta_card_ownership USING btree (card_id varchar_pattern_ops);


--
-- Name: marqeta_card_ownership_dasher_id_4d5e8234; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX marqeta_card_ownership_dasher_id_4d5e8234 ON marqeta_card_ownership USING btree (dasher_id);


--
-- Name: marqeta_card_token_fc218f76_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX marqeta_card_token_fc218f76_like ON marqeta_card USING btree (token varchar_pattern_ops);


--
-- Name: marqeta_card_transition_aborted_at_e9ae161f; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX marqeta_card_transition_aborted_at_e9ae161f ON marqeta_card_transition USING btree (aborted_at);


--
-- Name: marqeta_card_transition_card_id_4bf68626; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX marqeta_card_transition_card_id_4bf68626 ON marqeta_card_transition USING btree (card_id);


--
-- Name: marqeta_card_transition_card_id_4bf68626_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX marqeta_card_transition_card_id_4bf68626_like ON marqeta_card_transition USING btree (card_id varchar_pattern_ops);


--
-- Name: marqeta_card_transition_shift_id_842a8328; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX marqeta_card_transition_shift_id_842a8328 ON marqeta_card_transition USING btree (shift_id);


--
-- Name: marqeta_card_transition_succeeded_at_e11c3482; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX marqeta_card_transition_succeeded_at_e11c3482 ON marqeta_card_transition USING btree (succeeded_at);


--
-- Name: marqeta_decline_exemption_created_by_id_c420d085; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX marqeta_decline_exemption_created_by_id_c420d085 ON marqeta_decline_exemption USING btree (created_by_id);


--
-- Name: marqeta_decline_exemption_delivery_id_fe7d3d75; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX marqeta_decline_exemption_delivery_id_fe7d3d75 ON marqeta_decline_exemption USING btree (delivery_id);


--
-- Name: marqeta_transaction_delivery_id_31f7adaf; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX marqeta_transaction_delivery_id_31f7adaf ON marqeta_transaction USING btree (delivery_id);


--
-- Name: marqeta_transaction_event_card_acceptor_id_a86839c1; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX marqeta_transaction_event_card_acceptor_id_a86839c1 ON marqeta_transaction_event USING btree (card_acceptor_id);


--
-- Name: marqeta_transaction_event_ownership_id_e3b46982; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX marqeta_transaction_event_ownership_id_e3b46982 ON marqeta_transaction_event USING btree (ownership_id);


--
-- Name: marqeta_transaction_event_shift_id_66da2655; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX marqeta_transaction_event_shift_id_66da2655 ON marqeta_transaction_event USING btree (shift_id);


--
-- Name: marqeta_transaction_event_token_715fe268_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX marqeta_transaction_event_token_715fe268_like ON marqeta_transaction_event USING btree (token varchar_pattern_ops);


--
-- Name: marqeta_transaction_token_650bc5e3_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX marqeta_transaction_token_650bc5e3_like ON marqeta_transaction USING btree (token text_pattern_ops);


--
-- Name: mass_communication_status_message_uuid_ffe0fd23_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX mass_communication_status_message_uuid_ffe0fd23_like ON mass_communication_status USING btree (message_uuid varchar_pattern_ops);


--
-- Name: mass_communication_status_sender_id_a8e8f447; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX mass_communication_status_sender_id_a8e8f447 ON mass_communication_status USING btree (sender_id);


--
-- Name: order_cart_business_referral_id_ff3e44eb; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX order_cart_business_referral_id_ff3e44eb ON order_cart USING btree (business_referral_id);


--
-- Name: order_cart_consumer_promot_consumer_promotion_id_6aa3f2fb; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX order_cart_consumer_promot_consumer_promotion_id_6aa3f2fb ON order_cart_consumer_promotion_link USING btree (consumer_promotion_id);


--
-- Name: order_cart_consumer_promotion_link_order_cart_id_5a6f0361; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX order_cart_consumer_promotion_link_order_cart_id_5a6f0361 ON order_cart_consumer_promotion_link USING btree (order_cart_id);


--
-- Name: order_cart_creator_id_8172b8ff; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX order_cart_creator_id_8172b8ff ON order_cart USING btree (creator_id);


--
-- Name: order_cart_delivery_address_id_a6942a1b; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX order_cart_delivery_address_id_a6942a1b ON order_cart USING btree (delivery_address_id);


--
-- Name: order_cart_device_fingerprint_link_fingerprint_id_225dc7b1; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX order_cart_device_fingerprint_link_fingerprint_id_225dc7b1 ON order_cart_device_fingerprint_link USING btree (fingerprint_id);


--
-- Name: order_cart_device_fingerprint_link_order_cart_id_f4d640e5; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX order_cart_device_fingerprint_link_order_cart_id_f4d640e5 ON order_cart_device_fingerprint_link USING btree (order_cart_id);


--
-- Name: order_cart_discount_component_order_cart_id_fe63fa63; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX order_cart_discount_component_order_cart_id_fe63fa63 ON order_cart_discount_component USING btree (order_cart_id);


--
-- Name: order_cart_discount_component_source_id_68b064ff; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX order_cart_discount_component_source_id_68b064ff ON order_cart_discount_component USING btree (source_id);


--
-- Name: order_cart_discount_component_source_type_name_1a6b13eb_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX order_cart_discount_component_source_type_name_1a6b13eb_like ON order_cart_discount_component_source_type USING btree (name text_pattern_ops);


--
-- Name: order_cart_discount_component_store_order_cart_id_da9e8891; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX order_cart_discount_component_store_order_cart_id_da9e8891 ON order_cart_discount_component USING btree (store_order_cart_id);


--
-- Name: order_cart_escalation_reason_escalation_id_f62b9290; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX order_cart_escalation_reason_escalation_id_f62b9290 ON order_cart_escalation_reason USING btree (escalation_id);


--
-- Name: order_cart_escalation_reviewed_by_id_2adb162a; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX order_cart_escalation_reviewed_by_id_2adb162a ON order_cart_escalation USING btree (reviewed_by_id);


--
-- Name: order_cart_is_first_ordercart_359ceefd; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX order_cart_is_first_ordercart_359ceefd ON order_cart USING btree (is_first_ordercart);


--
-- Name: order_cart_locked_6a7183d8; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX order_cart_locked_6a7183d8 ON order_cart USING btree (locked);


--
-- Name: order_cart_pricing_strategy_strategy_type_a8823f5c_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX order_cart_pricing_strategy_strategy_type_a8823f5c_like ON order_cart_pricing_strategy USING btree (strategy_type text_pattern_ops);


--
-- Name: order_cart_promo_code_id_1975069c; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX order_cart_promo_code_id_1975069c ON order_cart USING btree (promo_code_id);


--
-- Name: order_cart_submitted_at_3310b944; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX order_cart_submitted_at_3310b944 ON order_cart USING btree (submitted_at);


--
-- Name: order_cart_url_code_cb618ccc_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX order_cart_url_code_cb618ccc_like ON order_cart USING btree (url_code varchar_pattern_ops);


--
-- Name: order_consumer_id_a83b8db3; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX order_consumer_id_a83b8db3 ON "order" USING btree (consumer_id);


--
-- Name: order_item_extra_option_item_extra_option_id_baa0519e; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX order_item_extra_option_item_extra_option_id_baa0519e ON order_item_extra_option USING btree (item_extra_option_id);


--
-- Name: order_item_extra_option_order_item_id_227a2aaa; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX order_item_extra_option_order_item_id_227a2aaa ON order_item_extra_option USING btree (order_item_id);


--
-- Name: order_item_extra_option_parent_order_item_extra_op_267787b0; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX order_item_extra_option_parent_order_item_extra_op_267787b0 ON order_item_extra_option USING btree (parent_order_item_extra_option_id);


--
-- Name: order_item_item_id_00cc36f1; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX order_item_item_id_00cc36f1 ON order_item USING btree (item_id);


--
-- Name: order_item_order_id_0ca9e92e; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX order_item_order_id_0ca9e92e ON order_item USING btree (order_id);


--
-- Name: order_item_store_id_a042aa5a; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX order_item_store_id_a042aa5a ON order_item USING btree (store_id);


--
-- Name: order_menu_id_cb824fba; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX order_menu_id_cb824fba ON "order" USING btree (menu_id);


--
-- Name: order_menu_option_option_id_d1729bf1; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX order_menu_option_option_id_d1729bf1 ON order_menu_option USING btree (option_id);


--
-- Name: order_menu_option_order_id_d7c52c26; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX order_menu_option_order_id_d7c52c26 ON order_menu_option USING btree (order_id);


--
-- Name: order_order_cart_id_02676457; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX order_order_cart_id_02676457 ON "order" USING btree (order_cart_id);


--
-- Name: order_store_id_cbdb127f; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX order_store_id_cbdb127f ON "order" USING btree (store_id);


--
-- Name: order_store_order_cart_id_3d2d99da; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX order_store_order_cart_id_3d2d99da ON "order" USING btree (store_order_cart_id);


--
-- Name: payment_account_account_type_account_id_eef0b926_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX payment_account_account_type_account_id_eef0b926_idx ON payment_account USING btree (account_type, account_id);


--
-- Name: payment_account_charges_enabled_3bcad396; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX payment_account_charges_enabled_3bcad396 ON payment_account USING btree (charges_enabled);


--
-- Name: payment_account_is_verified_with_stripe_c11ce5e2; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX payment_account_is_verified_with_stripe_c11ce5e2 ON payment_account USING btree (is_verified_with_stripe);


--
-- Name: payment_account_resolve_outstanding_bala_0da3cc8f_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX payment_account_resolve_outstanding_bala_0da3cc8f_like ON payment_account USING btree (resolve_outstanding_balance_frequency text_pattern_ops);


--
-- Name: payment_account_resolve_outstanding_balance_frequency_0da3cc8f; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX payment_account_resolve_outstanding_balance_frequency_0da3cc8f ON payment_account USING btree (resolve_outstanding_balance_frequency);


--
-- Name: payment_account_transfers_enabled_05601ccc; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX payment_account_transfers_enabled_05601ccc ON payment_account USING btree (transfers_enabled);


--
-- Name: place_tag_name_a05b253a_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX place_tag_name_a05b253a_like ON place_tag USING btree (name varchar_pattern_ops);


--
-- Name: platform_name_71243fe8; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX platform_name_71243fe8 ON platform USING btree (name);


--
-- Name: platform_name_71243fe8_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX platform_name_71243fe8_like ON platform USING btree (name text_pattern_ops);


--
-- Name: promo_code_code_d56f658d_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX promo_code_code_d56f658d_like ON promo_code USING btree (code varchar_pattern_ops);


--
-- Name: promo_code_consumer_link_consumer_id_f9423f56; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX promo_code_consumer_link_consumer_id_f9423f56 ON promo_code_consumer_link USING btree (consumer_id);


--
-- Name: promo_code_consumer_link_promo_code_id_a4fc4562; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX promo_code_consumer_link_promo_code_id_a4fc4562 ON promo_code_consumer_link USING btree (promo_code_id);


--
-- Name: promo_code_markets_market_id_83fce76d; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX promo_code_markets_market_id_83fce76d ON promo_code_markets USING btree (market_id);


--
-- Name: promo_code_markets_promocode_id_32101512; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX promo_code_markets_promocode_id_32101512 ON promo_code_markets USING btree (promocode_id);


--
-- Name: promo_code_submarket_link_promo_code_id_ca91eba3; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX promo_code_submarket_link_promo_code_id_ca91eba3 ON promo_code_submarket_link USING btree (promo_code_id);


--
-- Name: promo_code_submarket_link_submarket_id_09afa639; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX promo_code_submarket_link_submarket_id_09afa639 ON promo_code_submarket_link USING btree (submarket_id);


--
-- Name: promotion_consumer_link_consumer_id_a56783f8; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX promotion_consumer_link_consumer_id_a56783f8 ON promotion_consumer_link USING btree (consumer_id);


--
-- Name: promotion_consumer_link_promotion_id_0dc3fdcd; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX promotion_consumer_link_promotion_id_0dc3fdcd ON promotion_consumer_link USING btree (promotion_id);


--
-- Name: promotion_featured_location_link_featured_location_id_d014d016; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX promotion_featured_location_link_featured_location_id_d014d016 ON promotion_featured_location_link USING btree (featured_location_id);


--
-- Name: promotion_featured_location_link_promotion_id_b3c8d310; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX promotion_featured_location_link_promotion_id_b3c8d310 ON promotion_featured_location_link USING btree (promotion_id);


--
-- Name: promotion_place_tag_link_place_tag_id_49472528; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX promotion_place_tag_link_place_tag_id_49472528 ON promotion_place_tag_link USING btree (place_tag_id);


--
-- Name: promotion_place_tag_link_promotion_id_05aa6564; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX promotion_place_tag_link_promotion_id_05aa6564 ON promotion_place_tag_link USING btree (promotion_id);


--
-- Name: promotion_redemption_event_order_cart_id_f99f63f6; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX promotion_redemption_event_order_cart_id_f99f63f6 ON promotion_redemption_event USING btree (order_cart_id);


--
-- Name: promotion_redemption_event_promotion_campaign_id_40cbe5e5; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX promotion_redemption_event_promotion_campaign_id_40cbe5e5 ON promotion_redemption_event USING btree (promotion_campaign_id);


--
-- Name: promotion_redemption_event_promotion_id_4a71099f; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX promotion_redemption_event_promotion_id_4a71099f ON promotion_redemption_event USING btree (promotion_id);


--
-- Name: promotion_redemption_event_region_id_3e067e19; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX promotion_redemption_event_region_id_3e067e19 ON promotion_redemption_event USING btree (region_id);


--
-- Name: promotion_redemption_event_store_id_32c7a708; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX promotion_redemption_event_store_id_32c7a708 ON promotion_redemption_event USING btree (store_id);


--
-- Name: promotion_redemption_event_timezone_fd3941c3; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX promotion_redemption_event_timezone_fd3941c3 ON promotion_redemption_event USING btree (timezone);


--
-- Name: promotion_redemption_event_timezone_fd3941c3_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX promotion_redemption_event_timezone_fd3941c3_like ON promotion_redemption_event USING btree (timezone varchar_pattern_ops);


--
-- Name: promotion_submarket_link_promotion_id_4a612f03; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX promotion_submarket_link_promotion_id_4a612f03 ON promotion_submarket_link USING btree (promotion_id);


--
-- Name: promotion_submarket_link_submarket_id_e9e0ad13; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX promotion_submarket_link_submarket_id_e9e0ad13 ON promotion_submarket_link USING btree (submarket_id);


--
-- Name: promotions_featured_location_next_featured_location_id_e2bc2b66; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX promotions_featured_location_next_featured_location_id_e2bc2b66 ON promotions_featured_location USING btree (next_featured_location_id);


--
-- Name: real_time_supply_model_starting_point_id_73a647eb; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX real_time_supply_model_starting_point_id_73a647eb ON real_time_supply_model USING btree (starting_point_id);


--
-- Name: real_time_supply_prediction_starting_point_id_a07911de; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX real_time_supply_prediction_starting_point_id_a07911de ON real_time_supply_prediction USING btree (starting_point_id);


--
-- Name: real_time_supply_prediction_supply_model_id_3d4c16c8; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX real_time_supply_prediction_supply_model_id_3d4c16c8 ON real_time_supply_prediction USING btree (supply_model_id);


--
-- Name: realtime_demand_evaluation_active_date_c1422cff; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX realtime_demand_evaluation_active_date_c1422cff ON realtime_demand_evaluation USING btree (active_date);


--
-- Name: realtime_demand_evaluation_created_at_e336e7d9; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX realtime_demand_evaluation_created_at_e336e7d9 ON realtime_demand_evaluation USING btree (created_at);


--
-- Name: realtime_demand_evaluation_starting_point_id_faf727ab; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX realtime_demand_evaluation_starting_point_id_faf727ab ON realtime_demand_evaluation USING btree (starting_point_id);


--
-- Name: refresh_token_key_3efb10fd_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX refresh_token_key_3efb10fd_like ON refresh_token USING btree (key varchar_pattern_ops);


--
-- Name: refresh_token_user_id_1d7a63ac; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX refresh_token_user_id_1d7a63ac ON refresh_token USING btree (user_id);


--
-- Name: region_country_id_f136eca4; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX region_country_id_f136eca4 ON region USING btree (country_id);


--
-- Name: region_shortname_0da82a39_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX region_shortname_0da82a39_like ON region USING btree (shortname text_pattern_ops);


--
-- Name: region_snapshot_date_03e16d9a; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX region_snapshot_date_03e16d9a ON region_snapshot USING btree (date);


--
-- Name: region_snapshot_district_id_b2335253; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX region_snapshot_district_id_b2335253 ON region_snapshot USING btree (district_id);


--
-- Name: region_snapshot_starting_point_id_06fac4a8; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX region_snapshot_starting_point_id_06fac4a8 ON region_snapshot USING btree (starting_point_id);


--
-- Name: scheduled_caps_boost_starting_point_id_2058452a; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX scheduled_caps_boost_starting_point_id_2058452a ON scheduled_caps_boost USING btree (starting_point_id);


--
-- Name: search_engine_store_feed_starting_point_id_cfb57fa4; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX search_engine_store_feed_starting_point_id_cfb57fa4 ON search_engine_store_feed USING btree (starting_point_id);


--
-- Name: search_engine_store_feed_store_id_682bbb30; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX search_engine_store_feed_store_id_682bbb30 ON search_engine_store_feed USING btree (store_id);


--
-- Name: seo_local_region_center_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX seo_local_region_center_id ON seo_local_region USING gist (center);


--
-- Name: seo_local_region_city_id_50f7b946; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX seo_local_region_city_id_50f7b946 ON seo_local_region USING btree (city_id);


--
-- Name: shortened_url_expanded_url_8588cd1c_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX shortened_url_expanded_url_8588cd1c_like ON shortened_url USING btree (expanded_url text_pattern_ops);


--
-- Name: shortened_url_url_code_5e68b84a_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX shortened_url_url_code_5e68b84a_like ON shortened_url USING btree (url_code text_pattern_ops);


--
-- Name: sms_help_message_status_phone_number_29cbe1b1_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX sms_help_message_status_phone_number_29cbe1b1_like ON sms_help_message_status USING btree (phone_number varchar_pattern_ops);


--
-- Name: sms_help_message_status_user_id_6217acd5; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX sms_help_message_status_user_id_6217acd5 ON sms_help_message_status USING btree (user_id);


--
-- Name: sms_opt_out_number_phone_number_08c567ac_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX sms_opt_out_number_phone_number_08c567ac_like ON sms_opt_out_number USING btree (phone_number varchar_pattern_ops);


--
-- Name: starship_delivery_info_delivery_id_2e5e8e7d; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX starship_delivery_info_delivery_id_2e5e8e7d ON starship_delivery_info USING btree (delivery_id);


--
-- Name: starship_delivery_info_starship_delivery_id_1cbe8655; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX starship_delivery_info_starship_delivery_id_1cbe8655 ON starship_delivery_info USING btree (starship_delivery_id);


--
-- Name: starship_delivery_info_starship_delivery_id_1cbe8655_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX starship_delivery_info_starship_delivery_id_1cbe8655_like ON starship_delivery_info USING btree (starship_delivery_id text_pattern_ops);


--
-- Name: starship_delivery_info_tracking_be796857_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX starship_delivery_info_tracking_be796857_like ON starship_delivery_info USING btree (tracking text_pattern_ops);


--
-- Name: starting_point_activation_time_da9a416f; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX starting_point_activation_time_da9a416f ON starting_point USING btree (activation_time);


--
-- Name: starting_point_assignment__starting_point_id_bea987a6; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX starting_point_assignment__starting_point_id_bea987a6 ON starting_point_assignment_latency_stats USING btree (starting_point_id);


--
-- Name: starting_point_assignment_latency_stats_active_date_74db1fe8; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX starting_point_assignment_latency_stats_active_date_74db1fe8 ON starting_point_assignment_latency_stats USING btree (active_date);


--
-- Name: starting_point_deactivation_time_27976126; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX starting_point_deactivation_time_27976126 ON starting_point USING btree (deactivation_time);


--
-- Name: starting_point_delivery_du_starting_point_id_34606949; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX starting_point_delivery_du_starting_point_id_34606949 ON starting_point_delivery_duration_stats USING btree (starting_point_id);


--
-- Name: starting_point_delivery_duration_stats_active_date_69651a6e; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX starting_point_delivery_duration_stats_active_date_69651a6e ON starting_point_delivery_duration_stats USING btree (active_date);


--
-- Name: starting_point_delivery_hours_starting_point_id_404ae42b; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX starting_point_delivery_hours_starting_point_id_404ae42b ON starting_point_delivery_hours USING btree (starting_point_id);


--
-- Name: starting_point_geometry_geom_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX starting_point_geometry_geom_id ON starting_point_geometry USING gist (geom);


--
-- Name: starting_point_html_color_f44a8f6e_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX starting_point_html_color_f44a8f6e_like ON starting_point USING btree (html_color varchar_pattern_ops);


--
-- Name: starting_point_market_id_8e3f1497; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX starting_point_market_id_8e3f1497 ON starting_point USING btree (market_id);


--
-- Name: starting_point_r2c_stats_active_date_dcc7d454; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX starting_point_r2c_stats_active_date_dcc7d454 ON starting_point_r2c_stats USING btree (active_date);


--
-- Name: starting_point_r2c_stats_starting_point_id_7a965846; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX starting_point_r2c_stats_starting_point_id_7a965846 ON starting_point_r2c_stats USING btree (starting_point_id);


--
-- Name: starting_point_set_market_id_f3c05e7e; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX starting_point_set_market_id_f3c05e7e ON starting_point_set USING btree (market_id);


--
-- Name: starting_point_set_updated_at_dff13cdc; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX starting_point_set_updated_at_dff13cdc ON starting_point_set USING btree (updated_at);


--
-- Name: starting_point_shortname_a45f013e_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX starting_point_shortname_a45f013e_like ON starting_point USING btree (shortname varchar_pattern_ops);


--
-- Name: starting_point_submarket_id_1367e594; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX starting_point_submarket_id_1367e594 ON starting_point USING btree (submarket_id);


--
-- Name: store_confirmed_time_snapshot_active_date_701a8e78; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX store_confirmed_time_snapshot_active_date_701a8e78 ON store_confirmed_time_snapshot USING btree (active_date);


--
-- Name: store_confirmed_time_snapshot_created_at_b5a06c74; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX store_confirmed_time_snapshot_created_at_b5a06c74 ON store_confirmed_time_snapshot USING btree (created_at);


--
-- Name: store_consumer_review_consumer_id_41acc1e2; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX store_consumer_review_consumer_id_41acc1e2 ON store_consumer_review USING btree (consumer_id);


--
-- Name: store_consumer_review_created_at_61b6f16a; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX store_consumer_review_created_at_61b6f16a ON store_consumer_review USING btree (created_at);


--
-- Name: store_consumer_review_rating_def9eb41; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX store_consumer_review_rating_def9eb41 ON store_consumer_review USING btree (rating);


--
-- Name: store_consumer_review_store_id_b6428b9e; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX store_consumer_review_store_id_b6428b9e ON store_consumer_review USING btree (store_id);


--
-- Name: store_consumer_review_tag_link_review_id_751fd5cb; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX store_consumer_review_tag_link_review_id_751fd5cb ON store_consumer_review_tag_link USING btree (review_id);


--
-- Name: store_consumer_review_tag_link_tag_id_3c72815d; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX store_consumer_review_tag_link_tag_id_3c72815d ON store_consumer_review_tag_link USING btree (tag_id);


--
-- Name: store_consumer_review_tag_name_ab6eadde_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX store_consumer_review_tag_name_ab6eadde_like ON store_consumer_review_tag USING btree (name text_pattern_ops);


--
-- Name: store_delivery_duration_stats_active_date_c0daa50d; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX store_delivery_duration_stats_active_date_c0daa50d ON store_delivery_duration_stats USING btree (active_date);


--
-- Name: store_delivery_duration_stats_store_id_3b127faa; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX store_delivery_duration_stats_store_id_3b127faa ON store_delivery_duration_stats USING btree (store_id);


--
-- Name: store_mastercard_data_store_id_e27449db; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX store_mastercard_data_store_id_e27449db ON store_mastercard_data USING btree (store_id);


--
-- Name: store_netsuite_customer_link_netsuite_entity_id_8cca8cda_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX store_netsuite_customer_link_netsuite_entity_id_8cca8cda_like ON store_netsuite_customer_link USING btree (netsuite_entity_id text_pattern_ops);


--
-- Name: store_order_cart_menu_id_cd8e4c2b; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX store_order_cart_menu_id_cd8e4c2b ON store_order_cart USING btree (menu_id);


--
-- Name: store_order_cart_order_cart_id_595cd0d6; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX store_order_cart_order_cart_id_595cd0d6 ON store_order_cart USING btree (order_cart_id);


--
-- Name: store_order_cart_store_id_cffd9329; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX store_order_cart_store_id_cffd9329 ON store_order_cart USING btree (store_id);


--
-- Name: store_order_place_latency_stats_active_date_38f9e1fe; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX store_order_place_latency_stats_active_date_38f9e1fe ON store_order_place_latency_stats USING btree (active_date);


--
-- Name: store_order_place_latency_stats_store_id_7f08141e; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX store_order_place_latency_stats_store_id_7f08141e ON store_order_place_latency_stats USING btree (store_id);


--
-- Name: store_point_of_sale_tran_store_transaction_id_3b33a959_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX store_point_of_sale_tran_store_transaction_id_3b33a959_like ON store_point_of_sale_transaction USING btree (store_transaction_id text_pattern_ops);


--
-- Name: store_point_of_sale_transaction_store_transaction_id_3b33a959; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX store_point_of_sale_transaction_store_transaction_id_3b33a959 ON store_point_of_sale_transaction USING btree (store_transaction_id);


--
-- Name: stripe_bank_account_active_0ef7c741; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX stripe_bank_account_active_0ef7c741 ON stripe_bank_account USING btree (active);


--
-- Name: stripe_card_active_e470b6f9; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX stripe_card_active_e470b6f9 ON stripe_card USING btree (active);


--
-- Name: stripe_card_consumer_id_043b0b95; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX stripe_card_consumer_id_043b0b95 ON stripe_card USING btree (consumer_id);


--
-- Name: stripe_card_event_consumer_id_d0bb5239; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX stripe_card_event_consumer_id_d0bb5239 ON stripe_card_event USING btree (consumer_id);


--
-- Name: stripe_card_stripe_customer_id_06dd873c; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX stripe_card_stripe_customer_id_06dd873c ON stripe_card USING btree (stripe_customer_id);


--
-- Name: stripe_card_stripe_id_1dc0899f_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX stripe_card_stripe_id_1dc0899f_like ON stripe_card USING btree (stripe_id varchar_pattern_ops);


--
-- Name: stripe_charge_card_id_47885fdf; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX stripe_charge_card_id_47885fdf ON stripe_charge USING btree (card_id);


--
-- Name: stripe_charge_charge_id_672b9190; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX stripe_charge_charge_id_672b9190 ON stripe_charge USING btree (charge_id);


--
-- Name: stripe_charge_stripe_id_87d40e11; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX stripe_charge_stripe_id_87d40e11 ON stripe_charge USING btree (stripe_id);


--
-- Name: stripe_charge_stripe_id_87d40e11_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX stripe_charge_stripe_id_87d40e11_like ON stripe_charge USING btree (stripe_id varchar_pattern_ops);


--
-- Name: stripe_dispute_stripe_card_id_ab2f0c08; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX stripe_dispute_stripe_card_id_ab2f0c08 ON stripe_dispute USING btree (stripe_card_id);


--
-- Name: stripe_dispute_stripe_charge_id_da15e7b2; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX stripe_dispute_stripe_charge_id_da15e7b2 ON stripe_dispute USING btree (stripe_charge_id);


--
-- Name: stripe_dispute_stripe_dispute_id_5e1f427d_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX stripe_dispute_stripe_dispute_id_5e1f427d_like ON stripe_dispute USING btree (stripe_dispute_id text_pattern_ops);


--
-- Name: stripe_managed_account_stripe_id_9f94047a; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX stripe_managed_account_stripe_id_9f94047a ON stripe_managed_account USING btree (stripe_id);


--
-- Name: stripe_managed_account_stripe_id_9f94047a_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX stripe_managed_account_stripe_id_9f94047a_like ON stripe_managed_account USING btree (stripe_id text_pattern_ops);


--
-- Name: stripe_recipient_stripe_id_f02bf121; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX stripe_recipient_stripe_id_f02bf121 ON stripe_recipient USING btree (stripe_id);


--
-- Name: stripe_recipient_stripe_id_f02bf121_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX stripe_recipient_stripe_id_f02bf121_like ON stripe_recipient USING btree (stripe_id text_pattern_ops);


--
-- Name: stripe_transfer_stripe_id_ededa59b; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX stripe_transfer_stripe_id_ededa59b ON stripe_transfer USING btree (stripe_id);


--
-- Name: stripe_transfer_stripe_id_ededa59b_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX stripe_transfer_stripe_id_ededa59b_like ON stripe_transfer USING btree (stripe_id varchar_pattern_ops);


--
-- Name: stripe_transfer_transfer_id_57913c98; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX stripe_transfer_transfer_id_57913c98 ON stripe_transfer USING btree (transfer_id);


--
-- Name: submarket_market_id_ff4223ec; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX submarket_market_id_ff4223ec ON submarket USING btree (market_id);


--
-- Name: submarket_name_f89b3729_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX submarket_name_f89b3729_like ON submarket USING btree (name varchar_pattern_ops);


--
-- Name: submarket_referral_program_id_2518371f; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX submarket_referral_program_id_2518371f ON submarket USING btree (referral_program_id);


--
-- Name: submarket_slug_a23ee195_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX submarket_slug_a23ee195_like ON submarket USING btree (slug varchar_pattern_ops);


--
-- Name: subnational_division_country_id_02d40283; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX subnational_division_country_id_02d40283 ON subnational_division USING btree (country_id);


--
-- Name: subnational_division_shortname_23dca994_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX subnational_division_shortname_23dca994_like ON subnational_division USING btree (shortname varchar_pattern_ops);


--
-- Name: support_salesforce_case_record_case_number_fa049aef_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX support_salesforce_case_record_case_number_fa049aef_like ON support_salesforce_case_record USING btree (case_number text_pattern_ops);


--
-- Name: support_salesforce_case_record_case_uid_d9f51900_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX support_salesforce_case_record_case_uid_d9f51900_like ON support_salesforce_case_record USING btree (case_uid text_pattern_ops);


--
-- Name: support_salesforce_case_record_delivery_id_ed7b369b; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX support_salesforce_case_record_delivery_id_ed7b369b ON support_salesforce_case_record USING btree (delivery_id);


--
-- Name: transfer_payment_account_id_b229cea5; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX transfer_payment_account_id_b229cea5 ON transfer USING btree (payment_account_id);


--
-- Name: transfer_recipient_ct_id_d955a1ae; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX transfer_recipient_ct_id_d955a1ae ON transfer USING btree (recipient_ct_id);


--
-- Name: transfer_status_21026cd9; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX transfer_status_21026cd9 ON transfer USING btree (status);


--
-- Name: transfer_status_21026cd9_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX transfer_status_21026cd9_like ON transfer USING btree (status text_pattern_ops);


--
-- Name: twilio_masking_number_assi_twilio_masking_number_id_a26d7984; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX twilio_masking_number_assi_twilio_masking_number_id_a26d7984 ON twilio_masking_number_assignment USING btree (twilio_masking_number_id);


--
-- Name: twilio_masking_number_assignment_created_at_19037ad0; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX twilio_masking_number_assignment_created_at_19037ad0 ON twilio_masking_number_assignment USING btree (created_at);


--
-- Name: twilio_number_country_id_49d13740; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX twilio_number_country_id_49d13740 ON twilio_number USING btree (country_id);


--
-- Name: twilio_number_phone_sid_7fe8bb3c_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX twilio_number_phone_sid_7fe8bb3c_like ON twilio_number USING btree (phone_sid varchar_pattern_ops);


--
-- Name: user_activation_change_event_changed_by_id_5d3e4cc7; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX user_activation_change_event_changed_by_id_5d3e4cc7 ON user_activation_change_event USING btree (changed_by_id);


--
-- Name: user_activation_change_event_user_id_3af7e91c; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX user_activation_change_event_user_id_3af7e91c ON user_activation_change_event USING btree (user_id);


--
-- Name: user_device_fingerprint_link_fingerprint_id_74d6d034; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX user_device_fingerprint_link_fingerprint_id_74d6d034 ON user_device_fingerprint_link USING btree (fingerprint_id);


--
-- Name: user_device_fingerprint_link_user_id_c4d59d93; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX user_device_fingerprint_link_user_id_c4d59d93 ON user_device_fingerprint_link USING btree (user_id);


--
-- Name: user_email_54dc62b2_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX user_email_54dc62b2_like ON "user" USING btree (email varchar_pattern_ops);


--
-- Name: user_group_admin _group_id_9a479256; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "user_group_admin _group_id_9a479256" ON "user_group_admin " USING btree (group_id);


--
-- Name: user_group_admin _user_id_2d389e35; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "user_group_admin _user_id_2d389e35" ON "user_group_admin " USING btree (user_id);


--
-- Name: user_groups_group_id_b76f8aba; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX user_groups_group_id_b76f8aba ON user_groups USING btree (group_id);


--
-- Name: user_groups_user_id_abaea130; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX user_groups_user_id_abaea130 ON user_groups USING btree (user_id);


--
-- Name: user_identity_service_key_0a7af36b; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX user_identity_service_key_0a7af36b ON "user" USING btree (identity_service_key);


--
-- Name: user_is_active_74579245; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX user_is_active_74579245 ON "user" USING btree (is_active);


--
-- Name: user_is_guest_06cb6743; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX user_is_guest_06cb6743 ON "user" USING btree (is_guest);


--
-- Name: user_is_staff_b71b1a3e; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX user_is_staff_b71b1a3e ON "user" USING btree (is_staff);


--
-- Name: user_outgoing_number_id_075eb9a4; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX user_outgoing_number_id_075eb9a4 ON "user" USING btree (outgoing_number_id);


--
-- Name: user_phone_number_181d522d; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX user_phone_number_181d522d ON "user" USING btree (phone_number);


--
-- Name: user_phone_number_181d522d_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX user_phone_number_181d522d_like ON "user" USING btree (phone_number varchar_pattern_ops);


--
-- Name: user_social_data_user_id_db8fc193; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX user_social_data_user_id_db8fc193 ON user_social_data USING btree (user_id);


--
-- Name: user_user_permissions_permission_id_9deb68a3; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX user_user_permissions_permission_id_9deb68a3 ON user_user_permissions USING btree (permission_id);


--
-- Name: user_user_permissions_user_id_ed4a47ea; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX user_user_permissions_user_id_ed4a47ea ON user_user_permissions USING btree (user_id);


--
-- Name: vanity_url_url_d10800be_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX vanity_url_url_d10800be_like ON vanity_url USING btree (url varchar_pattern_ops);


--
-- Name: vanity_url_utm_term_id_607b87b5; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX vanity_url_utm_term_id_607b87b5 ON vanity_url USING btree (utm_term_id);


--
-- Name: vehicle_reservation_dasher_id_7e688af8; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX vehicle_reservation_dasher_id_7e688af8 ON vehicle_reservation USING btree (dasher_id);


--
-- Name: vehicle_reservation_rental_id_04ad6cc4; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX vehicle_reservation_rental_id_04ad6cc4 ON vehicle_reservation USING btree (rental_id);


--
-- Name: verification_attempt_consumer_verification_status_id_b13700ab; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX verification_attempt_consumer_verification_status_id_b13700ab ON verification_attempt USING btree (consumer_verification_status_id);


--
-- Name: version_client_name_ee8bd234_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX version_client_name_ee8bd234_like ON version_client USING btree (name varchar_pattern_ops);


--
-- Name: weather_forecast_model_starting_point_id_34b704a0; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX weather_forecast_model_starting_point_id_34b704a0 ON weather_forecast_model USING btree (starting_point_id);


--
-- Name: weather_historical_model_starting_point_id_6c48d392; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX weather_historical_model_starting_point_id_6c48d392 ON weather_historical_model USING btree (starting_point_id);


--
-- Name: web_deployment_backend_release_id_d5884393; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX web_deployment_backend_release_id_d5884393 ON web_deployment USING btree (backend_release_id);


--
-- Name: web_deployment_backend_release_id_d5884393_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX web_deployment_backend_release_id_d5884393_like ON web_deployment USING btree (backend_release_id text_pattern_ops);


--
-- Name: web_deployment_frontend_release_id_65b4939c; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX web_deployment_frontend_release_id_65b4939c ON web_deployment USING btree (frontend_release_id);


--
-- Name: web_deployment_frontend_release_id_65b4939c_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX web_deployment_frontend_release_id_65b4939c_like ON web_deployment USING btree (frontend_release_id text_pattern_ops);


--
-- Name: zendesk_template_category_id_fd246b35; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX zendesk_template_category_id_fd246b35 ON zendesk_template USING btree (category_id);


--
-- Name: address_place_tag_link address_place_tag_link_address_id_ae51d061_fk_address_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY address_place_tag_link
    ADD CONSTRAINT address_place_tag_link_address_id_ae51d061_fk_address_id FOREIGN KEY (address_id) REFERENCES address(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: address_place_tag_link address_place_tag_link_place_tag_id_712329ce_fk_place_tag_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY address_place_tag_link
    ADD CONSTRAINT address_place_tag_link_place_tag_id_712329ce_fk_place_tag_id FOREIGN KEY (place_tag_id) REFERENCES place_tag(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: analytics_dailybusinessmetrics analytics_dailybusin_constants_id_2974c16a_fk_analytics; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY analytics_dailybusinessmetrics
    ADD CONSTRAINT analytics_dailybusin_constants_id_2974c16a_fk_analytics FOREIGN KEY (constants_id) REFERENCES analytics_businessconstants(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: analytics_dailybusinessmetrics analytics_dailybusin_submarket_id_e1047c59_fk_submarket; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY analytics_dailybusinessmetrics
    ADD CONSTRAINT analytics_dailybusin_submarket_id_e1047c59_fk_submarket FOREIGN KEY (submarket_id) REFERENCES submarket(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: analytics_siteoutage analytics_siteoutage_reported_by_id_a2669100_fk_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY analytics_siteoutage
    ADD CONSTRAINT analytics_siteoutage_reported_by_id_a2669100_fk_user_id FOREIGN KEY (reported_by_id) REFERENCES "user"(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: api_key api_key_user_id_2b8305f7_fk_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY api_key
    ADD CONSTRAINT api_key_user_id_2b8305f7_fk_user_id FOREIGN KEY (user_id) REFERENCES "user"(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auth_group_permissions auth_group_permissio_permission_id_84c5c92e_fk_auth_perm; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY auth_group_permissions
    ADD CONSTRAINT auth_group_permissio_permission_id_84c5c92e_fk_auth_perm FOREIGN KEY (permission_id) REFERENCES auth_permission(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auth_group_permissions auth_group_permissions_group_id_b120cbf9_fk_auth_group_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY auth_group_permissions
    ADD CONSTRAINT auth_group_permissions_group_id_b120cbf9_fk_auth_group_id FOREIGN KEY (group_id) REFERENCES auth_group(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auth_permission auth_permission_content_type_id_2f476e4b_fk_django_co; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY auth_permission
    ADD CONSTRAINT auth_permission_content_type_id_2f476e4b_fk_django_co FOREIGN KEY (content_type_id) REFERENCES django_content_type(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: authtoken_token authtoken_token_user_id_35299eff_fk_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY authtoken_token
    ADD CONSTRAINT authtoken_token_user_id_35299eff_fk_user_id FOREIGN KEY (user_id) REFERENCES "user"(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: blacklisted_consumer_address blacklisted_consumer_blacklisted_user_id_04605c3b_fk_doordash_; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY blacklisted_consumer_address
    ADD CONSTRAINT blacklisted_consumer_blacklisted_user_id_04605c3b_fk_doordash_ FOREIGN KEY (blacklisted_user_id) REFERENCES doordash_blacklisteduser(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: capacity_planning_evaluation capacity_planning_ev_capacity_plan_id_9407e181_fk_dasher_ca; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY capacity_planning_evaluation
    ADD CONSTRAINT capacity_planning_ev_capacity_plan_id_9407e181_fk_dasher_ca FOREIGN KEY (capacity_plan_id) REFERENCES dasher_capacity_plan(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: capacity_planning_evaluation capacity_planning_ev_starting_point_id_c6cc5e66_fk_starting_; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY capacity_planning_evaluation
    ADD CONSTRAINT capacity_planning_ev_starting_point_id_c6cc5e66_fk_starting_ FOREIGN KEY (starting_point_id) REFERENCES starting_point(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: card_acceptor card_acceptor_blacklisted_by_id_d670df09_fk_dispatcher_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY card_acceptor
    ADD CONSTRAINT card_acceptor_blacklisted_by_id_d670df09_fk_dispatcher_user_id FOREIGN KEY (blacklisted_by_id) REFERENCES dispatcher(user_id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: card_acceptor_store_association card_acceptor_store__card_acceptor_id_dbb4aebc_fk_card_acce; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY card_acceptor_store_association
    ADD CONSTRAINT card_acceptor_store__card_acceptor_id_dbb4aebc_fk_card_acce FOREIGN KEY (card_acceptor_id) REFERENCES card_acceptor(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: card_acceptor_store_association card_acceptor_store__manually_checked_by__09ed4c02_fk_dispatche; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY card_acceptor_store_association
    ADD CONSTRAINT card_acceptor_store__manually_checked_by__09ed4c02_fk_dispatche FOREIGN KEY (manually_checked_by_id) REFERENCES dispatcher(user_id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: cash_payment cash_payment_charge_id_1dfacd37_fk_consumer_charge_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY cash_payment
    ADD CONSTRAINT cash_payment_charge_id_1dfacd37_fk_consumer_charge_id FOREIGN KEY (charge_id) REFERENCES consumer_charge(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: city city_market_id_c4f221c6_fk_market_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY city
    ADD CONSTRAINT city_market_id_c4f221c6_fk_market_id FOREIGN KEY (market_id) REFERENCES market(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: city city_submarket_id_fbf91eee_fk_submarket_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY city
    ADD CONSTRAINT city_submarket_id_fbf91eee_fk_submarket_id FOREIGN KEY (submarket_id) REFERENCES submarket(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: communication_preferences_channel_link communication_prefer_communication_channe_6fa91fb7_fk_consumer_; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY communication_preferences_channel_link
    ADD CONSTRAINT communication_prefer_communication_channe_6fa91fb7_fk_consumer_ FOREIGN KEY (communication_channel_id) REFERENCES consumer_communication_channel(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: communication_preferences_channel_link communication_prefer_communication_prefer_d7553f67_fk_consumer_; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY communication_preferences_channel_link
    ADD CONSTRAINT communication_prefer_communication_prefer_d7553f67_fk_consumer_ FOREIGN KEY (communication_preferences_id) REFERENCES consumer_communication_preferences(consumer_id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: compensation_request compensation_request_approved_by_id_c0af7cfe_fk_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY compensation_request
    ADD CONSTRAINT compensation_request_approved_by_id_c0af7cfe_fk_user_id FOREIGN KEY (approved_by_id) REFERENCES "user"(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: compensation_request compensation_request_error_id_f3456ea5_fk_dispatch_error_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY compensation_request
    ADD CONSTRAINT compensation_request_error_id_f3456ea5_fk_dispatch_error_id FOREIGN KEY (error_id) REFERENCES dispatch_error(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: consumer_address_link consumer_address_link_address_id_15eb8998_fk_address_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_address_link
    ADD CONSTRAINT consumer_address_link_address_id_15eb8998_fk_address_id FOREIGN KEY (address_id) REFERENCES address(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: consumer_address_link consumer_address_link_consumer_id_9e837860_fk_consumer_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_address_link
    ADD CONSTRAINT consumer_address_link_consumer_id_9e837860_fk_consumer_id FOREIGN KEY (consumer_id) REFERENCES consumer(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: consumer_announcement_district_link consumer_announcemen_consumer_announcemen_112506de_fk_consumer_; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_announcement_district_link
    ADD CONSTRAINT consumer_announcemen_consumer_announcemen_112506de_fk_consumer_ FOREIGN KEY (consumer_announcement_id) REFERENCES consumer_announcement(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: consumer_announcement_submarkets consumer_announcemen_consumerannouncement_55b4b7c8_fk_consumer_; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_announcement_submarkets
    ADD CONSTRAINT consumer_announcemen_consumerannouncement_55b4b7c8_fk_consumer_ FOREIGN KEY (consumerannouncement_id) REFERENCES consumer_announcement(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: consumer_announcement_district_link consumer_announcemen_district_id_8146d646_fk_district_; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_announcement_district_link
    ADD CONSTRAINT consumer_announcemen_district_id_8146d646_fk_district_ FOREIGN KEY (district_id) REFERENCES district(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: consumer_announcement_submarkets consumer_announcemen_submarket_id_b15c6a4d_fk_submarket; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_announcement_submarkets
    ADD CONSTRAINT consumer_announcemen_submarket_id_b15c6a4d_fk_submarket FOREIGN KEY (submarket_id) REFERENCES submarket(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: consumer_channel_submarkets consumer_channel_sub_consumerchannel_id_5611af6b_fk_consumer_; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_channel_submarkets
    ADD CONSTRAINT consumer_channel_sub_consumerchannel_id_5611af6b_fk_consumer_ FOREIGN KEY (consumerchannel_id) REFERENCES consumer_channel(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: consumer_channel_submarkets consumer_channel_sub_submarket_id_38f61a4e_fk_submarket; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_channel_submarkets
    ADD CONSTRAINT consumer_channel_sub_submarket_id_38f61a4e_fk_submarket FOREIGN KEY (submarket_id) REFERENCES submarket(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: consumer_charge consumer_charge_consumer_id_f883f7d3_fk_consumer_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_charge
    ADD CONSTRAINT consumer_charge_consumer_id_f883f7d3_fk_consumer_id FOREIGN KEY (consumer_id) REFERENCES consumer(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: consumer_charge consumer_charge_country_id_7f5bd302_fk_country_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_charge
    ADD CONSTRAINT consumer_charge_country_id_7f5bd302_fk_country_id FOREIGN KEY (country_id) REFERENCES country(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: consumer_charge consumer_charge_issue_id_a06f09e1_fk_delivery_issue_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_charge
    ADD CONSTRAINT consumer_charge_issue_id_a06f09e1_fk_delivery_issue_id FOREIGN KEY (issue_id) REFERENCES delivery_issue(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: consumer_charge consumer_charge_target_ct_id_11e8fa7a_fk_django_content_type_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_charge
    ADD CONSTRAINT consumer_charge_target_ct_id_11e8fa7a_fk_django_content_type_id FOREIGN KEY (target_ct_id) REFERENCES django_content_type(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: consumer_communication_preferences consumer_communicati_consumer_id_636c1b94_fk_consumer_; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_communication_preferences
    ADD CONSTRAINT consumer_communicati_consumer_id_636c1b94_fk_consumer_ FOREIGN KEY (consumer_id) REFERENCES consumer(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: consumer_communication_preferences consumer_communicati_email_holdout_group__a0759447_fk_email_hol; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_communication_preferences
    ADD CONSTRAINT consumer_communicati_email_holdout_group__a0759447_fk_email_hol FOREIGN KEY (email_holdout_group_id) REFERENCES email_holdout_group(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: consumer_communication_preferences consumer_communicati_email_preference_id_ef0dd076_fk_email_pre; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_communication_preferences
    ADD CONSTRAINT consumer_communicati_email_preference_id_ef0dd076_fk_email_pre FOREIGN KEY (email_preference_id) REFERENCES email_preference(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: consumer consumer_default_address_id_87d263cb_fk_address_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer
    ADD CONSTRAINT consumer_default_address_id_87d263cb_fk_address_id FOREIGN KEY (default_address_id) REFERENCES address(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: consumer consumer_default_card_id_97fb8f90_fk_stripe_card_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer
    ADD CONSTRAINT consumer_default_card_id_97fb8f90_fk_stripe_card_id FOREIGN KEY (default_card_id) REFERENCES stripe_card(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: consumer consumer_default_country_id_b520b701_fk_country_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer
    ADD CONSTRAINT consumer_default_country_id_b520b701_fk_country_id FOREIGN KEY (default_country_id) REFERENCES country(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: consumer_delivery_rating_category_link consumer_delivery_ra_category_id_5af94e46_fk_consumer_; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_delivery_rating_category_link
    ADD CONSTRAINT consumer_delivery_ra_category_id_5af94e46_fk_consumer_ FOREIGN KEY (category_id) REFERENCES consumer_delivery_rating_category(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: consumer_delivery_rating_category_link consumer_delivery_ra_rating_id_bd05f5e0_fk_consumer_; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_delivery_rating_category_link
    ADD CONSTRAINT consumer_delivery_ra_rating_id_bd05f5e0_fk_consumer_ FOREIGN KEY (rating_id) REFERENCES consumer_delivery_rating(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: consumer_ios_devices consumer_ios_devices_consumer_id_7cfc75c3_fk_consumer_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_ios_devices
    ADD CONSTRAINT consumer_ios_devices_consumer_id_7cfc75c3_fk_consumer_id FOREIGN KEY (consumer_id) REFERENCES consumer(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: consumer_ios_devices consumer_ios_devices_device_id_7b82b206_fk_ios_notif; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_ios_devices
    ADD CONSTRAINT consumer_ios_devices_device_id_7b82b206_fk_ios_notif FOREIGN KEY (device_id) REFERENCES ios_notifications_device(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: consumer_preferences consumer_preferences_consumer_id_8f55d6a0_fk_consumer_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_preferences
    ADD CONSTRAINT consumer_preferences_consumer_id_8f55d6a0_fk_consumer_id FOREIGN KEY (consumer_id) REFERENCES consumer(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: consumer_preferences_category_link consumer_preferences_consumer_preferences_56712347_fk_consumer_; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_preferences_category_link
    ADD CONSTRAINT consumer_preferences_consumer_preferences_56712347_fk_consumer_ FOREIGN KEY (consumer_preferences_id) REFERENCES consumer_preferences(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: consumer_promotion consumer_promotion_channel_id_47a407fa_fk_consumer_channel_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_promotion
    ADD CONSTRAINT consumer_promotion_channel_id_47a407fa_fk_consumer_channel_id FOREIGN KEY (channel_id) REFERENCES consumer_channel(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: consumer_promotion consumer_promotion_consumer_promotion_c_ed9a6a8b_fk_consumer_; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_promotion
    ADD CONSTRAINT consumer_promotion_consumer_promotion_c_ed9a6a8b_fk_consumer_ FOREIGN KEY (consumer_promotion_campaign_id) REFERENCES consumer_promotion_campaign(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: consumer_referral_link consumer_referral_link_referree_id_5ab71cf4_fk_consumer_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_referral_link
    ADD CONSTRAINT consumer_referral_link_referree_id_5ab71cf4_fk_consumer_id FOREIGN KEY (referree_id) REFERENCES consumer(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: consumer_referral_link consumer_referral_link_referrer_id_3158f718_fk_consumer_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_referral_link
    ADD CONSTRAINT consumer_referral_link_referrer_id_3158f718_fk_consumer_id FOREIGN KEY (referrer_id) REFERENCES consumer(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: consumer_share consumer_share_consumer_id_6608e820_fk_consumer_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_share
    ADD CONSTRAINT consumer_share_consumer_id_6608e820_fk_consumer_id FOREIGN KEY (consumer_id) REFERENCES consumer(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: consumer_store_request consumer_store_request_consumer_id_d20471be_fk_consumer_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_store_request
    ADD CONSTRAINT consumer_store_request_consumer_id_d20471be_fk_consumer_id FOREIGN KEY (consumer_id) REFERENCES consumer(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: consumer consumer_stripe_country_id_b02ababd_fk_country_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer
    ADD CONSTRAINT consumer_stripe_country_id_b02ababd_fk_country_id FOREIGN KEY (stripe_country_id) REFERENCES country(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: consumer_subscription_unit consumer_subscriptio_charge_id_453633df_fk_consumer_; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_subscription_unit
    ADD CONSTRAINT consumer_subscriptio_charge_id_453633df_fk_consumer_ FOREIGN KEY (charge_id) REFERENCES consumer_charge(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: consumer_subscription_plan consumer_subscriptio_consumer_discount_id_446bf1cb_fk_consumer_; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_subscription_plan
    ADD CONSTRAINT consumer_subscriptio_consumer_discount_id_446bf1cb_fk_consumer_ FOREIGN KEY (consumer_discount_id) REFERENCES consumer_discount(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: consumer_subscription_plan_trial_featured_location_link consumer_subscriptio_consumer_subscriptio_0219faf2_fk_consumer_; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_subscription_plan_trial_featured_location_link
    ADD CONSTRAINT consumer_subscriptio_consumer_subscriptio_0219faf2_fk_consumer_ FOREIGN KEY (consumer_subscription_plan_trial_id) REFERENCES consumer_subscription_plan_trial(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: consumer_subscription_unit consumer_subscriptio_consumer_subscriptio_093f8c78_fk_consumer_; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_subscription_unit
    ADD CONSTRAINT consumer_subscriptio_consumer_subscriptio_093f8c78_fk_consumer_ FOREIGN KEY (consumer_subscription_plan_trial_id) REFERENCES consumer_subscription_plan_trial(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: consumer_subscription consumer_subscriptio_consumer_subscriptio_0c1de937_fk_consumer_; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_subscription
    ADD CONSTRAINT consumer_subscriptio_consumer_subscriptio_0c1de937_fk_consumer_ FOREIGN KEY (consumer_subscription_plan_id) REFERENCES consumer_subscription_plan(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: consumer_subscription_plan_trial consumer_subscriptio_consumer_subscriptio_326e6aa9_fk_consumer_; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_subscription_plan_trial
    ADD CONSTRAINT consumer_subscriptio_consumer_subscriptio_326e6aa9_fk_consumer_ FOREIGN KEY (consumer_subscription_plan_id) REFERENCES consumer_subscription_plan(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: consumer_subscription_unit consumer_subscriptio_consumer_subscriptio_6d0f0b4c_fk_consumer_; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_subscription_unit
    ADD CONSTRAINT consumer_subscriptio_consumer_subscriptio_6d0f0b4c_fk_consumer_ FOREIGN KEY (consumer_subscription_id) REFERENCES consumer_subscription(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: consumer_subscription_plan_submarket_link consumer_subscriptio_consumer_subscriptio_adc2ead7_fk_consumer_; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_subscription_plan_submarket_link
    ADD CONSTRAINT consumer_subscriptio_consumer_subscriptio_adc2ead7_fk_consumer_ FOREIGN KEY (consumer_subscription_plan_id) REFERENCES consumer_subscription_plan(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: consumer_subscription_plan_trial_submarket_link consumer_subscriptio_consumer_subscriptio_bdb1ee39_fk_consumer_; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_subscription_plan_trial_submarket_link
    ADD CONSTRAINT consumer_subscriptio_consumer_subscriptio_bdb1ee39_fk_consumer_ FOREIGN KEY (consumer_subscription_plan_trial_id) REFERENCES consumer_subscription_plan_trial(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: consumer_subscription_plan_featured_location_link consumer_subscriptio_consumer_subscriptio_c706f1bb_fk_consumer_; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_subscription_plan_featured_location_link
    ADD CONSTRAINT consumer_subscriptio_consumer_subscriptio_c706f1bb_fk_consumer_ FOREIGN KEY (consumer_subscription_plan_id) REFERENCES consumer_subscription_plan(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: consumer_subscription_plan_trial_promotion_infos consumer_subscriptio_consumersubscription_8b6b4757_fk_consumer_; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_subscription_plan_trial_promotion_infos
    ADD CONSTRAINT consumer_subscriptio_consumersubscription_8b6b4757_fk_consumer_ FOREIGN KEY (consumersubscriptionplanpromotioninfo_id) REFERENCES consumer_subscription_plan_promotion_info(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: consumer_subscription_plan_promotion_infos consumer_subscriptio_consumersubscription_cc43dac5_fk_consumer_; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_subscription_plan_promotion_infos
    ADD CONSTRAINT consumer_subscriptio_consumersubscription_cc43dac5_fk_consumer_ FOREIGN KEY (consumersubscriptionplan_id) REFERENCES consumer_subscription_plan(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: consumer_subscription_plan_trial_promotion_infos consumer_subscriptio_consumersubscription_d9451a7c_fk_consumer_; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_subscription_plan_trial_promotion_infos
    ADD CONSTRAINT consumer_subscriptio_consumersubscription_d9451a7c_fk_consumer_ FOREIGN KEY (consumersubscriptionplantrial_id) REFERENCES consumer_subscription_plan_trial(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: consumer_subscription_plan_promotion_infos consumer_subscriptio_consumersubscription_ff102a4f_fk_consumer_; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_subscription_plan_promotion_infos
    ADD CONSTRAINT consumer_subscriptio_consumersubscription_ff102a4f_fk_consumer_ FOREIGN KEY (consumersubscriptionplanpromotioninfo_id) REFERENCES consumer_subscription_plan_promotion_info(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: consumer_subscription_plan_trial_featured_location_link consumer_subscriptio_featured_location_id_3ec5f5bf_fk_promotion; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_subscription_plan_trial_featured_location_link
    ADD CONSTRAINT consumer_subscriptio_featured_location_id_3ec5f5bf_fk_promotion FOREIGN KEY (featured_location_id) REFERENCES promotions_featured_location(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: consumer_subscription_plan_featured_location_link consumer_subscriptio_featured_location_id_a543f4b7_fk_promotion; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_subscription_plan_featured_location_link
    ADD CONSTRAINT consumer_subscriptio_featured_location_id_a543f4b7_fk_promotion FOREIGN KEY (featured_location_id) REFERENCES promotions_featured_location(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: consumer_subscription consumer_subscription_consumer_id_07bf3b1e_fk_consumer_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_subscription
    ADD CONSTRAINT consumer_subscription_consumer_id_07bf3b1e_fk_consumer_id FOREIGN KEY (consumer_id) REFERENCES consumer(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: consumer_survey_answer_option consumer_survey_answ_survey_question_id_1f759b96_fk_consumer_; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_survey_answer_option
    ADD CONSTRAINT consumer_survey_answ_survey_question_id_1f759b96_fk_consumer_ FOREIGN KEY (survey_question_id) REFERENCES consumer_survey_question(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: consumer_survey_question_response consumer_survey_ques_survey_answer_option_48082598_fk_consumer_; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_survey_question_response
    ADD CONSTRAINT consumer_survey_ques_survey_answer_option_48082598_fk_consumer_ FOREIGN KEY (survey_answer_option_id) REFERENCES consumer_survey_answer_option(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: consumer_survey_question consumer_survey_ques_survey_id_9d4fc6bf_fk_consumer_; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_survey_question
    ADD CONSTRAINT consumer_survey_ques_survey_id_9d4fc6bf_fk_consumer_ FOREIGN KEY (survey_id) REFERENCES consumer_survey(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: consumer_survey_question_response consumer_survey_ques_survey_question_id_9ab71de7_fk_consumer_; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_survey_question_response
    ADD CONSTRAINT consumer_survey_ques_survey_question_id_9ab71de7_fk_consumer_ FOREIGN KEY (survey_question_id) REFERENCES consumer_survey_question(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: consumer_survey_question_response consumer_survey_ques_survey_response_id_3aba90d2_fk_consumer_; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_survey_question_response
    ADD CONSTRAINT consumer_survey_ques_survey_response_id_3aba90d2_fk_consumer_ FOREIGN KEY (survey_response_id) REFERENCES consumer_survey_response(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: consumer_survey_response consumer_survey_resp_survey_id_9aa1b2e0_fk_consumer_; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_survey_response
    ADD CONSTRAINT consumer_survey_resp_survey_id_9aa1b2e0_fk_consumer_ FOREIGN KEY (survey_id) REFERENCES consumer_survey(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: consumer_survey_response consumer_survey_response_consumer_id_bcd1a9f2_fk_consumer_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_survey_response
    ADD CONSTRAINT consumer_survey_response_consumer_id_bcd1a9f2_fk_consumer_id FOREIGN KEY (consumer_id) REFERENCES consumer(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: consumer_tos_link consumer_tos_link_consumer_id_232c8014_fk_consumer_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_tos_link
    ADD CONSTRAINT consumer_tos_link_consumer_id_232c8014_fk_consumer_id FOREIGN KEY (consumer_id) REFERENCES consumer(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: consumer_tos_link consumer_tos_link_terms_of_service_id_72cf09a8_fk_consumer_; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_tos_link
    ADD CONSTRAINT consumer_tos_link_terms_of_service_id_72cf09a8_fk_consumer_ FOREIGN KEY (terms_of_service_id) REFERENCES consumer_terms_of_service(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: consumer consumer_user_id_3f9288e6_fk_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer
    ADD CONSTRAINT consumer_user_id_3f9288e6_fk_user_id FOREIGN KEY (user_id) REFERENCES "user"(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: consumer_variable_pay consumer_variable_pay_consumer_id_81feb784_fk_consumer_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_variable_pay
    ADD CONSTRAINT consumer_variable_pay_consumer_id_81feb784_fk_consumer_id FOREIGN KEY (consumer_id) REFERENCES consumer(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: consumer_variable_pay consumer_variable_pay_district_id_4c5ed7af_fk_district_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_variable_pay
    ADD CONSTRAINT consumer_variable_pay_district_id_4c5ed7af_fk_district_id FOREIGN KEY (district_id) REFERENCES district(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: consumer_verification_status consumer_verificatio_consumer_id_d146028e_fk_consumer_; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY consumer_verification_status
    ADD CONSTRAINT consumer_verificatio_consumer_id_d146028e_fk_consumer_ FOREIGN KEY (consumer_id) REFERENCES consumer(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_image core_image_target_ct_id_5fe8deb4_fk_django_content_type_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY core_image
    ADD CONSTRAINT core_image_target_ct_id_5fe8deb4_fk_django_content_type_id FOREIGN KEY (target_ct_id) REFERENCES django_content_type(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_modelannotation core_modelannotation_target_ct_id_e5fbc600_fk_django_co; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY core_modelannotation
    ADD CONSTRAINT core_modelannotation_target_ct_id_e5fbc600_fk_django_co FOREIGN KEY (target_ct_id) REFERENCES django_content_type(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: curated_category_membership curated_category_mem_category_id_41178a87_fk_curated_c; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY curated_category_membership
    ADD CONSTRAINT curated_category_mem_category_id_41178a87_fk_curated_c FOREIGN KEY (category_id) REFERENCES curated_category(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: curated_category_membership curated_category_mem_member_ct_id_3dd2c4aa_fk_django_co; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY curated_category_membership
    ADD CONSTRAINT curated_category_mem_member_ct_id_3dd2c4aa_fk_django_co FOREIGN KEY (member_ct_id) REFERENCES django_content_type(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: curated_category curated_category_submarket_id_572c346b_fk_submarket_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY curated_category
    ADD CONSTRAINT curated_category_submarket_id_572c346b_fk_submarket_id FOREIGN KEY (submarket_id) REFERENCES submarket(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: dasher_capacity_model dasher_capacity_mode_starting_point_id_6e9ea3b7_fk_starting_; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY dasher_capacity_model
    ADD CONSTRAINT dasher_capacity_mode_starting_point_id_6e9ea3b7_fk_starting_ FOREIGN KEY (starting_point_id) REFERENCES starting_point(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: dasher_capacity_plan dasher_capacity_plan_model_id_99f6f073_fk_dasher_ca; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY dasher_capacity_plan
    ADD CONSTRAINT dasher_capacity_plan_model_id_99f6f073_fk_dasher_ca FOREIGN KEY (model_id) REFERENCES dasher_capacity_model(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: dasher_capacity_plan dasher_capacity_plan_starting_point_id_d549d44e_fk_starting_; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY dasher_capacity_plan
    ADD CONSTRAINT dasher_capacity_plan_starting_point_id_d549d44e_fk_starting_ FOREIGN KEY (starting_point_id) REFERENCES starting_point(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: delivery_batch_membership delivery_batch_membe_batch_id_76f3bd57_fk_delivery_; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_batch_membership
    ADD CONSTRAINT delivery_batch_membe_batch_id_76f3bd57_fk_delivery_ FOREIGN KEY (batch_id) REFERENCES delivery_batch(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: delivery_event delivery_event_category_id_c39cda48_fk_delivery_; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_event
    ADD CONSTRAINT delivery_event_category_id_c39cda48_fk_delivery_ FOREIGN KEY (category_id) REFERENCES delivery_event_category(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: delivery_event delivery_event_created_by_id_2c294d4a_fk_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_event
    ADD CONSTRAINT delivery_event_created_by_id_2c294d4a_fk_user_id FOREIGN KEY (created_by_id) REFERENCES "user"(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: delivery_funding delivery_funding_created_by_id_bffc87f1_fk_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_funding
    ADD CONSTRAINT delivery_funding_created_by_id_bffc87f1_fk_user_id FOREIGN KEY (created_by_id) REFERENCES "user"(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: delivery_gift delivery_gift_consumer_id_9a6db8c3_fk_consumer_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_gift
    ADD CONSTRAINT delivery_gift_consumer_id_9a6db8c3_fk_consumer_id FOREIGN KEY (consumer_id) REFERENCES consumer(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: delivery_growth_model delivery_growth_mode_starting_point_id_8d0d7cd2_fk_starting_; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_growth_model
    ADD CONSTRAINT delivery_growth_mode_starting_point_id_8d0d7cd2_fk_starting_ FOREIGN KEY (starting_point_id) REFERENCES starting_point(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: delivery_growth_prediction delivery_growth_pred_growth_model_id_10399c53_fk_delivery_; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_growth_prediction
    ADD CONSTRAINT delivery_growth_pred_growth_model_id_10399c53_fk_delivery_ FOREIGN KEY (growth_model_id) REFERENCES delivery_growth_model(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: delivery_growth_prediction delivery_growth_pred_starting_point_id_3bda6847_fk_starting_; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_growth_prediction
    ADD CONSTRAINT delivery_growth_pred_starting_point_id_3bda6847_fk_starting_ FOREIGN KEY (starting_point_id) REFERENCES starting_point(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: delivery_issue delivery_issue_claimed_by_id_529f5739_fk_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_issue
    ADD CONSTRAINT delivery_issue_claimed_by_id_529f5739_fk_user_id FOREIGN KEY (claimed_by_id) REFERENCES "user"(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: delivery_issue delivery_issue_created_by_id_9d83b02f_fk_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_issue
    ADD CONSTRAINT delivery_issue_created_by_id_9d83b02f_fk_user_id FOREIGN KEY (created_by_id) REFERENCES "user"(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: delivery_issue delivery_issue_event_id_4ed3909d_fk_delivery_event_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_issue
    ADD CONSTRAINT delivery_issue_event_id_4ed3909d_fk_delivery_event_id FOREIGN KEY (event_id) REFERENCES delivery_event(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: delivery_issue delivery_issue_resolved_by_id_e01555ff_fk_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_issue
    ADD CONSTRAINT delivery_issue_resolved_by_id_e01555ff_fk_user_id FOREIGN KEY (resolved_by_id) REFERENCES "user"(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: delivery_item delivery_item_drive_order_id_31691705_fk_drive_order_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_item
    ADD CONSTRAINT delivery_item_drive_order_id_31691705_fk_drive_order_id FOREIGN KEY (drive_order_id) REFERENCES drive_order(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: delivery_masking_number_assignment delivery_masking_num_twilio_masking_numbe_c4158fd5_fk_twilio_ma; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_masking_number_assignment
    ADD CONSTRAINT delivery_masking_num_twilio_masking_numbe_c4158fd5_fk_twilio_ma FOREIGN KEY (twilio_masking_number_id) REFERENCES twilio_masking_number(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: delivery_rating_category_link delivery_rating_cate_category_id_48d0e88b_fk_delivery_; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_rating_category_link
    ADD CONSTRAINT delivery_rating_cate_category_id_48d0e88b_fk_delivery_ FOREIGN KEY (category_id) REFERENCES delivery_rating_category(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: delivery_rating_category_link delivery_rating_cate_rating_id_0d7544c0_fk_delivery_; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_rating_category_link
    ADD CONSTRAINT delivery_rating_cate_rating_id_0d7544c0_fk_delivery_ FOREIGN KEY (rating_id) REFERENCES delivery_rating(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: delivery_request delivery_request_dropoff_address_id_ce0e432a_fk_address_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_request
    ADD CONSTRAINT delivery_request_dropoff_address_id_ce0e432a_fk_address_id FOREIGN KEY (dropoff_address_id) REFERENCES address(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: delivery_request delivery_request_order_cart_id_4231d4bf_fk_order_cart_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_request
    ADD CONSTRAINT delivery_request_order_cart_id_4231d4bf_fk_order_cart_id FOREIGN KEY (order_cart_id) REFERENCES order_cart(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: delivery_request delivery_request_pickup_address_id_885fd4cf_fk_address_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_request
    ADD CONSTRAINT delivery_request_pickup_address_id_885fd4cf_fk_address_id FOREIGN KEY (pickup_address_id) REFERENCES address(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: delivery_simulator delivery_simulator_drive_order_id_ed1cebec_fk_drive_order_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY delivery_simulator
    ADD CONSTRAINT delivery_simulator_drive_order_id_ed1cebec_fk_drive_order_id FOREIGN KEY (drive_order_id) REFERENCES drive_order(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: developer developer_user_id_bee8a33b_fk_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY developer
    ADD CONSTRAINT developer_user_id_bee8a33b_fk_user_id FOREIGN KEY (user_id) REFERENCES "user"(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: dispatch_error dispatch_error_created_by_id_284b4e65_fk_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY dispatch_error
    ADD CONSTRAINT dispatch_error_created_by_id_284b4e65_fk_user_id FOREIGN KEY (created_by_id) REFERENCES "user"(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: dispatch_error dispatch_error_order_id_d817ddfe_fk_order_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY dispatch_error
    ADD CONSTRAINT dispatch_error_order_id_d817ddfe_fk_order_id FOREIGN KEY (order_id) REFERENCES "order"(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: dispatcher dispatcher_user_id_09a87f60_fk_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY dispatcher
    ADD CONSTRAINT dispatcher_user_id_09a87f60_fk_user_id FOREIGN KEY (user_id) REFERENCES "user"(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: district district_city_id_9a75808c_fk_city_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY district
    ADD CONSTRAINT district_city_id_9a75808c_fk_city_id FOREIGN KEY (city_id) REFERENCES city(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: district_geometry district_geometry_district_id_afce7782_fk_district_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY district_geometry
    ADD CONSTRAINT district_geometry_district_id_afce7782_fk_district_id FOREIGN KEY (district_id) REFERENCES district(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: district district_market_id_c618bbcd_fk_market_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY district
    ADD CONSTRAINT district_market_id_c618bbcd_fk_market_id FOREIGN KEY (market_id) REFERENCES market(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: district_starting_point_availability_override district_starting_po_district_id_9b8309ee_fk_district_; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY district_starting_point_availability_override
    ADD CONSTRAINT district_starting_po_district_id_9b8309ee_fk_district_ FOREIGN KEY (district_id) REFERENCES district(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: district_starting_point_availability_override district_starting_po_startingpoint_id_a4cce1af_fk_starting_; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY district_starting_point_availability_override
    ADD CONSTRAINT district_starting_po_startingpoint_id_a4cce1af_fk_starting_ FOREIGN KEY (startingpoint_id) REFERENCES starting_point(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: district district_submarket_id_bd85af85_fk_submarket_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY district
    ADD CONSTRAINT district_submarket_id_bd85af85_fk_submarket_id FOREIGN KEY (submarket_id) REFERENCES submarket(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: django_admin_log django_admin_log_content_type_id_c4bce8eb_fk_django_co; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY django_admin_log
    ADD CONSTRAINT django_admin_log_content_type_id_c4bce8eb_fk_django_co FOREIGN KEY (content_type_id) REFERENCES django_content_type(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: django_admin_log django_admin_log_user_id_c564eba6_fk_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY django_admin_log
    ADD CONSTRAINT django_admin_log_user_id_c564eba6_fk_user_id FOREIGN KEY (user_id) REFERENCES "user"(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: django_twilio_credential django_twilio_credential_user_id_29c9a22d_fk_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY django_twilio_credential
    ADD CONSTRAINT django_twilio_credential_user_id_29c9a22d_fk_user_id FOREIGN KEY (user_id) REFERENCES "user"(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: doordash_blacklistedpaymentcard doordash_blacklisted_blacklisted_user_id_30514b12_fk_doordash_; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY doordash_blacklistedpaymentcard
    ADD CONSTRAINT doordash_blacklisted_blacklisted_user_id_30514b12_fk_doordash_ FOREIGN KEY (blacklisted_user_id) REFERENCES doordash_blacklisteduser(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: doordash_blacklistedphonenumber doordash_blacklisted_blacklisted_user_id_520a249c_fk_doordash_; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY doordash_blacklistedphonenumber
    ADD CONSTRAINT doordash_blacklisted_blacklisted_user_id_520a249c_fk_doordash_ FOREIGN KEY (blacklisted_user_id) REFERENCES doordash_blacklisteduser(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: doordash_blacklistedemail doordash_blacklisted_blacklisted_user_id_7a7521f8_fk_doordash_; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY doordash_blacklistedemail
    ADD CONSTRAINT doordash_blacklisted_blacklisted_user_id_7a7521f8_fk_doordash_ FOREIGN KEY (blacklisted_user_id) REFERENCES doordash_blacklisteduser(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: doordash_blacklisteduser doordash_blacklisted_deactivation_source__895ea495_fk_user_deac; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY doordash_blacklisteduser
    ADD CONSTRAINT doordash_blacklisted_deactivation_source__895ea495_fk_user_deac FOREIGN KEY (deactivation_source_id) REFERENCES user_deactivation_source(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: doordash_blacklisteduser doordash_blacklisteduser_user_id_3a83eecc_fk_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY doordash_blacklisteduser
    ADD CONSTRAINT doordash_blacklisteduser_user_id_3a83eecc_fk_user_id FOREIGN KEY (user_id) REFERENCES "user"(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: doordash_orderitemsubstitutionevent doordash_orderitemsu_order_item_id_6b894c7c_fk_order_ite; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY doordash_orderitemsubstitutionevent
    ADD CONSTRAINT doordash_orderitemsu_order_item_id_6b894c7c_fk_order_ite FOREIGN KEY (order_item_id) REFERENCES order_item(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: doordash_orderitemsubstitutionevent doordash_orderitemsu_replaced_order_item__f4ef9c96_fk_order_ite; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY doordash_orderitemsubstitutionevent
    ADD CONSTRAINT doordash_orderitemsu_replaced_order_item__f4ef9c96_fk_order_ite FOREIGN KEY (replaced_order_item_id) REFERENCES order_item(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: drive_webhook_event drive_webhook_event_delivery_event_categ_58b3c187_fk_delivery_; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY drive_webhook_event
    ADD CONSTRAINT drive_webhook_event_delivery_event_categ_58b3c187_fk_delivery_ FOREIGN KEY (delivery_event_category_id) REFERENCES delivery_event_category(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: drive_webhook_subscription drive_webhook_subscr_delivery_event_categ_7bcb9a6e_fk_delivery_; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY drive_webhook_subscription
    ADD CONSTRAINT drive_webhook_subscr_delivery_event_categ_7bcb9a6e_fk_delivery_ FOREIGN KEY (delivery_event_category_id) REFERENCES delivery_event_category(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: email_notification email_notification_issue_id_b3d9705a_fk_delivery_issue_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY email_notification
    ADD CONSTRAINT email_notification_issue_id_b3d9705a_fk_delivery_issue_id FOREIGN KEY (issue_id) REFERENCES delivery_issue(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: email_notification email_notification_target_ct_id_3b0b1c23_fk_django_co; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY email_notification
    ADD CONSTRAINT email_notification_target_ct_id_3b0b1c23_fk_django_co FOREIGN KEY (target_ct_id) REFERENCES django_content_type(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: email_verification_request email_verification_request_user_id_0d6dcb18_fk_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY email_verification_request
    ADD CONSTRAINT email_verification_request_user_id_0d6dcb18_fk_user_id FOREIGN KEY (user_id) REFERENCES "user"(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: employee employee_manager_id_54b357b6_fk_employee_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY employee
    ADD CONSTRAINT employee_manager_id_54b357b6_fk_employee_user_id FOREIGN KEY (manager_id) REFERENCES employee(user_id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: employee employee_user_id_cc4f5a1c_fk_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY employee
    ADD CONSTRAINT employee_user_id_cc4f5a1c_fk_user_id FOREIGN KEY (user_id) REFERENCES "user"(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: experiment_distribution experiment_distribution_experiment_id_0eec6552_fk_experiment_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY experiment_distribution
    ADD CONSTRAINT experiment_distribution_experiment_id_0eec6552_fk_experiment_id FOREIGN KEY (experiment_id) REFERENCES experiment(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: experiment_override experiment_override_experiment_id_871b7c0b_fk_experiment_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY experiment_override
    ADD CONSTRAINT experiment_override_experiment_id_871b7c0b_fk_experiment_id FOREIGN KEY (experiment_id) REFERENCES experiment(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: experiment_override experiment_override_user_id_29066c65_fk_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY experiment_override
    ADD CONSTRAINT experiment_override_user_id_29066c65_fk_user_id FOREIGN KEY (user_id) REFERENCES "user"(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: experiment_user experiment_user_user_id_3963c413_fk_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY experiment_user
    ADD CONSTRAINT experiment_user_user_id_3963c413_fk_user_id FOREIGN KEY (user_id) REFERENCES "user"(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: experiment_version experiment_version_experiment_id_85cce31c_fk_experiment2_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY experiment_version
    ADD CONSTRAINT experiment_version_experiment_id_85cce31c_fk_experiment2_id FOREIGN KEY (experiment_id) REFERENCES experiment2(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: gift_code gift_code_creator_id_43de49a3_fk_consumer_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY gift_code
    ADD CONSTRAINT gift_code_creator_id_43de49a3_fk_consumer_id FOREIGN KEY (creator_id) REFERENCES consumer(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: gift_code gift_code_redeemer_id_7d769552_fk_consumer_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY gift_code
    ADD CONSTRAINT gift_code_redeemer_id_7d769552_fk_consumer_id FOREIGN KEY (redeemer_id) REFERENCES consumer(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: grab_pay_account grab_pay_account_consumer_id_5d60f2b4_fk_consumer_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY grab_pay_account
    ADD CONSTRAINT grab_pay_account_consumer_id_5d60f2b4_fk_consumer_id FOREIGN KEY (consumer_id) REFERENCES consumer(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: grab_pay_charge grab_pay_charge_charge_id_85d087d0_fk_consumer_charge_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY grab_pay_charge
    ADD CONSTRAINT grab_pay_charge_charge_id_85d087d0_fk_consumer_charge_id FOREIGN KEY (charge_id) REFERENCES consumer_charge(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: grab_pay_charge grab_pay_charge_grab_pay_account_id_338932cc_fk_grab_pay_; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY grab_pay_charge
    ADD CONSTRAINT grab_pay_charge_grab_pay_account_id_338932cc_fk_grab_pay_ FOREIGN KEY (grab_pay_account_id) REFERENCES grab_pay_account(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: grab_transfer grab_transfer_transfer_id_a0a525c2_fk_transfer_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY grab_transfer
    ADD CONSTRAINT grab_transfer_transfer_id_a0a525c2_fk_transfer_id FOREIGN KEY (transfer_id) REFERENCES transfer(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: invoicing_group_membership invoicing_group_memb_invoicing_group_id_f47521fb_fk_invoicing; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY invoicing_group_membership
    ADD CONSTRAINT invoicing_group_memb_invoicing_group_id_f47521fb_fk_invoicing FOREIGN KEY (invoicing_group_id) REFERENCES invoicing_group(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: invoicing_group_onboarding_rule invoicing_group_onbo_invoicing_group_id_b471e097_fk_invoicing; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY invoicing_group_onboarding_rule
    ADD CONSTRAINT invoicing_group_onbo_invoicing_group_id_b471e097_fk_invoicing FOREIGN KEY (invoicing_group_id) REFERENCES invoicing_group(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: ios_notifications_device_users ios_notifications_de_device_id_d0bddd71_fk_ios_notif; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY ios_notifications_device_users
    ADD CONSTRAINT ios_notifications_de_device_id_d0bddd71_fk_ios_notif FOREIGN KEY (device_id) REFERENCES ios_notifications_device(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: ios_notifications_device ios_notifications_de_service_id_d82269bf_fk_ios_notif; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY ios_notifications_device
    ADD CONSTRAINT ios_notifications_de_service_id_d82269bf_fk_ios_notif FOREIGN KEY (service_id) REFERENCES ios_notifications_apnservice(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: ios_notifications_device_users ios_notifications_device_users_user_id_c84b371e_fk_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY ios_notifications_device_users
    ADD CONSTRAINT ios_notifications_device_users_user_id_c84b371e_fk_user_id FOREIGN KEY (user_id) REFERENCES "user"(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: ios_notifications_feedbackservice ios_notifications_fe_apn_service_id_2db1f5ae_fk_ios_notif; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY ios_notifications_feedbackservice
    ADD CONSTRAINT ios_notifications_fe_apn_service_id_2db1f5ae_fk_ios_notif FOREIGN KEY (apn_service_id) REFERENCES ios_notifications_apnservice(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: ios_notifications_notification ios_notifications_no_service_id_a25fb97e_fk_ios_notif; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY ios_notifications_notification
    ADD CONSTRAINT ios_notifications_no_service_id_a25fb97e_fk_ios_notif FOREIGN KEY (service_id) REFERENCES ios_notifications_apnservice(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: kill_switch_interval kill_switch_interval_killed_by_id_ed281167_fk_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY kill_switch_interval
    ADD CONSTRAINT kill_switch_interval_killed_by_id_ed281167_fk_user_id FOREIGN KEY (killed_by_id) REFERENCES "user"(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: kill_switch_interval kill_switch_interval_starting_point_id_8d2b568e_fk_starting_; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY kill_switch_interval
    ADD CONSTRAINT kill_switch_interval_starting_point_id_8d2b568e_fk_starting_ FOREIGN KEY (starting_point_id) REFERENCES starting_point(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: kill_switch_interval kill_switch_interval_unkilled_by_id_1624bdc7_fk_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY kill_switch_interval
    ADD CONSTRAINT kill_switch_interval_unkilled_by_id_1624bdc7_fk_user_id FOREIGN KEY (unkilled_by_id) REFERENCES "user"(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: managed_account_transfer managed_account_tran_account_ct_id_94a5852f_fk_django_co; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY managed_account_transfer
    ADD CONSTRAINT managed_account_tran_account_ct_id_94a5852f_fk_django_co FOREIGN KEY (account_ct_id) REFERENCES django_content_type(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: managed_account_transfer managed_account_transfer_transfer_id_e3c56806_fk_transfer_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY managed_account_transfer
    ADD CONSTRAINT managed_account_transfer_transfer_id_e3c56806_fk_transfer_id FOREIGN KEY (transfer_id) REFERENCES transfer(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: market market_country_id_d94abd98_fk_country_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY market
    ADD CONSTRAINT market_country_id_d94abd98_fk_country_id FOREIGN KEY (country_id) REFERENCES country(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: market market_region_id_c8b496df_fk_region_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY market
    ADD CONSTRAINT market_region_id_c8b496df_fk_region_id FOREIGN KEY (region_id) REFERENCES region(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: market_special_hours market_special_hours_market_id_fd60d9f6_fk_market_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY market_special_hours
    ADD CONSTRAINT market_special_hours_market_id_fd60d9f6_fk_market_id FOREIGN KEY (market_id) REFERENCES market(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: market market_subnational_division_f438906a_fk_subnation; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY market
    ADD CONSTRAINT market_subnational_division_f438906a_fk_subnation FOREIGN KEY (subnational_division_id) REFERENCES subnational_division(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: marqeta_card_ownership marqeta_card_ownership_card_id_b7e17995_fk_marqeta_card_token; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY marqeta_card_ownership
    ADD CONSTRAINT marqeta_card_ownership_card_id_b7e17995_fk_marqeta_card_token FOREIGN KEY (card_id) REFERENCES marqeta_card(token) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: marqeta_card_transition marqeta_card_transition_card_id_4bf68626_fk_marqeta_card_token; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY marqeta_card_transition
    ADD CONSTRAINT marqeta_card_transition_card_id_4bf68626_fk_marqeta_card_token FOREIGN KEY (card_id) REFERENCES marqeta_card(token) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: marqeta_decline_exemption marqeta_decline_exemption_created_by_id_c420d085_fk_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY marqeta_decline_exemption
    ADD CONSTRAINT marqeta_decline_exemption_created_by_id_c420d085_fk_user_id FOREIGN KEY (created_by_id) REFERENCES "user"(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: marqeta_transaction_event marqeta_transaction__card_acceptor_id_a86839c1_fk_card_acce; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY marqeta_transaction_event
    ADD CONSTRAINT marqeta_transaction__card_acceptor_id_a86839c1_fk_card_acce FOREIGN KEY (card_acceptor_id) REFERENCES card_acceptor(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: marqeta_transaction_event marqeta_transaction__ownership_id_e3b46982_fk_marqeta_c; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY marqeta_transaction_event
    ADD CONSTRAINT marqeta_transaction__ownership_id_e3b46982_fk_marqeta_c FOREIGN KEY (ownership_id) REFERENCES marqeta_card_ownership(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: mass_communication_status mass_communication_status_sender_id_a8e8f447_fk_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY mass_communication_status
    ADD CONSTRAINT mass_communication_status_sender_id_a8e8f447_fk_user_id FOREIGN KEY (sender_id) REFERENCES "user"(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: order_cart_consumer_promotion_link order_cart_consumer__consumer_promotion_i_6aa3f2fb_fk_consumer_; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY order_cart_consumer_promotion_link
    ADD CONSTRAINT order_cart_consumer__consumer_promotion_i_6aa3f2fb_fk_consumer_ FOREIGN KEY (consumer_promotion_id) REFERENCES consumer_promotion(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: order_cart_consumer_promotion_link order_cart_consumer__order_cart_id_5a6f0361_fk_order_car; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY order_cart_consumer_promotion_link
    ADD CONSTRAINT order_cart_consumer__order_cart_id_5a6f0361_fk_order_car FOREIGN KEY (order_cart_id) REFERENCES order_cart(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: order_cart order_cart_creator_id_8172b8ff_fk_consumer_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY order_cart
    ADD CONSTRAINT order_cart_creator_id_8172b8ff_fk_consumer_id FOREIGN KEY (creator_id) REFERENCES consumer(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: order_cart order_cart_delivery_address_id_a6942a1b_fk_address_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY order_cart
    ADD CONSTRAINT order_cart_delivery_address_id_a6942a1b_fk_address_id FOREIGN KEY (delivery_address_id) REFERENCES address(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: order_cart_discount_component order_cart_discount__order_cart_id_fe63fa63_fk_order_car; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY order_cart_discount_component
    ADD CONSTRAINT order_cart_discount__order_cart_id_fe63fa63_fk_order_car FOREIGN KEY (order_cart_id) REFERENCES order_cart(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: order_cart_discount_component order_cart_discount__source_type_id_800dd313_fk_order_car; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY order_cart_discount_component
    ADD CONSTRAINT order_cart_discount__source_type_id_800dd313_fk_order_car FOREIGN KEY (source_type_id) REFERENCES order_cart_discount_component_source_type(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: order_cart_discount_component order_cart_discount__store_order_cart_id_da9e8891_fk_store_ord; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY order_cart_discount_component
    ADD CONSTRAINT order_cart_discount__store_order_cart_id_da9e8891_fk_store_ord FOREIGN KEY (store_order_cart_id) REFERENCES store_order_cart(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: order_cart_discount order_cart_discount_order_cart_id_d8e8ea66_fk_order_cart_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY order_cart_discount
    ADD CONSTRAINT order_cart_discount_order_cart_id_d8e8ea66_fk_order_cart_id FOREIGN KEY (order_cart_id) REFERENCES order_cart(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: order_cart_escalation_reason order_cart_escalatio_escalation_id_f62b9290_fk_order_car; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY order_cart_escalation_reason
    ADD CONSTRAINT order_cart_escalatio_escalation_id_f62b9290_fk_order_car FOREIGN KEY (escalation_id) REFERENCES order_cart_escalation(order_cart_id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: order_cart_escalation order_cart_escalatio_stripe_charge_id_a7f978a6_fk_stripe_ch; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY order_cart_escalation
    ADD CONSTRAINT order_cart_escalatio_stripe_charge_id_a7f978a6_fk_stripe_ch FOREIGN KEY (stripe_charge_id) REFERENCES stripe_charge(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: order_cart_escalation order_cart_escalation_order_cart_id_2a6e5273_fk_order_cart_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY order_cart_escalation
    ADD CONSTRAINT order_cart_escalation_order_cart_id_2a6e5273_fk_order_cart_id FOREIGN KEY (order_cart_id) REFERENCES order_cart(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: order_cart_escalation order_cart_escalation_reviewed_by_id_2adb162a_fk_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY order_cart_escalation
    ADD CONSTRAINT order_cart_escalation_reviewed_by_id_2adb162a_fk_user_id FOREIGN KEY (reviewed_by_id) REFERENCES "user"(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: order_cart order_cart_pricing_strategy_id_3227c426_fk_order_car; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY order_cart
    ADD CONSTRAINT order_cart_pricing_strategy_id_3227c426_fk_order_car FOREIGN KEY (pricing_strategy_id) REFERENCES order_cart_pricing_strategy(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: order_cart order_cart_promo_code_id_1975069c_fk_promo_code_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY order_cart
    ADD CONSTRAINT order_cart_promo_code_id_1975069c_fk_promo_code_id FOREIGN KEY (promo_code_id) REFERENCES promo_code(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: order order_consumer_id_a83b8db3_fk_consumer_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY "order"
    ADD CONSTRAINT order_consumer_id_a83b8db3_fk_consumer_id FOREIGN KEY (consumer_id) REFERENCES consumer(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: order_item_extra_option order_item_extra_opt_parent_order_item_ex_267787b0_fk_order_ite; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY order_item_extra_option
    ADD CONSTRAINT order_item_extra_opt_parent_order_item_ex_267787b0_fk_order_ite FOREIGN KEY (parent_order_item_extra_option_id) REFERENCES order_item_extra_option(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: order_item_extra_option order_item_extra_option_order_item_id_227a2aaa_fk_order_item_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY order_item_extra_option
    ADD CONSTRAINT order_item_extra_option_order_item_id_227a2aaa_fk_order_item_id FOREIGN KEY (order_item_id) REFERENCES order_item(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: order_item order_item_order_id_0ca9e92e_fk_order_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY order_item
    ADD CONSTRAINT order_item_order_id_0ca9e92e_fk_order_id FOREIGN KEY (order_id) REFERENCES "order"(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: order_menu_option order_menu_option_order_id_d7c52c26_fk_order_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY order_menu_option
    ADD CONSTRAINT order_menu_option_order_id_d7c52c26_fk_order_id FOREIGN KEY (order_id) REFERENCES "order"(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: order order_order_cart_id_02676457_fk_order_cart_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY "order"
    ADD CONSTRAINT order_order_cart_id_02676457_fk_order_cart_id FOREIGN KEY (order_cart_id) REFERENCES order_cart(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: promo_code_consumer_link promo_code_consumer__promo_code_id_a4fc4562_fk_promo_cod; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY promo_code_consumer_link
    ADD CONSTRAINT promo_code_consumer__promo_code_id_a4fc4562_fk_promo_cod FOREIGN KEY (promo_code_id) REFERENCES promo_code(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: promo_code_consumer_link promo_code_consumer_link_consumer_id_f9423f56_fk_consumer_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY promo_code_consumer_link
    ADD CONSTRAINT promo_code_consumer_link_consumer_id_f9423f56_fk_consumer_id FOREIGN KEY (consumer_id) REFERENCES consumer(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: promo_code_markets promo_code_markets_market_id_83fce76d_fk_market_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY promo_code_markets
    ADD CONSTRAINT promo_code_markets_market_id_83fce76d_fk_market_id FOREIGN KEY (market_id) REFERENCES market(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: promo_code_markets promo_code_markets_promocode_id_32101512_fk_promo_code_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY promo_code_markets
    ADD CONSTRAINT promo_code_markets_promocode_id_32101512_fk_promo_code_id FOREIGN KEY (promocode_id) REFERENCES promo_code(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: promo_code_submarket_link promo_code_submarket_link_submarket_id_09afa639_fk_submarket_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY promo_code_submarket_link
    ADD CONSTRAINT promo_code_submarket_link_submarket_id_09afa639_fk_submarket_id FOREIGN KEY (submarket_id) REFERENCES submarket(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: promo_code_submarket_link promo_code_submarket_promo_code_id_ca91eba3_fk_promo_cod; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY promo_code_submarket_link
    ADD CONSTRAINT promo_code_submarket_promo_code_id_ca91eba3_fk_promo_cod FOREIGN KEY (promo_code_id) REFERENCES promo_code(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: promotion_consumer_link promotion_consumer_l_promotion_id_0dc3fdcd_fk_consumer_; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY promotion_consumer_link
    ADD CONSTRAINT promotion_consumer_l_promotion_id_0dc3fdcd_fk_consumer_ FOREIGN KEY (promotion_id) REFERENCES consumer_promotion(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: promotion_consumer_link promotion_consumer_link_consumer_id_a56783f8_fk_consumer_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY promotion_consumer_link
    ADD CONSTRAINT promotion_consumer_link_consumer_id_a56783f8_fk_consumer_id FOREIGN KEY (consumer_id) REFERENCES consumer(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: promotion_featured_location_link promotion_featured_l_featured_location_id_d014d016_fk_promotion; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY promotion_featured_location_link
    ADD CONSTRAINT promotion_featured_l_featured_location_id_d014d016_fk_promotion FOREIGN KEY (featured_location_id) REFERENCES promotions_featured_location(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: promotion_featured_location_link promotion_featured_l_promotion_id_b3c8d310_fk_consumer_; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY promotion_featured_location_link
    ADD CONSTRAINT promotion_featured_l_promotion_id_b3c8d310_fk_consumer_ FOREIGN KEY (promotion_id) REFERENCES consumer_promotion(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: promotion_place_tag_link promotion_place_tag__promotion_id_05aa6564_fk_consumer_; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY promotion_place_tag_link
    ADD CONSTRAINT promotion_place_tag__promotion_id_05aa6564_fk_consumer_ FOREIGN KEY (promotion_id) REFERENCES consumer_promotion(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: promotion_place_tag_link promotion_place_tag_link_place_tag_id_49472528_fk_place_tag_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY promotion_place_tag_link
    ADD CONSTRAINT promotion_place_tag_link_place_tag_id_49472528_fk_place_tag_id FOREIGN KEY (place_tag_id) REFERENCES place_tag(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: promotion_redemption_event promotion_redemption_event_region_id_3e067e19_fk_region_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY promotion_redemption_event
    ADD CONSTRAINT promotion_redemption_event_region_id_3e067e19_fk_region_id FOREIGN KEY (region_id) REFERENCES region(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: promotion_redemption_event promotion_redemption_order_cart_id_f99f63f6_fk_order_car; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY promotion_redemption_event
    ADD CONSTRAINT promotion_redemption_order_cart_id_f99f63f6_fk_order_car FOREIGN KEY (order_cart_id) REFERENCES order_cart(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: promotion_redemption_event promotion_redemption_promotion_campaign_i_40cbe5e5_fk_consumer_; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY promotion_redemption_event
    ADD CONSTRAINT promotion_redemption_promotion_campaign_i_40cbe5e5_fk_consumer_ FOREIGN KEY (promotion_campaign_id) REFERENCES consumer_promotion_campaign(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: promotion_redemption_event promotion_redemption_promotion_id_4a71099f_fk_consumer_; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY promotion_redemption_event
    ADD CONSTRAINT promotion_redemption_promotion_id_4a71099f_fk_consumer_ FOREIGN KEY (promotion_id) REFERENCES consumer_promotion(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: promotion_submarket_link promotion_submarket__promotion_id_4a612f03_fk_consumer_; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY promotion_submarket_link
    ADD CONSTRAINT promotion_submarket__promotion_id_4a612f03_fk_consumer_ FOREIGN KEY (promotion_id) REFERENCES consumer_promotion(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: promotion_submarket_link promotion_submarket_link_submarket_id_e9e0ad13_fk_submarket_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY promotion_submarket_link
    ADD CONSTRAINT promotion_submarket_link_submarket_id_e9e0ad13_fk_submarket_id FOREIGN KEY (submarket_id) REFERENCES submarket(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: promotions_featured_location promotions_featured__next_featured_locati_e2bc2b66_fk_promotion; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY promotions_featured_location
    ADD CONSTRAINT promotions_featured__next_featured_locati_e2bc2b66_fk_promotion FOREIGN KEY (next_featured_location_id) REFERENCES promotions_featured_location(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: real_time_supply_model real_time_supply_mod_starting_point_id_73a647eb_fk_starting_; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY real_time_supply_model
    ADD CONSTRAINT real_time_supply_mod_starting_point_id_73a647eb_fk_starting_ FOREIGN KEY (starting_point_id) REFERENCES starting_point(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: real_time_supply_prediction real_time_supply_pre_starting_point_id_a07911de_fk_starting_; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY real_time_supply_prediction
    ADD CONSTRAINT real_time_supply_pre_starting_point_id_a07911de_fk_starting_ FOREIGN KEY (starting_point_id) REFERENCES starting_point(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: real_time_supply_prediction real_time_supply_pre_supply_model_id_3d4c16c8_fk_real_time; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY real_time_supply_prediction
    ADD CONSTRAINT real_time_supply_pre_supply_model_id_3d4c16c8_fk_real_time FOREIGN KEY (supply_model_id) REFERENCES real_time_supply_model(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: realtime_demand_evaluation realtime_demand_eval_starting_point_id_faf727ab_fk_starting_; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY realtime_demand_evaluation
    ADD CONSTRAINT realtime_demand_eval_starting_point_id_faf727ab_fk_starting_ FOREIGN KEY (starting_point_id) REFERENCES starting_point(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: refresh_token refresh_token_user_id_1d7a63ac_fk_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY refresh_token
    ADD CONSTRAINT refresh_token_user_id_1d7a63ac_fk_user_id FOREIGN KEY (user_id) REFERENCES "user"(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: region region_country_id_f136eca4_fk_country_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY region
    ADD CONSTRAINT region_country_id_f136eca4_fk_country_id FOREIGN KEY (country_id) REFERENCES country(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: region_snapshot region_snapshot_district_id_b2335253_fk_district_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY region_snapshot
    ADD CONSTRAINT region_snapshot_district_id_b2335253_fk_district_id FOREIGN KEY (district_id) REFERENCES district(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: region_snapshot region_snapshot_starting_point_id_06fac4a8_fk_starting_point_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY region_snapshot
    ADD CONSTRAINT region_snapshot_starting_point_id_06fac4a8_fk_starting_point_id FOREIGN KEY (starting_point_id) REFERENCES starting_point(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: scheduled_caps_boost scheduled_caps_boost_starting_point_id_2058452a_fk_starting_; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY scheduled_caps_boost
    ADD CONSTRAINT scheduled_caps_boost_starting_point_id_2058452a_fk_starting_ FOREIGN KEY (starting_point_id) REFERENCES starting_point(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: seo_local_region seo_local_region_city_id_50f7b946_fk_city_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY seo_local_region
    ADD CONSTRAINT seo_local_region_city_id_50f7b946_fk_city_id FOREIGN KEY (city_id) REFERENCES city(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: sms_help_message_status sms_help_message_status_user_id_6217acd5_fk_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY sms_help_message_status
    ADD CONSTRAINT sms_help_message_status_user_id_6217acd5_fk_user_id FOREIGN KEY (user_id) REFERENCES "user"(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: starting_point_assignment_latency_stats starting_point_assig_starting_point_id_bea987a6_fk_starting_; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY starting_point_assignment_latency_stats
    ADD CONSTRAINT starting_point_assig_starting_point_id_bea987a6_fk_starting_ FOREIGN KEY (starting_point_id) REFERENCES starting_point(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: starting_point_delivery_duration_stats starting_point_deliv_starting_point_id_34606949_fk_starting_; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY starting_point_delivery_duration_stats
    ADD CONSTRAINT starting_point_deliv_starting_point_id_34606949_fk_starting_ FOREIGN KEY (starting_point_id) REFERENCES starting_point(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: starting_point_delivery_hours starting_point_deliv_starting_point_id_404ae42b_fk_starting_; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY starting_point_delivery_hours
    ADD CONSTRAINT starting_point_deliv_starting_point_id_404ae42b_fk_starting_ FOREIGN KEY (starting_point_id) REFERENCES starting_point(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: starting_point_geometry starting_point_geome_starting_point_id_afd128e0_fk_starting_; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY starting_point_geometry
    ADD CONSTRAINT starting_point_geome_starting_point_id_afd128e0_fk_starting_ FOREIGN KEY (starting_point_id) REFERENCES starting_point(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: starting_point starting_point_market_id_8e3f1497_fk_market_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY starting_point
    ADD CONSTRAINT starting_point_market_id_8e3f1497_fk_market_id FOREIGN KEY (market_id) REFERENCES market(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: starting_point_r2c_stats starting_point_r2c_s_starting_point_id_7a965846_fk_starting_; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY starting_point_r2c_stats
    ADD CONSTRAINT starting_point_r2c_s_starting_point_id_7a965846_fk_starting_ FOREIGN KEY (starting_point_id) REFERENCES starting_point(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: starting_point_set starting_point_set_market_id_f3c05e7e_fk_market_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY starting_point_set
    ADD CONSTRAINT starting_point_set_market_id_f3c05e7e_fk_market_id FOREIGN KEY (market_id) REFERENCES market(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: starting_point_set starting_point_set_starting_point_id_99f0c359_fk_starting_; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY starting_point_set
    ADD CONSTRAINT starting_point_set_starting_point_id_99f0c359_fk_starting_ FOREIGN KEY (starting_point_id) REFERENCES starting_point(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: starting_point starting_point_submarket_id_1367e594_fk_submarket_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY starting_point
    ADD CONSTRAINT starting_point_submarket_id_1367e594_fk_submarket_id FOREIGN KEY (submarket_id) REFERENCES submarket(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: store_consumer_review_tag_link store_consumer_revie_review_id_751fd5cb_fk_store_con; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY store_consumer_review_tag_link
    ADD CONSTRAINT store_consumer_revie_review_id_751fd5cb_fk_store_con FOREIGN KEY (review_id) REFERENCES store_consumer_review(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: store_consumer_review_tag_link store_consumer_revie_tag_id_3c72815d_fk_store_con; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY store_consumer_review_tag_link
    ADD CONSTRAINT store_consumer_revie_tag_id_3c72815d_fk_store_con FOREIGN KEY (tag_id) REFERENCES store_consumer_review_tag(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: store_consumer_review store_consumer_review_consumer_id_41acc1e2_fk_consumer_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY store_consumer_review
    ADD CONSTRAINT store_consumer_review_consumer_id_41acc1e2_fk_consumer_id FOREIGN KEY (consumer_id) REFERENCES consumer(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: store_order_cart store_order_cart_order_cart_id_595cd0d6_fk_order_cart_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY store_order_cart
    ADD CONSTRAINT store_order_cart_order_cart_id_595cd0d6_fk_order_cart_id FOREIGN KEY (order_cart_id) REFERENCES order_cart(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: stripe_card stripe_card_consumer_id_043b0b95_fk_consumer_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY stripe_card
    ADD CONSTRAINT stripe_card_consumer_id_043b0b95_fk_consumer_id FOREIGN KEY (consumer_id) REFERENCES consumer(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: stripe_card_event stripe_card_event_consumer_id_d0bb5239_fk_consumer_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY stripe_card_event
    ADD CONSTRAINT stripe_card_event_consumer_id_d0bb5239_fk_consumer_id FOREIGN KEY (consumer_id) REFERENCES consumer(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: stripe_charge stripe_charge_card_id_47885fdf_fk_stripe_card_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY stripe_charge
    ADD CONSTRAINT stripe_charge_card_id_47885fdf_fk_stripe_card_id FOREIGN KEY (card_id) REFERENCES stripe_card(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: stripe_charge stripe_charge_charge_id_672b9190_fk_consumer_charge_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY stripe_charge
    ADD CONSTRAINT stripe_charge_charge_id_672b9190_fk_consumer_charge_id FOREIGN KEY (charge_id) REFERENCES consumer_charge(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: stripe_dispute stripe_dispute_stripe_card_id_ab2f0c08_fk_stripe_card_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY stripe_dispute
    ADD CONSTRAINT stripe_dispute_stripe_card_id_ab2f0c08_fk_stripe_card_id FOREIGN KEY (stripe_card_id) REFERENCES stripe_card(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: stripe_dispute stripe_dispute_stripe_charge_id_da15e7b2_fk_stripe_charge_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY stripe_dispute
    ADD CONSTRAINT stripe_dispute_stripe_charge_id_da15e7b2_fk_stripe_charge_id FOREIGN KEY (stripe_charge_id) REFERENCES stripe_charge(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: stripe_transfer stripe_transfer_transfer_id_57913c98_fk_transfer_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY stripe_transfer
    ADD CONSTRAINT stripe_transfer_transfer_id_57913c98_fk_transfer_id FOREIGN KEY (transfer_id) REFERENCES transfer(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: submarket submarket_market_id_ff4223ec_fk_market_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY submarket
    ADD CONSTRAINT submarket_market_id_ff4223ec_fk_market_id FOREIGN KEY (market_id) REFERENCES market(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: subnational_division subnational_division_country_id_02d40283_fk_country_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY subnational_division
    ADD CONSTRAINT subnational_division_country_id_02d40283_fk_country_id FOREIGN KEY (country_id) REFERENCES country(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: transfer transfer_recipient_ct_id_d955a1ae_fk_django_content_type_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY transfer
    ADD CONSTRAINT transfer_recipient_ct_id_d955a1ae_fk_django_content_type_id FOREIGN KEY (recipient_ct_id) REFERENCES django_content_type(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: twilio_masking_number_assignment twilio_masking_numbe_twilio_masking_numbe_a26d7984_fk_twilio_ma; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY twilio_masking_number_assignment
    ADD CONSTRAINT twilio_masking_numbe_twilio_masking_numbe_a26d7984_fk_twilio_ma FOREIGN KEY (twilio_masking_number_id) REFERENCES twilio_masking_number(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: twilio_masking_number twilio_masking_numbe_twilio_number_id_8cd26882_fk_twilio_nu; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY twilio_masking_number
    ADD CONSTRAINT twilio_masking_numbe_twilio_number_id_8cd26882_fk_twilio_nu FOREIGN KEY (twilio_number_id) REFERENCES twilio_number(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: twilio_number twilio_number_country_id_49d13740_fk_country_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY twilio_number
    ADD CONSTRAINT twilio_number_country_id_49d13740_fk_country_id FOREIGN KEY (country_id) REFERENCES country(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: user_activation_change_event user_activation_change_event_changed_by_id_5d3e4cc7_fk_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY user_activation_change_event
    ADD CONSTRAINT user_activation_change_event_changed_by_id_5d3e4cc7_fk_user_id FOREIGN KEY (changed_by_id) REFERENCES "user"(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: user_activation_change_event user_activation_change_event_user_id_3af7e91c_fk_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY user_activation_change_event
    ADD CONSTRAINT user_activation_change_event_user_id_3af7e91c_fk_user_id FOREIGN KEY (user_id) REFERENCES "user"(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: user_device_fingerprint_link user_device_fingerprint_link_user_id_c4d59d93_fk_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY user_device_fingerprint_link
    ADD CONSTRAINT user_device_fingerprint_link_user_id_c4d59d93_fk_user_id FOREIGN KEY (user_id) REFERENCES "user"(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: user_group_admin  user_group_admin _group_id_9a479256_fk_auth_group_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY "user_group_admin "
    ADD CONSTRAINT "user_group_admin _group_id_9a479256_fk_auth_group_id" FOREIGN KEY (group_id) REFERENCES auth_group(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: user_group_admin  user_group_admin _user_id_2d389e35_fk_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY "user_group_admin "
    ADD CONSTRAINT "user_group_admin _user_id_2d389e35_fk_user_id" FOREIGN KEY (user_id) REFERENCES "user"(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: user_groups user_groups_group_id_b76f8aba_fk_auth_group_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY user_groups
    ADD CONSTRAINT user_groups_group_id_b76f8aba_fk_auth_group_id FOREIGN KEY (group_id) REFERENCES auth_group(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: user_groups user_groups_user_id_abaea130_fk_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY user_groups
    ADD CONSTRAINT user_groups_user_id_abaea130_fk_user_id FOREIGN KEY (user_id) REFERENCES "user"(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: user_locale_preference user_locale_preference_user_id_83455973_fk_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY user_locale_preference
    ADD CONSTRAINT user_locale_preference_user_id_83455973_fk_user_id FOREIGN KEY (user_id) REFERENCES "user"(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: user user_outgoing_number_id_075eb9a4_fk_twilio_number_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY "user"
    ADD CONSTRAINT user_outgoing_number_id_075eb9a4_fk_twilio_number_id FOREIGN KEY (outgoing_number_id) REFERENCES twilio_number(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: user_social_data user_social_data_user_id_db8fc193_fk_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY user_social_data
    ADD CONSTRAINT user_social_data_user_id_db8fc193_fk_user_id FOREIGN KEY (user_id) REFERENCES "user"(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: user_user_permissions user_user_permission_permission_id_9deb68a3_fk_auth_perm; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY user_user_permissions
    ADD CONSTRAINT user_user_permission_permission_id_9deb68a3_fk_auth_perm FOREIGN KEY (permission_id) REFERENCES auth_permission(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: user_user_permissions user_user_permissions_user_id_ed4a47ea_fk_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY user_user_permissions
    ADD CONSTRAINT user_user_permissions_user_id_ed4a47ea_fk_user_id FOREIGN KEY (user_id) REFERENCES "user"(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: vanity_url vanity_url_utm_term_id_607b87b5_fk_submarket_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY vanity_url
    ADD CONSTRAINT vanity_url_utm_term_id_607b87b5_fk_submarket_id FOREIGN KEY (utm_term_id) REFERENCES submarket(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: verification_attempt verification_attempt_consumer_verificatio_b13700ab_fk_consumer_; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY verification_attempt
    ADD CONSTRAINT verification_attempt_consumer_verificatio_b13700ab_fk_consumer_ FOREIGN KEY (consumer_verification_status_id) REFERENCES consumer_verification_status(consumer_id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: weather_forecast_model weather_forecast_mod_starting_point_id_34b704a0_fk_starting_; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY weather_forecast_model
    ADD CONSTRAINT weather_forecast_mod_starting_point_id_34b704a0_fk_starting_ FOREIGN KEY (starting_point_id) REFERENCES starting_point(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: weather_historical_model weather_historical_m_starting_point_id_6c48d392_fk_starting_; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY weather_historical_model
    ADD CONSTRAINT weather_historical_m_starting_point_id_6c48d392_fk_starting_ FOREIGN KEY (starting_point_id) REFERENCES starting_point(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: zendesk_template zendesk_template_category_id_fd246b35_fk_delivery_; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY zendesk_template
    ADD CONSTRAINT zendesk_template_category_id_fd246b35_fk_delivery_ FOREIGN KEY (category_id) REFERENCES delivery_event_category(id) DEFERRABLE INITIALLY DEFERRED;


--
-- PostgreSQL database dump complete
--
