BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 2e948ab7bd04

CREATE TYPE transaction_type AS ENUM ('income', 'expense');

CREATE TABLE transactions (
    id SERIAL NOT NULL, 
    amount NUMERIC(10, 2) NOT NULL, 
    type transaction_type NOT NULL, 
    category VARCHAR(50), 
    description VARCHAR(200), 
    party VARCHAR(100), 
    date TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id)
);

INSERT INTO alembic_version (version_num) VALUES ('2e948ab7bd04') RETURNING alembic_version.version_num;

COMMIT;

