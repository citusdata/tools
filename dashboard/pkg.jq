# removes debuginfo packages from RPM listings
# Input: packagecloud PackageFragment objects
def stripdebuginfo:
    map(
        select(
            .name |
            endswith("debuginfo") |
            not
        )
    )
;

# extracts a URL for requesting download stats from start_date to yesterday
# Input: a packagecloud PackageDetails object
def extracturl(start_date):
    .downloads_series_url +
    "?start_date=" + (
        start_date // ( # use provided start date or ask since package creation
          .created_at |
          split("T")[0] |
          gsub("-";"") + "Z"
        )
    ) + "&end_date=" + ((now - 86400) | strftime("%Y%m%dZ")) # yesterday
;

# removes download stats with zero downloads
# Input: a packagecloud SeriesValue object
def stripzeros:
    .value |
    to_entries |
    map(select(.value > 0))
;

# maps a package name back to project name and PG version
# Input: name, an RPM or Debian package name
def pkgnameandpgversion(name):
    if (name | startswith("postgresql-")) then
        name | split("-") as $parts |
        [
            ($parts[2:] | join("-") | # name portion (after PG version)
             sub("-\\d\\.\\d$"; "")), # replace fancy version portion
            $parts[1]                 # PG version portion
        ]
    else
        name | split("_") as $parts |
        [
            ($parts[:-1] | join("_") |              # name portion (before PG version)
             sub("\\d{2}$"; "")      |              # replace fancy version portion
             sub("^pg_cron$"; "pgcron")),           # normalize pg_cron to pgcron
            $parts[-1][:2] | sub("^9"; "9.")        # PG version portion
        ]
    end
;

# maps version/release back to git tag that produced them
# Input: r, a packagecloud PackageDetails object
def gittag(r):
    r.version | rtrimstr(".citus") as $version |
    if ($version | contains("~")) then
        $version | sub("~"; "-")
    elif (r.release // "" | startswith("rc")) then # hack for bad deb version 1.0.0-rc.1
        $version + "-" + r.release
    elif (r.release // "" | contains("rc")) then
        $version + "-" +
        (r.release // "" | split(".") | .[2] + "." + .[3])
    else
        $version
    end
;

# normalizes packagecloud data into download_stats schema
# Input: a packagecloud SeriesValue; r, a packagecloud PackageDetails object
def makerow(r):
    [
        (r.distro_version | split("/")),
        pkgnameandpgversion(r.name),
        gittag(r),
        # this regex converts from YYYYMMDDZ to YYYY-MM-DD
        (.key | sub("^(?<y>\\d{4})   # year
                      (?<m>\\d{2})   # month
                      (?<d>\\d{2})Z$ # day";
                    "\(.y)-\(.m)-\(.d)"; "ix")),
        .value
    ] |
    flatten
;

# discards time series data before since or after yesterday
# Input: a GitHub traffic/clones response; since, a start date
def filterdate(since):
  ((now - 86400) | todateiso8601) as $yesterday |
  .timestamp as $ts |
  select($ts >= since and $ts <= $yesterday)
;

# normalizes GitHub traffic/clone data into download_stats schema
# Input: a GitHub traffic/clones response; name, a repo name
def makeclonerows(name):
    select(.count > 0) |
    [
        null,
        null,
        name,
        null,
        "HEAD",
        ( .timestamp | split("T")[0]),
        .count
    ]
;

# remove Travis builds not yet complete or not after 'since'
# Input: an array of Travis CI build objects
def filterbuilds(since):
  select((.state | in({passed: null,
                      failed: null,
                      errored: null,
                      canceled: null})) and
         ((.number | tonumber) > since)
  )
;

# transform Travis builds into CSV rows
# Input: a stream of Travis CI build objects
def maketravisrows(name):
  [
    name,
    (.number | tonumber),
    (.started_at | split("T")[0]),
    (.job_ids | length)
  ]
;

# normalizes a RubyGems gem version listing into download_stats schema
# Input: a RubyGems gem version listing; name, a gem name
def makegemrows(name):
  ((now - 86400) | strftime("%Y-%m-%d")) as $today |
  map(
    [
        "ruby",
        null,
        name,
        null,
        .number,
        $today,
        .downloads_count
    ]
  )
;

# normalizes Docker Hub image detail into download_stats schema
# Input: a Docker Hub image detail response; name, an image name
def makepullrow(name):
    [
        "Docker",
        null,
        name,
        null,
        "all",
        ((now - 86400) | strftime("%Y-%m-%d")),
        .pull_count
    ]
;

# converts Homebrew-sourced dates into PostgreSQL-formatted ones
# Input: d, a date field from a Homebrew response
def brewdate(d):
    d | tonumber / 1000 | todateiso8601 | split("T")[0]
;

# normalizes Homebrew download data into download_stats schema
# Input: a Bintray packageStatistics response; name, a formula name
def makebrewrows(name):
  reduce .[] as $item ( # normalize rebuild versions into single version
    {}; # output is an object
    ($item | .version | split("_")[0]) as $base_version | # 6.0.0_1 -> 6.0.0
    ($item | .series) as $series |
    .[$base_version] += $series # concatenate e.g. all 6.0.0 series together
  ) | map_values( # operate on the values of the version -> series object
    reduce .[] as $datum ( # for given version, sum downloads on same date
      {}; # output is an object
      ($datum | .[0]) as $date |
      ($datum | .[1]) as $count |
      .[$date] += $count # transform to object, summing same dates
    ) | to_entries | map([.key, .value]) # transform entries to tuples
  ) | to_entries | map( # now have object mapping version -> (date, count)
    .key as $version | # extract key as version name
    .value | map(select(.[1] > 0)) | # discard entries with no downloads
    map([ # ready to map into CSV rows
      "macOS",
      null,
      name,
      null,
      $version,
      brewdate(.[0]),
      .[1]])
    ) | flatten(1)
;
