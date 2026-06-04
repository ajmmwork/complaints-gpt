-- Run this as the admin Postgres user AFTER your tables are created.
-- Replace the database name, role name, and password before running.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_roles
        WHERE rolname = 'agent_user'
    ) THEN
        CREATE ROLE agent_role
        LOGIN
        PASSWORD 'replace_with_secure_password'
        NOSUPERUSER
        NOCREATEDB
        NOCREATEROLE
        NOREPLICATION;
    END IF;
END
$$;

ALTER ROLE agent_role
    NOSUPERUSER
    NOCREATEDB
    NOCREATEROLE
    NOREPLICATION;

GRANT CONNECT ON DATABASE "complaints-db" TO agent_role;

REVOKE ALL ON SCHEMA public FROM agent_role;
GRANT USAGE ON SCHEMA public TO agent_role;
REVOKE CREATE ON SCHEMA public FROM agent_role;

REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM agent_role;
REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public FROM agent_role;
REVOKE ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public FROM agent_role;

GRANT SELECT, INSERT, UPDATE ON TABLE jobs TO agent_role;
GRANT SELECT, INSERT ON TABLE complaints TO agent_role;
GRANT SELECT, INSERT ON TABLE complaints_narratives TO agent_role;

GRANT SELECT, INSERT, UPDATE ON TABLE exploratory_jobs TO agent_role;
GRANT SELECT, INSERT ON TABLE companies TO agent_role;

GRANT SELECT, INSERT ON TABLE issues TO agent_role;
GRANT SELECT, INSERT ON TABLE products TO agent_role;

GRANT USAGE, SELECT ON SEQUENCE jobs_job_id_seq TO agent_role;
GRANT USAGE, SELECT ON SEQUENCE exploratory_jobs_job_id_seq TO agent_role;
GRANT USAGE, SELECT ON SEQUENCE companies_id_seq TO agent_role;
GRANT USAGE, SELECT ON SEQUENCE issues_id_seq TO agent_role;
GRANT USAGE, SELECT ON SEQUENCE products_id_seq TO agent_role;

REVOKE DELETE ON TABLE jobs FROM agent_role;
REVOKE DELETE ON TABLE complaints FROM agent_role;
REVOKE DELETE ON TABLE complaints_narratives FROM agent_role;
REVOKE DELETE ON TABLE exploratory_jobs FROM agent_role;
REVOKE DELETE ON TABLE companies FROM agent_role;
REVOKE DELETE ON TABLE issues FROM agent_role;
REVOKE DELETE ON TABLE products FROM agent_role;

REVOKE TRUNCATE ON TABLE jobs FROM agent_role;
REVOKE TRUNCATE ON TABLE complaints FROM agent_role;
REVOKE TRUNCATE ON TABLE complaints_narratives FROM agent_role;
REVOKE TRUNCATE ON TABLE exploratory_jobs FROM agent_role;
REVOKE TRUNCATE ON TABLE companies FROM agent_role;
REVOKE TRUNCATE ON TABLE issues FROM agent_role;
REVOKE TRUNCATE ON TABLE products FROM agent_role;

REVOKE REFERENCES ON TABLE jobs FROM agent_role;
REVOKE REFERENCES ON TABLE complaints FROM agent_role;
REVOKE REFERENCES ON TABLE complaints_narratives FROM agent_role;
REVOKE REFERENCES ON TABLE exploratory_jobs FROM agent_role;
REVOKE REFERENCES ON TABLE companies FROM agent_role;
REVOKE REFERENCES ON TABLE issues FROM agent_role;
REVOKE REFERENCES ON TABLE products FROM agent_role;

REVOKE TRIGGER ON TABLE jobs FROM agent_role;
REVOKE TRIGGER ON TABLE complaints FROM agent_role;
REVOKE TRIGGER ON TABLE complaints_narratives FROM agent_role;
REVOKE TRIGGER ON TABLE exploratory_jobs FROM agent_role;
REVOKE TRIGGER ON TABLE companies FROM agent_role;
REVOKE TRIGGER ON TABLE issues FROM agent_role;
REVOKE TRIGGER ON TABLE products FROM agent_role;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
REVOKE ALL ON TABLES FROM agent_role;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
REVOKE ALL ON SEQUENCES FROM agent_role;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
REVOKE ALL ON FUNCTIONS FROM agent_role;