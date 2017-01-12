def stripdebuginfo:
    map(
        select(
            .name |
            endswith("debuginfo") |
            not
        )
    )
;

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

def stripzeros:
    .value |
    to_entries |
    map(select(.value > 0))
;

def pkgnameandpgversion(name):
    if (name | startswith("postgresql-")) then
        name | split("-") as $parts |
        [
            ($parts[2:] | join("-")), # name portion (after PG version)
            $parts[1]                 # PG version portion
        ]
    else
        name | split("_") as $parts |
        [
            ($parts[:-1] | join("_")),              # name portion (before PG version)
            $parts[-1][0:1] + "." + $parts[-1][1:2] # PG version portion
        ]
    end
;

def gittag(r):
    r.version | rtrimstr(".citus") as $version |
    if ($version | contains("~")) then
        $version | sub("~"; "-")
    elif (r.release | contains("rc")) then
        $version + "-" +
        (r.release | split(".") | .[2] + "." + .[3])
    else
        $version
    end
;

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

def filterdate(since):
  ((now - 86400) | todateiso8601) as $yesterday |
  .timestamp as $ts |
  select($ts >= since and $ts <= $yesterday)
;

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

def brewdate(d):
    d | tonumber / 1000 | todateiso8601 | split("T")[0]
;

def makebrewrows(name):
    map(
        .version as $version |
        .series | map(select(.[1] > 0)) |
        map([
          "macOS",
          null,
          name,
          null,
          $version,
          brewdate(.[0]),
          .[1]])
    ) | flatten(1)
;