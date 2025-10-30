--
-- PostgreSQL database dump
--

\restrict GJ7bbCCsyYI2L45dKZgkhyM2UlmLa3j0jPYCNjMn0ZooWFgy2VMgJ21at3NBaJo

-- Dumped from database version 14.19
-- Dumped by pg_dump version 14.19

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: voyana
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO voyana;

--
-- Name: api_keys; Type: TABLE; Schema: public; Owner: voyana
--

CREATE TABLE public.api_keys (
    id integer NOT NULL,
    key character varying(64) NOT NULL,
    name character varying(64) NOT NULL,
    user_id integer,
    created_at timestamp without time zone NOT NULL,
    last_used_at timestamp without time zone,
    is_active boolean NOT NULL
);


ALTER TABLE public.api_keys OWNER TO voyana;

--
-- Name: api_keys_id_seq; Type: SEQUENCE; Schema: public; Owner: voyana
--

CREATE SEQUENCE public.api_keys_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.api_keys_id_seq OWNER TO voyana;

--
-- Name: api_keys_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: voyana
--

ALTER SEQUENCE public.api_keys_id_seq OWNED BY public.api_keys.id;


--
-- Name: audio_cache; Type: TABLE; Schema: public; Owner: voyana
--

CREATE TABLE public.audio_cache (
    id uuid NOT NULL,
    text_hash character varying(64) NOT NULL,
    text_content text NOT NULL,
    audio_url character varying(1024) NOT NULL,
    voice_id character varying(64) NOT NULL,
    created_at timestamp without time zone NOT NULL,
    last_accessed_at timestamp without time zone NOT NULL,
    access_count integer
);


ALTER TABLE public.audio_cache OWNER TO voyana;

--
-- Name: feedback; Type: TABLE; Schema: public; Owner: voyana
--

CREATE TABLE public.feedback (
    id integer NOT NULL,
    tour_id uuid,
    site_id uuid,
    user_id integer,
    feedback_type character varying(50) NOT NULL,
    rating integer,
    comment text,
    photo_data text,
    status character varying(20) NOT NULL,
    admin_notes text,
    created_at timestamp without time zone NOT NULL,
    reviewed_at timestamp without time zone,
    reviewed_by integer
);


ALTER TABLE public.feedback OWNER TO voyana;

--
-- Name: feedback_id_seq; Type: SEQUENCE; Schema: public; Owner: voyana
--

CREATE SEQUENCE public.feedback_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.feedback_id_seq OWNER TO voyana;

--
-- Name: feedback_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: voyana
--

ALTER SEQUENCE public.feedback_id_seq OWNED BY public.feedback.id;


--
-- Name: neighborhood_descriptions; Type: TABLE; Schema: public; Owner: voyana
--

