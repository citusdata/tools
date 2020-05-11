#!/usr/bin/perl
use lib '/usr/local/bin';
use common_functions;

$NEW_VERSION = $ARGV[0];
$OLD_VERSION = $ARGV[1];

my $github_token = get_and_verify_token();

# Necessary to create unique branch
$curTime = time();

`git checkout master`;
`git checkout -b master-$NEW_VERSION-$curTime`;

$new_release_minor_version = substr($NEW_VERSION, 0, 3);
$old_release_minor_version = substr($OLD_VERSION, 0, 3);
$old_release_minor_version_escape_dot = $old_release_minor_version;
$old_release_minor_version_escape_dot =~ s/\./\\./g;

# Update multi_machine_aws.rst
`sed -i 's/$OLD_VERSION/$NEW_VERSION/g' ./installation/multi_machine_aws.rst`;

# Commit changes to github
`git commit -a -m "Bump Citus version to $NEW_VERSION"`;
`git push origin master-$NEW_VERSION-$curTime`;

# Open a PR to the master
`curl -g -H "Accept: application/vnd.github.v3.full+json" -X POST --user "$github_token:x-oauth-basic" -d '{\"title\":\"Bump Citus to $NEW_VERSION\", \"base\":\"master\", \"head\":\"master-$NEW_VERSION-$curTime\" \"draft\":True}' https://api.github.com/repos/citusdata/citus_docs/pulls`;
