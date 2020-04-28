#!/usr/bin/perl
use lib '/usr/local/bin';
use common_functions;

$VERSION = $ARGV[0];
$POSTGERSQL_VERSION = $ARGV[1];
$num_args = $#ARGV + 1;

my $minor_version = substr( $VERSION, 0, 3 );
my $github_token = get_and_verify_token();

# Necessary to write log date
my @abbr_mon = qw(January February March April May June July August September October November December);
my ( $sec, $min, $hour, $mday, $mon, $year, $wday, $yday, $isdst ) = localtime(time);
$year += 1900;

# Necessary to create unique branch
$curTime = time();

# Checkout to the release's branch
`git checkout develop`;
`git checkout -b release-$VERSION-$curTime`;

# That means we want to update postgres version
if ( $num_args == 2 ) {
    `sed -i 's/postgres:[[:digit:]]*.[[:digit:]]*/postgres:$POSTGERSQL_VERSION/g' Dockerfile`;
}

# Update citus version on Dockerfile
`sed -i 's/VERSION=[[:digit:]]*.[[:digit:]]*.[[:digit:]]*/VERSION=$VERSION/g' Dockerfile`;
`sed -i 's/PG_MAJOR-citus-[[:digit:]]*.[[:digit:]]*/PG_MAJOR-citus-$minor_version/g' Dockerfile`;

# Update citus version on alpine Dockerfile
`sed -i 's/VERSION=[[:digit:]]*.[[:digit:]]*.[[:digit:]]*/VERSION=$VERSION/g' Dockerfile-alpine`;
`sed -i 's/PG_MAJOR-citus-[[:digit:]]*.[[:digit:]]*/PG_MAJOR-citus-$minor_version/g' Dockerfile-alpine`;

# Update citus version on docker-compose
`sed -i 's/citus:[[:digit:]]*.[[:digit:]]*.[[:digit:]]*/citus:$VERSION/g' docker-compose.yml`;

# Update travis.yml file
`sed -i 's/citus:[[:digit:]]*.[[:digit:]]*.[[:digit:]]*/citus:$VERSION/g' .travis.yml`;

# Get current changelog entries
open( CHANGELOG, "<CHANGELOG.md" ) || die "File not found";
my @current_lines = <CHANGELOG>;
close(CHANGELOG);

# Update the changelog file
open( CHANGELOG, ">CHANGELOG.md" ) || die "File not found";
print CHANGELOG "### citus-docker v$VERSION.docker ($abbr_mon[$mon] $mday, $year) ###\n\n";
print CHANGELOG "* Bump Citus version to $VERSION\n\n";

if ( $num_args == 2 ) {
    print CHANGELOG "* Bump PostgreSQL version to $POSTGRESQL_VERSION\n\n";
}

print CHANGELOG @current_lines;
close(CHANGELOG);

# Push the branch and open a PR against master
`git commit -a -m "Bump to version $VERSION"`;
`git push origin release-$VERSION-$curTime`;
`curl -g -H "Accept: application/vnd.github.v3.full+json" -X POST --user "$github_token:x-oauth-basic" -d '{\"title\":\"Bump docker to $VERSION\", \"base\":\"master\", \"head\":\"release-$VERSION-$curTime\"}' https://api.github.com/repos/citusdata/docker/pulls`;