CREATE TABLE public.neighborhood_descriptions (
    id integer NOT NULL,
    city character varying(100) NOT NULL,
    neighborhood character varying(100) NOT NULL,
    description text NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.neighborhood_descriptions OWNER TO voyana;

--
-- Name: neighborhood_descriptions_id_seq; Type: SEQUENCE; Schema: public; Owner: voyana
--

CREATE SEQUENCE public.neighborhood_descriptions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.neighborhood_descriptions_id_seq OWNER TO voyana;

--
-- Name: neighborhood_descriptions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: voyana
--

ALTER SEQUENCE public.neighborhood_descriptions_id_seq OWNED BY public.neighborhood_descriptions.id;


--
-- Name: password_reset_tokens; Type: TABLE; Schema: public; Owner: voyana
--

CREATE TABLE public.password_reset_tokens (
    id integer NOT NULL,
    user_id integer NOT NULL,
    token character varying(64) NOT NULL,
    expires_at timestamp without time zone NOT NULL,
    used boolean NOT NULL,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.password_reset_tokens OWNER TO voyana;

--
-- Name: password_reset_tokens_id_seq; Type: SEQUENCE; Schema: public; Owner: voyana
--

CREATE SEQUENCE public.password_reset_tokens_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.password_reset_tokens_id_seq OWNER TO voyana;

--
-- Name: password_reset_tokens_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: voyana
--

ALTER SEQUENCE public.password_reset_tokens_id_seq OWNED BY public.password_reset_tokens.id;


--
-- Name: sites; Type: TABLE; Schema: public; Owner: voyana
--

CREATE TABLE public.sites (
    id uuid NOT NULL,
    title character varying(200) NOT NULL,
    description text,
    latitude double precision NOT NULL,
    longitude double precision NOT NULL,
    user_submitted_locations double precision[],
    image_url character varying(1024),
    audio_url character varying(1024),
    web_url character varying(1024),
    keywords character varying(50)[],
    rating double precision,
    place_id character varying(255),
    formatted_address text,
    types character varying(50)[],
    user_ratings_total integer,
    phone_number text,
    google_photo_references character varying(1024)[],
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    city character varying(100),
    neighborhood character varying(100)
);


ALTER TABLE public.sites OWNER TO voyana;

--
-- Name: tour_sites; Type: TABLE; Schema: public; Owner: voyana
--

CREATE TABLE public.tour_sites (
    tour_id uuid NOT NULL,
    site_id uuid NOT NULL,
    display_order integer NOT NULL,
    visit_duration_minutes integer
);


ALTER TABLE public.tour_sites OWNER TO voyana;

--
-- Name: tours; Type: TABLE; Schema: public; Owner: voyana
--

CREATE TABLE public.tours (
    id uuid NOT NULL,
    owner_id integer NOT NULL,
    name character varying(200) NOT NULL,
    description text,
    city character varying(100),
    neighborhood character varying(100),
    latitude double precision,
    longitude double precision,
    image_url character varying(1024),
    audio_url character varying(1024),
    map_image_url character varying(1024),
    music_urls character varying(1024)[],
    duration_minutes integer,
    distance_meters double precision,
    status character varying(20) NOT NULL,
    is_public boolean NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    published_at timestamp without time zone
);


ALTER TABLE public.tours OWNER TO voyana;

--
-- Name: users; Type: TABLE; Schema: public; Owner: voyana
--

CREATE TABLE public.users (
    id integer NOT NULL,
    email character varying(255) NOT NULL,
    password_hash character varying(256),
    name character varying(255),
    role character varying(20) NOT NULL,
    google_id character varying(255),
    apple_id character varying(255),
    is_active boolean NOT NULL,
    email_verified boolean NOT NULL,
    created_at timestamp without time zone NOT NULL,
    last_login_at timestamp without time zone
);


ALTER TABLE public.users OWNER TO voyana;

--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: voyana
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.users_id_seq OWNER TO voyana;

--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: voyana
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: api_keys id; Type: DEFAULT; Schema: public; Owner: voyana
--

ALTER TABLE ONLY public.api_keys ALTER COLUMN id SET DEFAULT nextval('public.api_keys_id_seq'::regclass);


--
-- Name: feedback id; Type: DEFAULT; Schema: public; Owner: voyana
--

ALTER TABLE ONLY public.feedback ALTER COLUMN id SET DEFAULT nextval('public.feedback_id_seq'::regclass);


--
-- Name: neighborhood_descriptions id; Type: DEFAULT; Schema: public; Owner: voyana
--

ALTER TABLE ONLY public.neighborhood_descriptions ALTER COLUMN id SET DEFAULT nextval('public.neighborhood_descriptions_id_seq'::regclass);


--
-- Name: password_reset_tokens id; Type: DEFAULT; Schema: public; Owner: voyana
--

ALTER TABLE ONLY public.password_reset_tokens ALTER COLUMN id SET DEFAULT nextval('public.password_reset_tokens_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: voyana
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: voyana
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: api_keys api_keys_pkey; Type: CONSTRAINT; Schema: public; Owner: voyana
--

ALTER TABLE ONLY public.api_keys
    ADD CONSTRAINT api_keys_pkey PRIMARY KEY (id);


--
-- Name: audio_cache audio_cache_pkey; Type: CONSTRAINT; Schema: public; Owner: voyana
--

ALTER TABLE ONLY public.audio_cache
    ADD CONSTRAINT audio_cache_pkey PRIMARY KEY (id);


--
-- Name: feedback feedback_pkey; Type: CONSTRAINT; Schema: public; Owner: voyana
--

ALTER TABLE ONLY public.feedback
    ADD CONSTRAINT feedback_pkey PRIMARY KEY (id);


--
-- Name: neighborhood_descriptions neighborhood_descriptions_pkey; Type: CONSTRAINT; Schema: public; Owner: voyana
--

ALTER TABLE ONLY public.neighborhood_descriptions
    ADD CONSTRAINT neighborhood_descriptions_pkey PRIMARY KEY (id);


--
-- Name: password_reset_tokens password_reset_tokens_pkey; Type: CONSTRAINT; Schema: public; Owner: voyana
--

ALTER TABLE ONLY public.password_reset_tokens
    ADD CONSTRAINT password_reset_tokens_pkey PRIMARY KEY (id);


--
-- Name: sites sites_pkey; Type: CONSTRAINT; Schema: public; Owner: voyana
--

ALTER TABLE ONLY public.sites
    ADD CONSTRAINT sites_pkey PRIMARY KEY (id);


--
-- Name: tour_sites tour_sites_pkey; Type: CONSTRAINT; Schema: public; Owner: voyana
--

ALTER TABLE ONLY public.tour_sites
    ADD CONSTRAINT tour_sites_pkey PRIMARY KEY (tour_id, site_id);


--
-- Name: tours tours_pkey; Type: CONSTRAINT; Schema: public; Owner: voyana
--

ALTER TABLE ONLY public.tours
    ADD CONSTRAINT tours_pkey PRIMARY KEY (id);


--
-- Name: neighborhood_descriptions unique_city_neighborhood; Type: CONSTRAINT; Schema: public; Owner: voyana
--

ALTER TABLE ONLY public.neighborhood_descriptions
    ADD CONSTRAINT unique_city_neighborhood UNIQUE (city, neighborhood);


--
-- Name: users users_apple_id_key; Type: CONSTRAINT; Schema: public; Owner: voyana
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_apple_id_key UNIQUE (apple_id);


--
-- Name: users users_google_id_key; Type: CONSTRAINT; Schema: public; Owner: voyana
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_google_id_key UNIQUE (google_id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: voyana
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: ix_api_keys_key; Type: INDEX; Schema: public; Owner: voyana
--

CREATE UNIQUE INDEX ix_api_keys_key ON public.api_keys USING btree (key);


--
-- Name: ix_audio_cache_text_hash; Type: INDEX; Schema: public; Owner: voyana
--

CREATE UNIQUE INDEX ix_audio_cache_text_hash ON public.audio_cache USING btree (text_hash);


--
-- Name: ix_password_reset_tokens_token; Type: INDEX; Schema: public; Owner: voyana
--

CREATE UNIQUE INDEX ix_password_reset_tokens_token ON public.password_reset_tokens USING btree (token);


--
-- Name: ix_sites_place_id; Type: INDEX; Schema: public; Owner: voyana
--

CREATE INDEX ix_sites_place_id ON public.sites USING btree (place_id);


--
-- Name: ix_users_email; Type: INDEX; Schema: public; Owner: voyana
--

CREATE UNIQUE INDEX ix_users_email ON public.users USING btree (email);


--
-- Name: api_keys api_keys_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: voyana
--

ALTER TABLE ONLY public.api_keys
    ADD CONSTRAINT api_keys_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: feedback feedback_reviewed_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: voyana
--

ALTER TABLE ONLY public.feedback
    ADD CONSTRAINT feedback_reviewed_by_fkey FOREIGN KEY (reviewed_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: feedback feedback_site_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: voyana
--

ALTER TABLE ONLY public.feedback
    ADD CONSTRAINT feedback_site_id_fkey FOREIGN KEY (site_id) REFERENCES public.sites(id) ON DELETE CASCADE;


--
-- Name: feedback feedback_tour_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: voyana
--

ALTER TABLE ONLY public.feedback
    ADD CONSTRAINT feedback_tour_id_fkey FOREIGN KEY (tour_id) REFERENCES public.tours(id) ON DELETE CASCADE;


--
-- Name: feedback feedback_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: voyana
--

ALTER TABLE ONLY public.feedback
    ADD CONSTRAINT feedback_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: password_reset_tokens password_reset_tokens_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: voyana
--

ALTER TABLE ONLY public.password_reset_tokens
    ADD CONSTRAINT password_reset_tokens_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: tour_sites tour_sites_site_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: voyana
--

ALTER TABLE ONLY public.tour_sites
    ADD CONSTRAINT tour_sites_site_id_fkey FOREIGN KEY (site_id) REFERENCES public.sites(id) ON DELETE CASCADE;


--
-- Name: tour_sites tour_sites_tour_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: voyana
--

ALTER TABLE ONLY public.tour_sites
    ADD CONSTRAINT tour_sites_tour_id_fkey FOREIGN KEY (tour_id) REFERENCES public.tours(id) ON DELETE CASCADE;


--
-- Name: tours tours_owner_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: voyana
--

ALTER TABLE ONLY public.tours
    ADD CONSTRAINT tours_owner_id_fkey FOREIGN KEY (owner_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict GJ7bbCCsyYI2L45dKZgkhyM2UlmLa3j0jPYCNjMn0ZooWFgy2VMgJ21at3NBaJo

