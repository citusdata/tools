#!/usr/bin/perl
use lib '/usr/local/bin';
use common_functions;

$NEW_VERSION = $ARGV[0];
$OLD_VERSION = $ARGV[1];

`git checkout master`;

# Update configuration file
$old_major_version = substr($OLD_VERSION, 0, 1);
$new_major_version = substr($NEW_VERSION, 0, 1);

# Means, we are releasing a new major version
if ($new_major_version != $old_major_version) {
    `cp -r citus-$old_major_version citus-$new_major_version`;
    `git add citus-$new_major_version`;
    `aws s3 cp --recursive --acl public-read --region us-east-1 s3://citus-deployment/aws/citus$old_major_version s3://citus-deployment/aws/citus$new_major_version`;
}

`sed -i 's/$OLD_VERSION/$NEW_VERSION/g' citus-$new_major_version/citusdb.json`;

# Commit changes to github
`git commit -a -m "Bump Citus version to $NEW_VERSION"`;
`git push origin master`;

# Push the new json template to S3
`aws s3 cp --acl public-read --region us-east-1 citus-$new_major_version/citusdb.json s3://citus-deployment/aws/citus$new_major_version/cloudformation/citus-$NEW_VERSION.json`;
