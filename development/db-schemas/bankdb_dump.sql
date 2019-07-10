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

