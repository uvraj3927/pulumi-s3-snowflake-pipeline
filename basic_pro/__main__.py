import pulumi
import pulumi_aws as aws
import pulumi_snowflake as snowflake
import json

PREFIX_AWS = "s3-snowflake-demo414"
PROJECT_PREFIX = "s3-snowflake-demo414"

# 1. AWS S3 Bucket
s3_bucket = aws.s3.Bucket(
    f"{PROJECT_PREFIX}-bucket",
    bucket=f"{PROJECT_PREFIX}-raw-data-bucket",
    tags={
        "Environment": "Dev",
        "Project": "S3-Snowflake-Pipeline",
    },
)

s3_bucket_public_access_block = aws.s3.BucketPublicAccessBlock(
    f"{PROJECT_PREFIX}-bucket-public-access-block",
    bucket=s3_bucket.id,
    block_public_acls=True,
    block_public_policy=True,
    ignore_public_acls=True,
    restrict_public_buckets=True,
)

# 2. Snowflake Database, Schema, and Table
database = snowflake.Database(
    f"{PROJECT_PREFIX}_db",
    name="DEMO_PIPELINE_DB",
    comment="Database for S3 to Snowflake pipeline project",
)

schema = snowflake.Schema(
    f"{PROJECT_PREFIX}_schema",
    database=database.name,
    name="RAW_DATA",
    comment="Schema holding raw loaded tables",
)

table = snowflake.Table(
    f"{PROJECT_PREFIX}_table",
    database=database.name,
    schema=schema.name,
    name="INCOMING_EVENTS",
    comment="Table storing raw incoming events from S3",
    columns=[
        {
            "name": "EVENT_ID",
            "type": "VARCHAR(16777216)",
            "nullable": False,
        },
        {
            "name": "PAYLOAD",
            "type": "VARIANT",
            "nullable": True,
        },
        {
            "name": "INGESTED_AT",
            "type": "TIMESTAMP_NTZ(9)",
            "nullable": False,
        },
    ],
)
'''
# Outputs
pulumi.export("s3_bucket_name", s3_bucket.id)
pulumi.export("snowflake_database", database.name)
pulumi.export("snowflake_schema", schema.name)
pulumi.export("snowflake_table", table.name)'''
# ==========================================
# STEP 2 RESOURCES: Storage Integration & IAM
# ==========================================

# 1. Create S3 Bucket Access Policy
s3_access_policy = aws.iam.Policy(
    f"{PREFIX_AWS}-s3-policy",
    name=f"{PREFIX_AWS}-s3-access-policy",
    policy=s3_bucket.arn.apply(lambda arn: json.dumps({
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "s3:GetObject",
                    "s3:GetObjectVersion"
                ],
                "Resource": f"{arn}/*"
            },
            {
                "Effect": "Allow",
                "Action": [
                    "s3:ListBucket",
                    "s3:GetBucketLocation"
                ],
                "Resource": arn
            }
        ]
    })),
)

# 2. Get current AWS Account ID dynamically to scoping initial trust policy
current_aws_caller = aws.get_caller_identity()

# Create initial IAM Role allowing AWS account principal (scoped down)
snowflake_role = aws.iam.Role(
    f"{PREFIX_AWS}-snowflake-role",
    name=f"{PREFIX_AWS}-snowflake-access-role",
    assume_role_policy=json.dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"AWS": f"arn:aws:iam::{current_aws_caller.account_id}:root"},
            "Action": "sts:AssumeRole"
        }]
    }),
)

# Attach S3 Policy to IAM Role
aws.iam.RolePolicyAttachment(
    f"{PREFIX_AWS}-role-policy-attach",
    role=snowflake_role.name,
    policy_arn=s3_access_policy.arn,
)

# 3. Create Snowflake Storage Integration
storage_integration = snowflake.StorageIntegration(
    f"{PROJECT_PREFIX}_storage_integration",
    name="S3_STORAGE_INTEGRATION",
    type="EXTERNAL_STAGE",
    storage_provider="S3",
    enabled=True,
    storage_allowed_locations=[s3_bucket.arn.apply(lambda arn: f"s3://{arn.split(':')[-1]}/")],
    storage_aws_role_arn=snowflake_role.arn,
)

# ==========================================
# Stack Outputs
# ==========================================
pulumi.export("s3_bucket_name", s3_bucket.id)
pulumi.export("snowflake_database", database.name)
pulumi.export("snowflake_schema", schema.name)
pulumi.export("snowflake_table", table.name)
pulumi.export("storage_integration_name", storage_integration.name)
pulumi.export("snowflake_iam_user_arn", storage_integration.storage_aws_iam_user_arn)
pulumi.export("snowflake_external_id", storage_integration.storage_aws_external_id)