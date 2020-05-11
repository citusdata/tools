#!/usr/bin/perl
use lib '/usr/local/bin';
use common_functions;
use JSON;

$PROJECT = $ARGV[0];
$NEW_VERSION = $ARGV[1];
$EARLIEST_PR_DATE = $ARGV[2];

# Cherry-pick commit using commit end-points
sub cherry_pick_commits {
    @commit_urls = @_;

    my $minor_version = substr($NEW_VERSION, 0, 3);
    `git checkout release-$minor_version`;

    foreach my $commit_url (@commit_urls) {
        my $current_commits_text = `curl -H "Accept: application/vnd.github.v3.full+json" -X GET --user "$github_token:x-oauth-basic" '$commit_url' 2> /dev/null`;
        my @current_commits = @{decode_json($current_commits_text)};

        foreach my $current_commit (@current_commits) {
            %current_commit_hash = %$current_commit;

            # Cherry pick commits
            my $current_sha_code = $current_commit_hash{'sha'};
            `git cherry-pick $current_sha_code`;
        }
    }
}

# Necessary to create unique branch
$curTime = time();

my $github_token = get_and_verify_token();
my $minor_version = substr($NEW_VERSION, 0, 3);

# We will update the new major-minor version
$minor_version_escape_dot = $minor_version;
$minor_version_escape_dot =~ s/\./\\./g;

# Means it is a major release
if ( $NEW_VERSION =~ /.*\.0$/ ) {

    my $UPCOMING_VERSION = substr($NEW_VERSION, 0, 2) . (substr($NEW_VERSION, 2, 3) + 1) . "devel";
    my $upcoming_minor_version = substr($UPCOMING_VERSION, 0, 3);
    my $current_version_escape_dot = $minor_version_escape_dot . "devel";

    # Checkout the master branch of the repo
    `git checkout master`;

    # Now checkout ot the new release's branch
    `git checkout -b release-$minor_version`;

    # Update the version on the configuration file
    `sed -i 's/$current_version_escape_dot/$NEW_VERSION/g' configure.in`;

    # Run autoconf to generate new configure file
    `autoconf -f`;

    # Update expected version on multi_extension test
    `sed -i 's/$current_version_escape_dot/$NEW_VERSION/g' ./src/test/regress/expected/multi_extension.out`;

    # Push the branch of new release
    `git commit -a -m "Bump Citus version to $NEW_VERSION"`;

    `git push origin release-$minor_version`;

    print( "New version's branch has been created ..." . "\n" );

    # Now the new branch for major or minor release is pushed,
    # it is time to update the master branch
    `git checkout master`;
    `git checkout -b master-update-version-$curTime`;

    # Update the version on the configuration file
    `sed -i 's/$current_version_escape_dot/$UPCOMING_VERSION/g' configure.in`;

    # Update the version on the config.py file (for upgrade tests)
    `sed -i 's/$minor_version_escape_dot/$upcoming_minor_version/g' ./src/test/regress/upgrade/config.py`;

    # Run autoconf to generate new configure file
    `autoconf -f`;

    # Update expected version on multi_extension test
    `sed -i 's/$current_version_escape_dot/$UPCOMING_VERSION/g' ./src/test/regress/expected/multi_extension.out`;

    # We also need to update two different lines on the multi_extension.out
    `sed -i 's/Loaded library requires $minor_version/Loaded library requires $upcoming_minor_version/g' ./src/test/regress/expected/multi_extension.out`;

    my $current_schema_version = `awk -F' += +' -v property=default_version '\$1 ~ property {print \$2}' "./src/backend/distributed/citus.control"`;
    # trim output of awk (remove quotes and newline)
    $current_schema_version = substr($current_schema_version, 1, -2);

    # We need to append new lines to test files for migrating to new schema version
    `sed -i "/^ALTER EXTENSION citus UPDATE TO '$current_schema_version';/a ALTER EXTENSION citus UPDATE TO '$upcoming_minor_version-1';" ./src/test/regress/sql/multi_extension.sql`;
    `sed -i "/^ALTER EXTENSION citus UPDATE TO '$current_schema_version';/a ALTER EXTENSION citus UPDATE TO '$upcoming_minor_version-1';" ./src/test/regress/expected/multi_extension.out`;

    # Add a new sql file
    open( NEW_SQL_FILE, ">./src/backend/distributed/citus--$current_schema_version--$upcoming_minor_version-1.sql") || die "New SQL file couldn't created";
    print NEW_SQL_FILE "/* citus--$current_schema_version--$upcoming_minor_version-1 */"
      . "\n\n"
      . "-- bump version to $upcoming_minor_version-1" . "\n\n";
    close(NEW_SQL_FILE);

    # Update citus.control file
    `sed -i 's/$current_schema_version/$upcoming_minor_version-1/g' ./src/backend/distributed/citus.control`;

    # Push the changes to the master branch
    `git add ./src/backend/distributed/citus--$current_schema_version--$upcoming_minor_version-1.sql`;
    `git commit -a -m "Bump $PROJECT version to $UPCOMING_VERSION"`;
    `git push origin master-update-version-$curTime`;
    `curl -g -H "Accept: application/vnd.github.v3.full+json" -X POST --user "$github_token:x-oauth-basic" -d '{\"title\":\"Bump Citus to $UPCOMING_VERSION\", \"base\":\"master\", \"head\":\"master-update-version-$curTime" \"draft\":True}' https://api.github.com/repos/citusdata/$PROJECT/pulls`;
}

# means it is a point version
else {
    # Checkout release's branch
    `git checkout release-$minor_version`;

    # Create empty array to hold commit urls
    @picked_commits = ();

    my @sorted_pr_urls = get_sorted_prs($EARLIEST_PR_DATE, $PROJECT );

    foreach my $pr_url (@sorted_pr_urls) {
        my $pr_text = `curl -H "Accept: application/vnd.github.v3.full+json" -X GET --user "$github_token:x-oauth-basic" '$pr_url' 2> /dev/null`;
        my %pr_hash = %{decode_json($pr_text)};

        my $issue_url = $pr_hash{'issue_url'};
        my $issue_text = `curl -H "Accept: application/vnd.github.v3.full+json" -X GET --user "$github_token:x-oauth-basic" '$issue_url' 2> /dev/null`;
        my %issue_hash = %{decode_json($issue_text) };

        @labels = @{$issue_hash{'labels'}};
        if (has_backport_label(\@labels)) {
            unshift(@picked_commits, $pr_hash{'commits_url'});
        }
    }

    cherry_pick_commits(@picked_commits);

    $new_point_version = substr($NEW_VERSION, -1);
    $current_point_version = $new_point_version - "1";
    $current_version_escape_dot = $minor_version . "." . $current_point_version;
    $current_version_escape_dot =~ s/[^0-9]/\\./g;

    # Update configuration file
    `sed -i 's/$current_version_escape_dot/$NEW_VERSION/g' configure.in`;

    # Run autoconf to generate new configure file
    `autoconf`;

    # Update multi_extension file
    `sed -i 's/$current_version_escape_dot/$NEW_VERSION/g' ./src/test/regress/expected/multi_extension.out`;

    # Commit changes and push a new branch to pass travis tests
    `git commit -a -m "Bump version to $NEW_VERSION"`;
    `git checkout -b release-$minor_version-push-$curTime`;
    `git push origin release-$minor_version-push-$curTime`;
}
