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
CREATE INDEX ON download_stats ("date");

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
CREATE INDEX ON download_levels ("date");

CREATE TABLE travis_builds
(
	"name" text NOT NULL,
	"number" integer NOT NULL,
	"date" date NOT NULL,
	job_count integer NOT NULL
);
CREATE INDEX ON travis_builds ("date");

CREATE VIEW job_stats AS
SELECT "date", SUM(job_count) AS jobs
FROM travis_builds GROUP BY 1 ORDER BY 1;
