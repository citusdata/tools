#!/usr/bin/perl
use lib '/usr/local/bin';
use common_functions;

$DISTRO_VERSION = $ARGV[0];
$PROJECT = $ARGV[1];
$VERSION = $ARGV[2];

# Name of the repo is represented differently on logs and repos
my $github_repo_name = "citus";
my $log_repo_name = "Citus";
my $version_suffix = ".citus";
if ( $PROJECT eq "enterprise" ) {
    $github_repo_name = "citus-enterprise";
    $log_repo_name = "Citus Enterprise";
}
my $package_name = $github_repo_name;
if ( $PROJECT eq "pgautofailover" ) {
    $github_repo_name = "pg_auto_failover";
    $package_name = "pg-auto-failover";
    $log_repo_name = "pg_auto_failover";
    $version_suffix = "";
}
if ( $PROJECT eq "pgautofailover-enterprise" ) {
    $github_repo_name = "citus-ha";
    $package_name = "pg-auto-failover-enterprise";
    $log_repo_name = "pg_auto_failover enterprise";
    $version_suffix = "";
}

my $github_token = get_and_verify_token();

my $microsoft_email = get_microsoft_email();
my $git_name = get_git_name();

# Debian branch has it's own changelog, we can get them through the CHANGELOG file of the code repo
sub get_changelog_for_debian {

    # Update project spec file
    @changelog_file = `curl --user "$github_token:x-oauth-basic" -H "Accept: application/vnd.github.v3.raw" -X GET 'https://api.github.com/repos/citusdata/$github_repo_name/contents/CHANGELOG.md?ref=v$VERSION' 2> /dev/null`;

    $first_version_has_seen = 0;
    my @changelog_items;
    foreach $line (@changelog_file) {
        if ( $line =~ /^#/ ) {
            if ( $first_version_has_seen == 1 ) {
                last;
            }

            $first_version_has_seen += 1;
        }
        elsif ( $line =~ /^\*/ ) {
            $line =~ tr/\`//d;
            push( @changelog_items, '  ' . $line );
        }
        else {
            push( @changelog_items, $line );
        }
    }

    return @changelog_items;
}

# Necessary to write log date for both distros and create unique branch
my @abbr_mon = qw(Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec);
my @abbr_day = qw(Sun Mon Tue Wed Thu Fri Sat);
my ( $sec, $min, $hour, $mday, $mon, $year, $wday, $yday, $isdst ) =
  localtime(time);
$year += 1900;

# Necessary to create unique branch
$curTime = time();
my $main_branch = "$DISTRO_VERSION-$PROJECT";
my $pr_branch = "$DISTRO_VERSION-$PROJECT-$VERSION-push-$curTime";

# Checkout the distro's branch
`git checkout $main_branch`;
# Update distro's branch
`git pull origin $main_branch`;

# Create a new branch based on the distro's branch
`git checkout -b $pr_branch`;

# Update pkgvars
`sed -i 's/^pkglatest.*/pkglatest=$VERSION$version_suffix-1/g' pkgvars`;

# Based on the repo, update the package related variables
if ( $DISTRO_VERSION eq "redhat" || $DISTRO_VERSION eq "microsoft" || $DISTRO_VERSION eq "all") {
    `sed -i 's|^Version:.*|Version:	$VERSION$version_suffix|g' $package_name.spec`;
    `sed -i 's|^Source0:.*|Source0:	https:\/\/github.com\/citusdata\/$package_name\/archive\/v$VERSION.tar.gz|g' $package_name.spec`;
    `sed -i 's|^%changelog|%changelog\\n* $abbr_day[$wday] $abbr_mon[$mon] $mday $year - $git_name <$microsoft_email> $VERSION$version_suffix-1\\n- Official $VERSION release of $log_repo_name\\n|g' $package_name.spec`;
}
if ( $DISTRO_VERSION eq "debian" || $DISTRO_VERSION eq "microsoft" || $DISTRO_VERSION eq "all") {
    open( DEB_CLOG_FILE, "<./debian/changelog" ) || die "Debian changelog file not found";
    my @lines = <DEB_CLOG_FILE>;
    close(DEB_CLOG_FILE);

    # Change hour and get changelog (TODO: may update it !)
    $print_hour = $hour - 3;
    if ($PROJECT eq 'citus' || $PROJECT eq 'enterprise') {
        @changelog_print = get_changelog_for_debian();
    }


    # Update the changelog file of the debian branch
    open( DEB_CLOG_FILE, ">./debian/changelog" ) || die "Debian changelog file not found";
    print DEB_CLOG_FILE "$package_name ($VERSION$version_suffix-1) stable; urgency=low\n";
    if ($PROJECT eq 'citus' || $PROJECT eq 'enterprise') {
        print DEB_CLOG_FILE @changelog_print;
    }
    else
    {
        print DEB_CLOG_FILE "\n  * Official $VERSION release of $log_repo_name\n\n";
    }
    print DEB_CLOG_FILE " -- $git_name <$microsoft_email>  $abbr_day[$wday], $mday $abbr_mon[$mon] $year $print_hour:$min:$sec +0000\n\n";
    print DEB_CLOG_FILE @lines;
    close(DEB_CLOG_FILE);
}


my $commit_message_distro_version = "$DISTRO_VERSION ";
if ($DISTRO_VERSION eq "all") {
    $commit_message_distro_version = "";
}
# Commit, push changes and open a pull request
my $commit_message = "Bump $commit_message_distro_version$log_repo_name version to $VERSION";
`git commit -a -m "$commit_message"`;
`git push origin $pr_branch`;
`curl -g -H "Accept: application/vnd.github.v3.full+json" -X POST --user "$github_token:x-oauth-basic" -d '{\"title\":\"$commit_message\", \"head\":\"$pr_branch\", \"base\":\"$main_branch\"}' https://api.github.com/repos/citusdata/packaging/pulls`;
