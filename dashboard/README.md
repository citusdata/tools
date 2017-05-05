# Dashboard

These scripts are intended for use within daily cron scripts (presently running on our EC2 instance tagged _KPI Updater_) to keep a KPI (key performance indicators) database up to date (living on Heroku PostgreSQL).

## Getting Started

You probably shouldn't need to do anything with this, but if anything changes, log into that box, use `curl` or `wget` to get the latest version of the `citusdata/tools` repository, then `sudo make -C dashboard install`. Check the latest cron configuration using `crontab -l`, and see whether any cron failures have sent mail using `mail`.

## What's Included

All non `update_*` scripts emit (to standard out) CSV files suitable for loading into PostgreSQL tables defined in `schema.dll`. Most have pretty good usage messages, so check those out if needed.

`pkg.jq` is a huge mishmash of `jq` helper normalization functions for massaging API data into the right state before ingest.

### `docker_pulls`

Emits a single row containing the number of all-time Docker Hub pulls for a given Docker image. Loads into the `download_levels` table.

### `github_clones`

Emits the previous two weeks (all that the API exposes) of download stats for a given GitHub project, optionally starting at a specified date. Loads into the `download_stats` table.

### `github_clones`

Emits all-time download stats for every version of a specified Homebrew package, optionally starting at a specified date. Loads into the `download_stats` table.

### `packagecloud_downloads`

Emits all-time download stats for every version of every package in a specified packagecloud repository, optionally starting at a specified date. Loads into the `download_stats` table.

### `rubygem_installs`

Emits one row containing the all-time downloads for each version of a specified Ruby gem. Loads into the `download_levels` table.

### `travis_builds`

Emits rows representing the successful build history of a specified Travis CI project. Used to deduct "internal" GitHub clones and HLL pulls. Loads into the `travis_builds` table.

### `update_builds`

Determines whether the `travis_builds` table needs to be updated, and what date was last logged. Runs the `travis_builds` script and loads it into the KPI database.

### `update_stats`

Determines whether the `download_stats` and `download_levels` tables need to be updated, and what dates were last logged in each. Runs _all_ other scripts and loads them into KPI database.
