CREATE TABLE download_stats
(
    os text,
    release text,
    "name" text NOT NULL,
    pg_version decimal,
    version text NOT NULL,
    "date" date NOT NULL,
    downloads integer NOT NULL
);
CREATE INDEX ON download_stats (date);

CREATE TABLE download_levels
(
    os text,
    release text,
    "name" text NOT NULL,
    pg_version decimal,
    version text NOT NULL,
    "date" date NOT NULL,
    total_downloads integer NOT NULL
);
CREATE INDEX ON download_levels (date);
