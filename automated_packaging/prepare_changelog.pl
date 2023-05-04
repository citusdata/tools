#!/usr/bin/perl
use lib '/usr/local/bin';
use common_functions;
use JSON;
use POSIX qw(strftime);

$PROJECT = $ARGV[0];
$NEW_VERSION = $ARGV[1];
$EARLIEST_PR_DATE = $ARGV[2];

# Necessary to write log date and create a unique branch
@month_names = qw(January February March April May June July August September October November December);
( $sec, $min, $hour, $mday, $mon, $year, $wday, $yday, $isdst ) = localtime(time);
$year += 1900;

# Necessary to create unique branch
$curTime = "$year-$mon-$mday-$hour-$min-$sec";

sub add_changelog_header() {

    # Update the changelog file
    open( CHANGELOG_FILE, ">CHANGELOG.md" ) || die "Can't open the Changelog file !";
    print CHANGELOG_FILE "### $PROJECT v$NEW_VERSION ($month_names[$mon] $mday, $year) ###\n\n";
    close(CHANGELOG_FILE);
}

$github_token = get_and_verify_token();

# Checkout the main branch
`git checkout main`;

# Now create a new branch based on main
`git checkout -b $PROJECT-$NEW_VERSION-changelog-$curTime`;

# Read the current changelog
open( CHANGELOG_FILE, "<CHANGELOG.md" ) || die "Changelog file not found";
my @changelog_current_lines = <CHANGELOG_FILE>;
close(CHANGELOG_FILE);

# Check whether it is a point release
$is_point_release = $NEW_VERSION !~ /.*\.0$/;
@changelog_addings = create_release_changelog( $EARLIEST_PR_DATE, $PROJECT, $is_point_release );

add_changelog_header();
open( CHANGELOG_FILE, "+>>CHANGELOG.md" ) || die "Can't open the Changelog file !";
print CHANGELOG_FILE @changelog_addings;
print CHANGELOG_FILE @changelog_current_lines;
close(CHANGELOG_FILE);

# Commit and push the changes, then open a PR
`git commit -a -m "Add changelog entry for $NEW_VERSION"`;
`git push origin $PROJECT-$NEW_VERSION-changelog-$curTime`;
`curl -g -H "Accept: application/vnd.github.v3.full+json" -X POST --user "$github_token:x-oauth-basic" -d '{\"title\":\"Bump $PROJECT to $NEW_VERSION\", \"base\":\"main\", \"head\":\"$PROJECT-$NEW_VERSION-changelog-$curTime\"}' https://api.github.com/repos/citusdata/$PROJECT/pulls`;
