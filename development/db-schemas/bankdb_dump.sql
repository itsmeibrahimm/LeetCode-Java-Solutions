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
-- Name: aggregate_report; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE aggregate_report (
    id integer NOT NULL,
    label text NOT NULL,
    active boolean NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: aggregate_report_entity; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE aggregate_report_entity (
    id integer NOT NULL,
    entity_id integer NOT NULL,
    entity_type text NOT NULL,
    created_at timestamp with time zone NOT NULL,
    aggregate_report_id integer NOT NULL
);


--
-- Name: aggregate_report_entity_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE aggregate_report_entity_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: aggregate_report_entity_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE aggregate_report_entity_id_seq OWNED BY aggregate_report_entity.id;


--
-- Name: aggregate_report_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE aggregate_report_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: aggregate_report_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE aggregate_report_id_seq OWNED BY aggregate_report.id;


--
-- Name: aggregate_report_recipient; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE aggregate_report_recipient (
    id integer NOT NULL,
    email character varying(254) NOT NULL,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: aggregate_report_recipient_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE aggregate_report_recipient_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: aggregate_report_recipient_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE aggregate_report_recipient_id_seq OWNED BY aggregate_report_recipient.id;


--
-- Name: aggregate_report_recipients; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE aggregate_report_recipients (
    id integer NOT NULL,
    aggregatereport_id integer NOT NULL,
    aggregatereportrecipient_id integer NOT NULL
);


--
-- Name: aggregate_report_recipients_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE aggregate_report_recipients_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: aggregate_report_recipients_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE aggregate_report_recipients_id_seq OWNED BY aggregate_report_recipients.id;


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
-- Name: payment_account_edit_history; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE payment_account_edit_history (
    id integer NOT NULL,
    "timestamp" timestamp with time zone NOT NULL,
    user_id integer,
    device_id text,
    ip text,
    payment_account_id integer,
    owner_type text,
    owner_id integer,
    account_type text NOT NULL,
    account_id integer NOT NULL,
    old_bank_name text,
    new_bank_name text NOT NULL,
    old_bank_last4 text,
    new_bank_last4 text NOT NULL,
    old_fingerprint text,
    new_fingerprint text NOT NULL,
    login_as_user_id integer,
    notes text,
    CONSTRAINT payment_account_edit_history_account_id_check CHECK ((account_id >= 0)),
    CONSTRAINT payment_account_edit_history_login_as_user_id_check CHECK ((login_as_user_id >= 0)),
    CONSTRAINT payment_account_edit_history_owner_id_check CHECK ((owner_id >= 0)),
    CONSTRAINT payment_account_edit_history_payment_account_id_check CHECK ((payment_account_id >= 0)),
    CONSTRAINT payment_account_edit_history_user_id_check CHECK ((user_id >= 0))
);


--
-- Name: payment_account_edit_history_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE payment_account_edit_history_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: payment_account_edit_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE payment_account_edit_history_id_seq OWNED BY payment_account_edit_history.id;


--
-- Name: payment_summary_email; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE payment_summary_email (
    id integer NOT NULL,
    store_id integer NOT NULL,
    label text NOT NULL,
    start_datetime timestamp with time zone NOT NULL,
    end_datetime timestamp with time zone NOT NULL,
    data jsonb,
    related_transfer_id integer,
    last_scheduled_datetime timestamp with time zone NOT NULL,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: payment_summary_email_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE payment_summary_email_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: payment_summary_email_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE payment_summary_email_id_seq OWNED BY payment_summary_email.id;


--
-- Name: payout_accounts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE payout_accounts (
    id integer NOT NULL,
    stripe_bank_account_id text NOT NULL,
    last4 text NOT NULL,
    bank_name text NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: payout_accounts_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE payout_accounts_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: payout_accounts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE payout_accounts_id_seq OWNED BY payout_accounts.id;


--
-- Name: payout_cards; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE payout_cards (
    id integer NOT NULL,
    stripe_card_id text NOT NULL,
    last4 text NOT NULL,
    exp_month integer NOT NULL,
    exp_year integer NOT NULL,
    brand text NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    fingerprint text
);


--
-- Name: payout_cards_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE payout_cards_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: payout_cards_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE payout_cards_id_seq OWNED BY payout_cards.id;


--
-- Name: payout_methods; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE payout_methods (
    id integer NOT NULL,
    type text NOT NULL,
    currency text NOT NULL,
    country text NOT NULL,
    payment_account_id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    is_default boolean,
    token text NOT NULL,
    deleted_at timestamp with time zone
);


--
-- Name: payout_methods_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE payout_methods_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: payout_methods_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE payout_methods_id_seq OWNED BY payout_methods.id;


--
-- Name: payouts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE payouts (
    id integer NOT NULL,
    amount integer NOT NULL,
    payment_account_id integer NOT NULL,
    status text NOT NULL,
    currency text NOT NULL,
    fee integer NOT NULL,
    type text NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    idempotency_key text NOT NULL,
    payout_method_id integer,
    transaction_ids integer[] NOT NULL,
    token text NOT NULL,
    fee_transaction_id integer,
    error text
);


--
-- Name: payouts_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE payouts_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: payouts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE payouts_id_seq OWNED BY payouts.id;


--
-- Name: stripe_payout_requests; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE stripe_payout_requests (
    id integer NOT NULL,
    idempotency_key text NOT NULL,
    payout_method_id integer NOT NULL,
    response text,
    created_at timestamp with time zone NOT NULL,
    received_at timestamp with time zone,
    updated_at timestamp with time zone NOT NULL,
    stripe_payout_id text,
    request text,
    status text NOT NULL,
    events text,
    stripe_account_id text,
    payout_id integer NOT NULL
);


--
-- Name: stripe_payout_requests_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE stripe_payout_requests_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: stripe_payout_requests_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE stripe_payout_requests_id_seq OWNED BY stripe_payout_requests.id;


--
-- Name: stripe_transfer_requests; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE stripe_transfer_requests (
    id integer NOT NULL,
    response text,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    received_at timestamp with time zone,
    request text NOT NULL,
    response_status_code integer,
    stripe_transfer_id text,
    transfer_id integer NOT NULL
);


--
-- Name: stripe_transfer_requests_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE stripe_transfer_requests_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: stripe_transfer_requests_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE stripe_transfer_requests_id_seq OWNED BY stripe_transfer_requests.id;


--
-- Name: transaction_status_histories; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE transaction_status_histories (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    transaction_id integer NOT NULL,
    status_id integer NOT NULL
);


--
-- Name: transaction_status_histories_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE transaction_status_histories_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: transaction_status_histories_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE transaction_status_histories_id_seq OWNED BY transaction_status_histories.id;


--
-- Name: transaction_statuses; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE transaction_statuses (
    id integer NOT NULL,
    status_name text
);


--
-- Name: transaction_statuses_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE transaction_statuses_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: transaction_statuses_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE transaction_statuses_id_seq OWNED BY transaction_statuses.id;


--
-- Name: transactions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE transactions (
    id integer NOT NULL,
    amount integer NOT NULL,
    payment_account_id integer NOT NULL,
    transfer_id integer,
    amount_paid integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    created_by_id integer,
    notes text,
    metadata text,
    idempotency_key text,
    currency text,
    target_id integer,
    target_type text,
    state text,
    updated_at timestamp with time zone NOT NULL,
    dsj_id integer,
    payout_id integer,
    inserted_at timestamp with time zone
);


--
-- Name: transactions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE transactions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: transactions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE transactions_id_seq OWNED BY transactions.id;


--
-- Name: transfer_transactions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE transfer_transactions (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    transaction_id integer NOT NULL,
    transfer_id integer NOT NULL
);


--
-- Name: transfer_transactions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE transfer_transactions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: transfer_transactions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE transfer_transactions_id_seq OWNED BY transfer_transactions.id;


--
-- Name: transfers; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE transfers (
    id integer NOT NULL,
    amount integer NOT NULL,
    from_stripe_account_id text NOT NULL,
    to_stripe_account_id text NOT NULL,
    token text NOT NULL,
    fee integer,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: transfers_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE transfers_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: transfers_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE transfers_id_seq OWNED BY transfers.id;


--
-- Name: aggregate_report id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY aggregate_report ALTER COLUMN id SET DEFAULT nextval('aggregate_report_id_seq'::regclass);


--
-- Name: aggregate_report_entity id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY aggregate_report_entity ALTER COLUMN id SET DEFAULT nextval('aggregate_report_entity_id_seq'::regclass);


--
-- Name: aggregate_report_recipient id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY aggregate_report_recipient ALTER COLUMN id SET DEFAULT nextval('aggregate_report_recipient_id_seq'::regclass);


--
-- Name: aggregate_report_recipients id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY aggregate_report_recipients ALTER COLUMN id SET DEFAULT nextval('aggregate_report_recipients_id_seq'::regclass);


--
-- Name: django_migrations id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY django_migrations ALTER COLUMN id SET DEFAULT nextval('django_migrations_id_seq'::regclass);


--
-- Name: payment_account_edit_history id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY payment_account_edit_history ALTER COLUMN id SET DEFAULT nextval('payment_account_edit_history_id_seq'::regclass);


--
-- Name: payment_summary_email id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY payment_summary_email ALTER COLUMN id SET DEFAULT nextval('payment_summary_email_id_seq'::regclass);


--
-- Name: payout_accounts id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY payout_accounts ALTER COLUMN id SET DEFAULT nextval('payout_accounts_id_seq'::regclass);


--
-- Name: payout_cards id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY payout_cards ALTER COLUMN id SET DEFAULT nextval('payout_cards_id_seq'::regclass);


--
-- Name: payout_methods id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY payout_methods ALTER COLUMN id SET DEFAULT nextval('payout_methods_id_seq'::regclass);


--
-- Name: payouts id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY payouts ALTER COLUMN id SET DEFAULT nextval('payouts_id_seq'::regclass);


--
-- Name: stripe_payout_requests id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY stripe_payout_requests ALTER COLUMN id SET DEFAULT nextval('stripe_payout_requests_id_seq'::regclass);


--
-- Name: stripe_transfer_requests id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY stripe_transfer_requests ALTER COLUMN id SET DEFAULT nextval('stripe_transfer_requests_id_seq'::regclass);


--
-- Name: transaction_status_histories id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY transaction_status_histories ALTER COLUMN id SET DEFAULT nextval('transaction_status_histories_id_seq'::regclass);


--
-- Name: transaction_statuses id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY transaction_statuses ALTER COLUMN id SET DEFAULT nextval('transaction_statuses_id_seq'::regclass);


--
-- Name: transactions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY transactions ALTER COLUMN id SET DEFAULT nextval('transactions_id_seq'::regclass);


--
-- Name: transfer_transactions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY transfer_transactions ALTER COLUMN id SET DEFAULT nextval('transfer_transactions_id_seq'::regclass);


--
-- Name: transfers id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY transfers ALTER COLUMN id SET DEFAULT nextval('transfers_id_seq'::regclass);


--
-- Data for Name: aggregate_report; Type: TABLE DATA; Schema: public; Owner: -
--

COPY aggregate_report (id, label, active, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: aggregate_report_entity; Type: TABLE DATA; Schema: public; Owner: -
--

COPY aggregate_report_entity (id, entity_id, entity_type, created_at, aggregate_report_id) FROM stdin;
\.


--
-- Name: aggregate_report_entity_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('aggregate_report_entity_id_seq', 1, false);


--
-- Name: aggregate_report_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('aggregate_report_id_seq', 1, false);


--
-- Data for Name: aggregate_report_recipient; Type: TABLE DATA; Schema: public; Owner: -
--

COPY aggregate_report_recipient (id, email, created_at) FROM stdin;
\.


--
-- Name: aggregate_report_recipient_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('aggregate_report_recipient_id_seq', 1, false);


--
-- Data for Name: aggregate_report_recipients; Type: TABLE DATA; Schema: public; Owner: -
--

COPY aggregate_report_recipients (id, aggregatereport_id, aggregatereportrecipient_id) FROM stdin;
\.


--
-- Name: aggregate_report_recipients_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('aggregate_report_recipients_id_seq', 1, false);


--
-- Data for Name: django_migrations; Type: TABLE DATA; Schema: public; Owner: -
--

COPY django_migrations (id, app, name, applied) FROM stdin;
1	contenttypes	0001_initial	2019-08-04 03:30:37.759419+00
2	contenttypes	0002_remove_content_type_name	2019-08-04 03:30:37.779675+00
3	auth	0001_initial	2019-08-04 03:30:37.803776+00
4	auth	0002_alter_permission_name_max_length	2019-08-04 03:30:37.974859+00
5	auth	0003_alter_user_email_max_length	2019-08-04 03:30:38.000285+00
6	auth	0004_alter_user_username_opts	2019-08-04 03:30:38.012813+00
7	auth	0005_alter_user_last_login_null	2019-08-04 03:30:38.027141+00
8	auth	0006_require_contenttypes_0002	2019-08-04 03:30:38.030291+00
9	auth	0007_alter_validators_add_error_messages	2019-08-04 03:30:38.042638+00
10	accounts	0001_initial	2019-08-04 03:30:38.118751+00
11	doordash	0001_initial	2019-08-04 03:30:40.997014+00
12	accounts	0002_auto_20190313_2101	2019-08-04 03:30:41.382888+00
13	accounts	0003_userlocalepreference	2019-08-04 03:30:41.417969+00
14	accounts	0004_auto_20190528_1346	2019-08-04 03:30:41.450715+00
15	accounts	0005_devicefingerprint_abuse_reason	2019-08-04 03:30:41.481247+00
16	accounts	0006_remove_cascading_delete	2019-08-04 03:30:41.586672+00
17	accounts	0007_fingerprint_updated_at	2019-08-04 03:30:41.652951+00
18	admin	0001_initial	2019-08-04 03:30:41.696012+00
19	admin	0002_logentry_remove_auto_add	2019-08-04 03:30:41.73355+00
20	app_deploy	0001_initial	2019-08-04 03:30:41.786715+00
21	assignment	0001_initial	2019-08-04 03:30:41.806757+00
22	assignment	0002_shiftdeliverysetassignment	2019-08-04 03:30:41.827442+00
23	assignment	0003_shiftdeliveryassignment2_estimation_info	2019-08-04 03:30:41.851221+00
24	auth	0008_alter_user_username_max_length	2019-08-04 03:30:41.885178+00
25	authtoken	0001_initial	2019-08-04 03:30:41.920551+00
26	authtoken	0002_auto_20160226_1747	2019-08-04 03:30:42.461147+00
27	merchant	0001_initial	2019-08-04 03:30:45.212841+00
28	doordash	0002_auto_20190313_2101	2019-08-04 03:30:52.99953+00
29	dasher	0001_initial	2019-08-04 03:30:54.682061+00
30	dasher	0002_auto_20190313_2101	2019-08-04 03:30:59.030919+00
31	payments	0001_initial	2019-08-04 03:31:09.405754+00
32	ios_notifications	0001_initial	2019-08-04 03:31:10.696255+00
33	ios_notifications	0002_notification_silent	2019-08-04 03:31:10.735968+00
34	ios_notifications	0003_notification_loc_payload	2019-08-04 03:31:10.774316+00
35	ios_notifications	0004_auto_20141105_1515	2019-08-04 03:31:10.815058+00
36	dasher	0003_auto_20190313_2101	2019-08-04 03:31:36.548577+00
37	doordash	0003_auto_20190313_2101	2019-08-04 03:33:35.135588+00
38	doordash	0004_referral_not_credited_reason	2019-08-04 03:33:35.209153+00
39	doordash	0005_auto_20190314_1654	2019-08-04 03:33:35.357212+00
40	doordash	0006_delete_unused_tables	2019-08-04 03:33:36.582971+00
41	doordash	0007_remove_deliveryrequest	2019-08-04 03:33:41.967693+00
42	doordash	0008_notified_cx_request	2019-08-04 03:33:42.11321+00
43	doordash	0009_driveorder_cancelled_at	2019-08-04 03:33:42.149449+00
44	doordash	0010_consumerstorerequest_store_activation_date	2019-08-04 03:33:42.221116+00
45	doordash	0011_auto_20190326_2104	2019-08-04 03:33:42.363914+00
46	doordash	0012_auto_20190401_1645	2019-08-04 03:33:42.453484+00
47	doordash	0013_auto_20190408_1316	2019-08-04 03:33:42.917561+00
48	doordash	0014_auto_20190409_1641	2019-08-04 03:33:42.979331+00
49	doordash	0015_deliverysimulator_store_id	2019-08-04 03:33:43.085065+00
50	doordash	0016_auto_20190410_1526	2019-08-04 03:33:43.40603+00
51	doordash	0017_bogo_promotion_second_item_promo	2019-08-04 03:33:44.523243+00
52	doordash	0018_eta_pred_no_cascade_delete	2019-08-04 03:33:44.813498+00
53	doordash	0019_consumer_vip_tier	2019-08-04 03:33:44.945688+00
54	doordash	0020_auto_20190424_1123	2019-08-04 03:33:45.210787+00
55	doordash	0021_auto_20190424_1348	2019-08-04 03:33:45.459203+00
56	doordash	0022_remove_consumer_is_vip	2019-08-04 03:33:45.54853+00
57	doordash	0023_deliveryassignmentconstraint_preferred_dasher_equipment_ids	2019-08-04 03:33:45.579529+00
58	doordash	0024_experiment2_mobile_version_rules	2019-08-04 03:33:45.635998+00
59	doordash	0025_driveorder_external_order_status	2019-08-04 03:33:45.671844+00
60	doordash	0026_auto_20190501_1125	2019-08-04 03:33:45.830934+00
61	doordash	0027_driveorder_aggregator_fee	2019-08-04 03:33:45.866821+00
62	doordash	0028_storeordercart_updated_at	2019-08-04 03:33:45.94858+00
63	doordash	0029_auto_20190514_2319	2019-08-04 03:33:46.08974+00
64	doordash	0030_remove_storeordercart_updated_at	2019-08-04 03:33:46.174275+00
65	doordash	0031_auto_20190508_0453	2019-08-04 03:33:46.196763+00
66	doordash	0032_auto_20190521_1040	2019-08-04 03:33:46.360373+00
67	doordash	0033_auto_20190524_1531	2019-08-04 03:33:46.398867+00
68	doordash	0034_add_fr_ca_columns_to_support_i18n	2019-08-04 03:33:47.422742+00
69	doordash	0035_auto_20190529_1636	2019-08-04 03:33:47.516113+00
70	doordash	0036_experiment2_enable_real_time_tracking	2019-08-04 03:33:47.570791+00
71	doordash	0037_auto_20190530_1048	2019-08-04 03:33:47.644654+00
72	doordash	0038_auto_20190530_1017	2019-08-04 03:33:47.685159+00
73	doordash	0039_auto_20190603_0946	2019-08-04 03:33:47.788796+00
74	doordash	0040_auto_20190604_1331	2019-08-04 03:33:47.867318+00
75	doordash	0041_market_updated_at	2019-08-04 03:33:47.933684+00
76	doordash	0042_dispatcher_can_edit_delivery	2019-08-04 03:33:47.992332+00
77	doordash	0043_delivery_is_group_cart_delivery	2019-08-04 03:33:48.332564+00
78	doordash	0044_deliverysetmapping_removed_at	2019-08-04 03:33:48.368674+00
79	doordash	0045_idempotency_key	2019-08-04 03:33:48.541348+00
80	doordash	0046_consumerpromotion_is_active	2019-08-04 03:33:48.667459+00
81	doordash	0047_address_formatted_address_and_name	2019-08-04 03:33:48.782824+00
82	doordash	0048_country_allows_pre_tipping	2019-08-04 03:33:48.822556+00
83	doordash	0049_storeordercart_delivery_id	2019-08-04 03:33:48.901049+00
84	doordash	0050_auto_20190624_1554	2019-08-04 03:33:49.126805+00
85	doordash	0051_fix_cascading_deletes	2019-08-04 03:33:55.570133+00
86	doordash	0052_remove_menu_fk	2019-08-04 03:33:56.019416+00
87	doordash	0053_variable_can_edit	2019-08-04 03:33:56.057278+00
88	doordash	0054_idempotency_key_uniqueness	2019-08-04 03:33:56.31173+00
89	doordash	0055_driveorder_post_tip	2019-08-04 03:33:56.352102+00
90	dasher	0004_dasher_deactivation	2019-08-04 03:33:56.621572+00
91	dasher	0005_dasherdeliverypay_adjustment_amount	2019-08-04 03:33:56.696691+00
92	dasher	0006_auto_20190423_1817	2019-08-04 03:33:56.826483+00
93	dasher	0007_dasher_feature_preference	2019-08-04 03:33:56.906598+00
94	dasher	0008_deliveryreference	2019-08-04 03:33:56.930138+00
95	dasher	0009_auto_20190513_1359	2019-08-04 03:33:56.961653+00
96	dasher	0010_deliverydepot	2019-08-04 03:33:56.985438+00
97	dasher	0011_dasher_challenge	2019-08-04 03:33:57.071616+00
98	dasher	0012_auto_20190528_2332	2019-08-04 03:33:57.191444+00
99	dasher	0013_auto_20190603_2303	2019-08-04 03:33:57.259693+00
100	dasher	0014_dasheraustraliantaxinfo	2019-08-04 03:33:57.284358+00
101	dasher	0015_auto_20190622_1945	2019-08-04 03:33:57.539643+00
102	dasher	0016_auto_20190701_1332	2019-08-04 03:33:57.591823+00
103	dasher	0017_auto_20190702_0021	2019-08-04 03:33:59.151162+00
104	dasher	0018_auto_20190712_1136	2019-08-04 03:33:59.806503+00
105	dasher	0019_dasherapplicant_referral_campaign	2019-08-04 03:34:00.237547+00
106	dasher	0020_auto_20190722_1613	2019-08-04 03:34:00.40077+00
107	dasher	0021_auto_20190802_1926	2019-08-04 03:34:00.692594+00
108	django_twilio	0001_initial	2019-08-04 03:34:01.103997+00
109	payments	0002_stripecard_external_stripe_customer_id	2019-08-04 03:34:01.219158+00
110	payments	0003_transaction_inserted_at	2019-08-04 03:34:02.067706+00
111	payments	0004_stripecard_tokenization_method	2019-08-04 03:34:02.193179+00
112	payments	0005_stripecharge_updated_at	2019-08-04 03:34:02.255443+00
113	payments	0006_auto_20190422_0856	2019-08-04 03:34:03.126558+00
114	payments	0007_paymentaccountedithistory_login_as_user_id	2019-08-04 03:34:03.160114+00
115	payments	0008_scan_card_challege_field	2019-08-04 03:34:03.350389+00
116	payments	0009_paymentaccountedithistory_notes	2019-08-04 03:34:03.386555+00
117	payments	0010_charge_updated_at	2019-08-04 03:34:03.460616+00
118	payments	0011_remove_charge_updated_at	2019-08-04 03:34:04.473548+00
119	doordash	0056_order_payment_information	2019-08-04 03:34:05.064276+00
120	doordash	0057_auto_20190725_0931	2019-08-04 03:34:05.46093+00
121	doordash	0058_consumerpromotion_success_message	2019-08-04 03:34:05.641021+00
122	doordash	0059_auto_20190731_1148	2019-08-04 03:34:06.058336+00
123	encrypted_pii	0001_initial	2019-08-04 03:34:06.119643+00
124	invoicing	0001_initial	2019-08-04 03:34:06.262956+00
125	merchant	0002_auto_20190313_2101	2019-08-04 03:35:31.055522+00
126	merchant	0003_storebountyprogramlink_deactivated_at	2019-08-04 03:35:31.146509+00
127	merchant	0004_auto_20190325_1849	2019-08-04 03:35:31.691676+00
128	merchant	0005_store_activation_source	2019-08-04 03:35:31.863086+00
129	merchant	0006_store_fulfills_own_deliveries_disabled	2019-08-04 03:35:32.036881+00
130	merchant	0007_auto_20190408_1416	2019-08-04 03:35:32.040223+00
131	merchant	0008_auto_20190408_1441	2019-08-04 03:35:32.108545+00
132	merchant	0009_auto_20190411_1031	2019-08-04 03:35:32.14636+00
133	merchant	0010_storeitemextradeactivation	2019-08-04 03:35:32.171685+00
134	merchant	0011_store_max_delivery_polygon	2019-08-04 03:35:32.326972+00
135	merchant	0012_alter_email_helper_text	2019-08-04 03:35:32.488958+00
136	merchant	0013_auto_20190501_1059	2019-08-04 03:35:32.561916+00
137	merchant	0014_temporarydeactivation_timezone	2019-08-04 03:35:32.681798+00
138	merchant	0015_auto_20190515_1807	2019-08-04 03:35:32.859695+00
139	merchant	0016_itemextraoption_itemvehicletypelink_timestamp	2019-08-04 03:35:33.129214+00
140	merchant	0017_merchantpromotionstoreordercartlink	2019-08-04 03:35:33.161408+00
141	merchant	0018_menutopilotmenu	2019-08-04 03:35:33.194245+00
142	merchant	0019_printer_fee	2019-08-04 03:35:33.386611+00
143	merchant	0020_store_subscription_commission_trial_end_time	2019-08-04 03:35:33.496064+00
144	merchant	0021_create_created_deactivated_by	2019-08-04 03:35:33.706576+00
145	merchant	0022_remove_id_column_move_to_etl	2019-08-04 03:35:33.750452+00
146	merchant	0023_merchantpromotiontarget	2019-08-04 03:35:34.99246+00
147	merchant	0024_opaqueidmapping	2019-08-04 03:35:35.022887+00
148	merchant	0025_auto_20190612_1500	2019-08-04 03:35:35.065067+00
149	merchant	0026_merchantpromotionstoreordercartlink_bcs_promotion_uuid	2019-08-04 03:35:35.102501+00
150	merchant	0027_merchantpromotiontarget_bcs_promotion_uuid	2019-08-04 03:35:35.143014+00
151	merchant	0028_auto_20190618_1247	2019-08-04 03:35:35.215882+00
152	merchant	0029_builtintaxcategoryrule	2019-08-04 03:35:35.248276+00
153	merchant	0030_merchantpromotion_generated_codes_for_consumer_table	2019-08-04 03:35:35.322208+00
154	merchant	0031_menudb_into_merchantdb_migration	2019-08-04 03:35:36.252914+00
155	merchant	0032_menu_source_of_creation	2019-08-04 03:35:36.315909+00
156	merchant	0033_auto_20190725_1112	2019-08-04 03:35:36.498648+00
157	merchant	0034_modify_merchant_promotion	2019-08-04 03:35:36.677943+00
158	merchant	0035_merchantpromotionstoreordercartlink_created_at	2019-08-04 03:35:36.712517+00
159	merchant	0036_storepromotionmembership_created_at	2019-08-04 03:35:36.792889+00
160	merchant	0037_qrcode_qrcodeaction	2019-08-04 03:35:37.431683+00
161	payments	0012_auto_20190718_1023	2019-08-04 03:35:37.581394+00
162	refreshtoken	0001_initial	2019-08-04 03:35:38.057804+00
163	scheduler	0001_initial	2019-08-04 03:35:38.094115+00
164	scheduler	0002_regionscheduledtask	2019-08-04 03:35:38.129921+00
165	scheduler	0003_auto_20190603_1341	2019-08-04 03:35:38.1783+00
166	security	0001_initial	2019-08-04 03:35:38.563352+00
167	sessions	0001_initial	2019-08-04 03:35:38.594234+00
168	support	0001_initial	2019-08-04 03:35:38.973663+00
169	version	0001_initial	2019-08-04 03:35:39.00673+00
\.


--
-- Name: django_migrations_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('django_migrations_id_seq', 169, true);


--
-- Data for Name: payment_account_edit_history; Type: TABLE DATA; Schema: public; Owner: -
--

COPY payment_account_edit_history (id, "timestamp", user_id, device_id, ip, payment_account_id, owner_type, owner_id, account_type, account_id, old_bank_name, new_bank_name, old_bank_last4, new_bank_last4, old_fingerprint, new_fingerprint, login_as_user_id, notes) FROM stdin;
\.


--
-- Name: payment_account_edit_history_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('payment_account_edit_history_id_seq', 1, false);


--
-- Data for Name: payment_summary_email; Type: TABLE DATA; Schema: public; Owner: -
--

COPY payment_summary_email (id, store_id, label, start_datetime, end_datetime, data, related_transfer_id, last_scheduled_datetime, created_at) FROM stdin;
\.


--
-- Name: payment_summary_email_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('payment_summary_email_id_seq', 1, false);


--
-- Data for Name: payout_accounts; Type: TABLE DATA; Schema: public; Owner: -
--

COPY payout_accounts (id, stripe_bank_account_id, last4, bank_name, created_at, updated_at) FROM stdin;
\.


--
-- Name: payout_accounts_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('payout_accounts_id_seq', 1, false);


--
-- Data for Name: payout_cards; Type: TABLE DATA; Schema: public; Owner: -
--

COPY payout_cards (id, stripe_card_id, last4, exp_month, exp_year, brand, created_at, updated_at, fingerprint) FROM stdin;
\.


--
-- Name: payout_cards_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('payout_cards_id_seq', 1, false);


--
-- Data for Name: payout_methods; Type: TABLE DATA; Schema: public; Owner: -
--

COPY payout_methods (id, type, currency, country, payment_account_id, created_at, updated_at, is_default, token, deleted_at) FROM stdin;
\.


--
-- Name: payout_methods_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('payout_methods_id_seq', 1, false);


--
-- Data for Name: payouts; Type: TABLE DATA; Schema: public; Owner: -
--

COPY payouts (id, amount, payment_account_id, status, currency, fee, type, created_at, updated_at, idempotency_key, payout_method_id, transaction_ids, token, fee_transaction_id, error) FROM stdin;
\.


--
-- Name: payouts_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('payouts_id_seq', 1, false);


--
-- Data for Name: stripe_payout_requests; Type: TABLE DATA; Schema: public; Owner: -
--

COPY stripe_payout_requests (id, idempotency_key, payout_method_id, response, created_at, received_at, updated_at, stripe_payout_id, request, status, events, stripe_account_id, payout_id) FROM stdin;
\.


--
-- Name: stripe_payout_requests_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('stripe_payout_requests_id_seq', 1, false);


--
-- Data for Name: stripe_transfer_requests; Type: TABLE DATA; Schema: public; Owner: -
--

COPY stripe_transfer_requests (id, response, created_at, updated_at, received_at, request, response_status_code, stripe_transfer_id, transfer_id) FROM stdin;
\.


--
-- Name: stripe_transfer_requests_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('stripe_transfer_requests_id_seq', 1, false);


--
-- Data for Name: transaction_status_histories; Type: TABLE DATA; Schema: public; Owner: -
--

COPY transaction_status_histories (id, created_at, updated_at, transaction_id, status_id) FROM stdin;
\.


--
-- Name: transaction_status_histories_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('transaction_status_histories_id_seq', 1, false);


--
-- Data for Name: transaction_statuses; Type: TABLE DATA; Schema: public; Owner: -
--

COPY transaction_statuses (id, status_name) FROM stdin;
\.


--
-- Name: transaction_statuses_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('transaction_statuses_id_seq', 1, false);


--
-- Data for Name: transactions; Type: TABLE DATA; Schema: public; Owner: -
--

COPY transactions (id, amount, payment_account_id, transfer_id, amount_paid, created_at, created_by_id, notes, metadata, idempotency_key, currency, target_id, target_type, state, updated_at, dsj_id, payout_id, inserted_at) FROM stdin;
\.


--
-- Name: transactions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('transactions_id_seq', 1, false);


--
-- Data for Name: transfer_transactions; Type: TABLE DATA; Schema: public; Owner: -
--

COPY transfer_transactions (id, created_at, transaction_id, transfer_id) FROM stdin;
\.


--
-- Name: transfer_transactions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('transfer_transactions_id_seq', 1, false);


--
-- Data for Name: transfers; Type: TABLE DATA; Schema: public; Owner: -
--

COPY transfers (id, amount, from_stripe_account_id, to_stripe_account_id, token, fee, created_at, updated_at) FROM stdin;
\.


--
-- Name: transfers_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('transfers_id_seq', 1, false);


--
-- Name: aggregate_report_entity aggregate_report_entity_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY aggregate_report_entity
    ADD CONSTRAINT aggregate_report_entity_pkey PRIMARY KEY (id);


--
-- Name: aggregate_report aggregate_report_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY aggregate_report
    ADD CONSTRAINT aggregate_report_pkey PRIMARY KEY (id);


--
-- Name: aggregate_report_recipients aggregate_report_recipie_aggregatereport_id_aggre_670056a8_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY aggregate_report_recipients
    ADD CONSTRAINT aggregate_report_recipie_aggregatereport_id_aggre_670056a8_uniq UNIQUE (aggregatereport_id, aggregatereportrecipient_id);


--
-- Name: aggregate_report_recipient aggregate_report_recipient_email_d9d319ca_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY aggregate_report_recipient
    ADD CONSTRAINT aggregate_report_recipient_email_d9d319ca_uniq UNIQUE (email);


--
-- Name: aggregate_report_recipient aggregate_report_recipient_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY aggregate_report_recipient
    ADD CONSTRAINT aggregate_report_recipient_pkey PRIMARY KEY (id);


--
-- Name: aggregate_report_recipients aggregate_report_recipients_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY aggregate_report_recipients
    ADD CONSTRAINT aggregate_report_recipients_pkey PRIMARY KEY (id);


--
-- Name: django_migrations django_migrations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY django_migrations
    ADD CONSTRAINT django_migrations_pkey PRIMARY KEY (id);


--
-- Name: payment_account_edit_history payment_account_edit_history_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY payment_account_edit_history
    ADD CONSTRAINT payment_account_edit_history_pkey PRIMARY KEY (id);


--
-- Name: payment_summary_email payment_summary_email_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY payment_summary_email
    ADD CONSTRAINT payment_summary_email_pkey PRIMARY KEY (id);


--
-- Name: payout_accounts payout_accounts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY payout_accounts
    ADD CONSTRAINT payout_accounts_pkey PRIMARY KEY (id);


--
-- Name: payout_cards payout_cards_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY payout_cards
    ADD CONSTRAINT payout_cards_pkey PRIMARY KEY (id);


--
-- Name: payout_methods payout_methods_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY payout_methods
    ADD CONSTRAINT payout_methods_pkey PRIMARY KEY (id);


--
-- Name: payouts payouts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY payouts
    ADD CONSTRAINT payouts_pkey PRIMARY KEY (id);


--
-- Name: stripe_payout_requests stripe_payout_requests_payout_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY stripe_payout_requests
    ADD CONSTRAINT stripe_payout_requests_payout_id_key UNIQUE (payout_id);


--
-- Name: stripe_payout_requests stripe_payout_requests_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY stripe_payout_requests
    ADD CONSTRAINT stripe_payout_requests_pkey PRIMARY KEY (id);


--
-- Name: stripe_transfer_requests stripe_transfer_requests_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY stripe_transfer_requests
    ADD CONSTRAINT stripe_transfer_requests_pkey PRIMARY KEY (id);


--
-- Name: transaction_status_histories transaction_status_histories_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY transaction_status_histories
    ADD CONSTRAINT transaction_status_histories_pkey PRIMARY KEY (id);


--
-- Name: transaction_statuses transaction_statuses_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY transaction_statuses
    ADD CONSTRAINT transaction_statuses_pkey PRIMARY KEY (id);


--
-- Name: transactions transactions_idempotency_key_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY transactions
    ADD CONSTRAINT transactions_idempotency_key_key UNIQUE (idempotency_key);


--
-- Name: transactions transactions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY transactions
    ADD CONSTRAINT transactions_pkey PRIMARY KEY (id);


--
-- Name: transfer_transactions transfer_transactions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY transfer_transactions
    ADD CONSTRAINT transfer_transactions_pkey PRIMARY KEY (id);


--
-- Name: transfer_transactions transfer_transactions_transaction_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY transfer_transactions
    ADD CONSTRAINT transfer_transactions_transaction_id_key UNIQUE (transaction_id);


--
-- Name: transfer_transactions transfer_transactions_transfer_id_transaction_id_36e1564f_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY transfer_transactions
    ADD CONSTRAINT transfer_transactions_transfer_id_transaction_id_36e1564f_uniq UNIQUE (transfer_id, transaction_id);


--
-- Name: transfers transfers_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY transfers
    ADD CONSTRAINT transfers_pkey PRIMARY KEY (id);


--
-- Name: aggregate_report_entity_aggregate_report_id_3a9b08a2; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX aggregate_report_entity_aggregate_report_id_3a9b08a2 ON aggregate_report_entity USING btree (aggregate_report_id);


--
-- Name: aggregate_report_entity_entity_id_entity_type_11fc1050_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX aggregate_report_entity_entity_id_entity_type_11fc1050_idx ON aggregate_report_entity USING btree (entity_id, entity_type);


--
-- Name: aggregate_report_recipient_aggregatereportrecipient_i_ba51bc2e; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX aggregate_report_recipient_aggregatereportrecipient_i_ba51bc2e ON aggregate_report_recipients USING btree (aggregatereportrecipient_id);


--
-- Name: aggregate_report_recipients_aggregatereport_id_a6d17f1f; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX aggregate_report_recipients_aggregatereport_id_a6d17f1f ON aggregate_report_recipients USING btree (aggregatereport_id);


--
-- Name: payment_account_edit_history_payment_account_id_faece59b; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX payment_account_edit_history_payment_account_id_faece59b ON payment_account_edit_history USING btree (payment_account_id);


--
-- Name: payment_account_edit_history_timestamp_d844da77; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX payment_account_edit_history_timestamp_d844da77 ON payment_account_edit_history USING btree ("timestamp");


--
-- Name: payment_summary_email_store_id_7bc3b1cb; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX payment_summary_email_store_id_7bc3b1cb ON payment_summary_email USING btree (store_id);


--
-- Name: stripe_transfer_requests_transfer_id_cd5be9ab; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX stripe_transfer_requests_transfer_id_cd5be9ab ON stripe_transfer_requests USING btree (transfer_id);


--
-- Name: transactions_created_at_3143a260; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX transactions_created_at_3143a260 ON transactions USING btree (created_at);


--
-- Name: transactions_idempotency_key_47231c55_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX transactions_idempotency_key_47231c55_like ON transactions USING btree (idempotency_key text_pattern_ops);


--
-- Name: transfer_transactions_transfer_id_e14f919f; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX transfer_transactions_transfer_id_e14f919f ON transfer_transactions USING btree (transfer_id);


--
-- Name: aggregate_report_entity aggregate_report_ent_aggregate_report_id_3a9b08a2_fk_aggregate; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY aggregate_report_entity
    ADD CONSTRAINT aggregate_report_ent_aggregate_report_id_3a9b08a2_fk_aggregate FOREIGN KEY (aggregate_report_id) REFERENCES aggregate_report(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: aggregate_report_recipients aggregate_report_rec_aggregatereport_id_a6d17f1f_fk_aggregate; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY aggregate_report_recipients
    ADD CONSTRAINT aggregate_report_rec_aggregatereport_id_a6d17f1f_fk_aggregate FOREIGN KEY (aggregatereport_id) REFERENCES aggregate_report(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: aggregate_report_recipients aggregate_report_rec_aggregatereportrecip_ba51bc2e_fk_aggregate; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY aggregate_report_recipients
    ADD CONSTRAINT aggregate_report_rec_aggregatereportrecip_ba51bc2e_fk_aggregate FOREIGN KEY (aggregatereportrecipient_id) REFERENCES aggregate_report_recipient(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: stripe_payout_requests stripe_payout_requests_payout_id_5e426cba_fk_payouts_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY stripe_payout_requests
    ADD CONSTRAINT stripe_payout_requests_payout_id_5e426cba_fk_payouts_id FOREIGN KEY (payout_id) REFERENCES payouts(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: stripe_transfer_requests stripe_transfer_requests_transfer_id_cd5be9ab_fk_transfers_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY stripe_transfer_requests
    ADD CONSTRAINT stripe_transfer_requests_transfer_id_cd5be9ab_fk_transfers_id FOREIGN KEY (transfer_id) REFERENCES transfers(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: transfer_transactions transfer_transaction_transaction_id_5ed77f82_fk_transacti; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY transfer_transactions
    ADD CONSTRAINT transfer_transaction_transaction_id_5ed77f82_fk_transacti FOREIGN KEY (transaction_id) REFERENCES transactions(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: transfer_transactions transfer_transactions_transfer_id_e14f919f_fk_transfers_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY transfer_transactions
    ADD CONSTRAINT transfer_transactions_transfer_id_e14f919f_fk_transfers_id FOREIGN KEY (transfer_id) REFERENCES transfers(id) DEFERRABLE INITIALLY DEFERRED;


--
-- PostgreSQL database dump complete
--
