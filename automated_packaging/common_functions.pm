#!/usr/bin/perl

package common_functions;
use Exporter;
use JSON;

# Export subroutines
our @ISA = qw(Exporter);
our @EXPORT = qw(get_and_verify_token get_microsoft_email get_git_name get_sorted_prs create_release_changelog has_backport_label);

# untaint environment
local $ENV{'PATH'} = '/usr/local/bin:/usr/local/sbin:/usr/bin:/bin:/usr/sbin:/sbin';

sub get_microsoft_email {
    unless (exists $ENV{MICROSOFT_EMAIL}) {
        die "You must have a MICROSOFT_EMAIL set";
    }

    my $microsoft_email = $ENV{MICROSOFT_EMAIL};
    return $microsoft_email;
}

sub get_git_name {
    my $git_name = `git config user.name`;
    # Strip trailing newline
    chomp $git_name;
    if ($git_name eq "") {
        die "You must set your git name using 'git config user.name \"Your name Here\"'";
    }
    return $git_name;
}


sub get_and_verify_token {
    unless (exists $ENV{GITHUB_TOKEN}) {
        die "You must have a GITHUB_TOKEN set";
    }

    my $github_token = $ENV{GITHUB_TOKEN};
    if ($ENV{GITHUB_TOKEN} =~ /^(\w+)$/x) {
        $github_token = $1;
    }
    else {
        die "Malformed GITHUB_TOKEN: $github_token";
    }

    my $cmd = "curl -sf -H 'Accept: application/vnd.github.v3.full+json' -X GET --user '$github_token:x-oauth-basic' " . 'https://api.github.com/';
    my $result = `$cmd > /dev/null 2>&1`;
    my $exit_code = $? >> 8;

    if ($exit_code == 22) {
        die "Your token was rejected by GitHub.";
    }

    return $github_token;
}

# Get sorted PRs according to merged-at by collecting PRs up to given data (using created info)
sub get_sorted_prs {
    my $earliest_pr_date = @_[0];
    my $repo_name = @_[1];
    my %sorted_pr_hash = ();
    my $github_token = get_and_verify_token();

    my $page_number = 1;
    $merged_date = "2100-12-12";
    do {
        my $prs_text = `curl -H "Accept: application/vnd.github.v3.full+json" -X GET --user "$github_token:x-oauth-basic" 'https://api.github.com/repos/citusdata/$repo_name/pulls?base=master&state=all&page=$page_number' 2> /dev/null`;
        my @prs = @{decode_json($prs_text)};

        foreach my $pr (@prs) {
            my %pr_hash = %$pr;

            if (defined($pr_hash{'merged_at'})) {

                $merged_date = substr($pr_hash{'merged_at'}, 0, 10);
                $created_date = substr($pr_hash{'created_at'}, 0, 10);

                if ($created_date lt $earliest_pr_date) {
                    last;
                }

                if ($merged_date lt $earliest_pr_date) {
                    next;
                }

                $sorted_pr_hash{$pr_hash{'merged_at'}} = $pr_hash{'url'};
            }
        }

        $page_number += 1;
    } while ($created_date gt $earliest_pr_date);

    my @keys = reverse sort keys(%sorted_pr_hash);
    my @vals = @sorted_pr_hash{@keys};

    print( "PRs has been read in the merge order ..." . "\n" );

    return @vals;
}

# Search for the backport label given a label array
sub has_backport_label {

    my @labels = @{$_[0]};

    foreach my $label (@labels) {
        %label_hash = %{$label};
        if ($label_hash{'name'} eq 'backport') {
            return 1;
        }
    }

    return 0;
}

# Creates changelog entries up to the given last date. It extracts lines starting with DESCRIPTION: from
# PR messages to generate these entries. You can use different repo names to generate changelog entries for
# different repos.
sub create_release_changelog {
    my $earliest_pr_date = @_[0];
    my $repo_name = @_[1];
    my $is_point_release = @_[2];

    my @comment_lines = ();
    my $github_token = get_and_verify_token();

    my @sorted_pr_urls = get_sorted_prs($earliest_pr_date, $repo_name);

    foreach my $pr_url (@sorted_pr_urls) {
        print("Getting information for " . $pr_url . "\n");
        my $pr_text = `curl -H "Accept: application/vnd.github.v3.full+json" -X GET --user "$github_token:x-oauth-basic" '$pr_url' 2> /dev/null`;
        my %pr_hash = %{decode_json($pr_text)};
        my $add_to_changelog = 1;

        if ($is_point_release) {
            my $issue_url = $pr_hash{'issue_url'};
            my $issue_text = `curl -H "Accept: application/vnd.github.v3.full+json" -X GET --user "$github_token:x-oauth-basic" '$issue_url' 2> /dev/null`;
            my %issue_hash = %{decode_json($issue_text)};
            $add_to_changelog = 0;

            @labels = @{$issue_hash{'labels'}};
            if (has_backport_label(\@labels)) {
                $add_to_changelog = 1;
            }
        }

        if ($add_to_changelog) {
            @log_output = split("\n", $pr_hash{'body'});
            foreach $line (@log_output) {
                if ($line =~ /^DESCRIPTION: */) {
                    $description_part = substr($line, length($&), -1);
                    if (length($description_part) > 78) {
                        print("You have to shorten PR message $description_part of $pr_url");
                        `git reset --hard`;
                        die "Can not add description longer than 78 charachters";
                    }
                    print("Description $description_part has been added ... \n");
                    push(@comment_lines, "* " . $description_part . "\n\n");
                }
            }
        }
    }

    return @comment_lines;
}
