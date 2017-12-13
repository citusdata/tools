#!/usr/bin/perl
use lib '/usr/local/bin';
use common_functions;

$NEW_VERSION = $ARGV[0];
$OLD_VERSION = $ARGV[1];

my $github_token = get_and_verify_token();

$old_version_escape_dot = $OLD_VERSION;
$old_version_escape_dot =~ s/\./\\./g;
$old_minor_version = substr($OLD_VERSION, 0, 3);
$new_minor_version = substr($NEW_VERSION, 0, 3);
$new_point_version = substr($NEW_VERSION, -1);

# Necessary to create unique branch
$curTime = time();

# Move to code directory
`git checkout pgxn-citus`;
`git checkout -b pgxn-citus-push-$curTime`;

# Update pkgvars
`sed -i 's/pkglatest=[[:digit:]]*.[[:digit:]]*.[[:digit:]]*/pkglatest=$NEW_VERSION/g' pkgvars`;

# Update META.json file
`sed -i 's/$old_version_escape_dot/$NEW_VERSION/g' META.json`;
`sed -i 's/$old_minor_version-[[:digit:]]/$new_minor_version-$new_point_version/g' META.json`;

# Commit changes to github
`git commit -a -m "Bump Citus to $NEW_VERSION"`;
`git push origin pgxn-citus-push-$curTime`;

# Open a PR to the master
`curl -g -H "Accept: application/vnd.github.v3.full+json" -X POST --user "$github_token:x-oauth-basic" -d '{\"title\":\"Bump Citus to $NEW_VERSION\", \"base\":\"pgxn-citus\", \"head\":\"pgxn-citus-push-$curTime\"}' https://api.github.com/repos/citusdata/packaging/pulls`;
