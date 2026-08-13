import json
import pulumi
import pulumi_aws as aws
import pulumi_snowflake as snowflake

PREFIX_AWS = "s3-snowflake-demo414"
PROJECT_PREFIX = "s3-snowflake-demo414"

# ==========================================
# STEP 1 RESOURCES: S3 Bucket, DB, Schema, Table
# ==========================================

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

# ==========================================
# STEP 2 RESOURCES: Storage Integration & IAM
# ==========================================

# 1. Create S3 Bucket Access Policy
s3_access_policy = aws.iam.Policy(
    f"{PREFIX_AWS}-s3-policy",
    name=f"{PREFIX_AWS}-s3-access-policy",
    policy=s3_bucket.arn.apply(
        lambda arn: json.dumps(
            {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": [
                            "s3:GetObject",
                            "s3:GetObjectVersion",
                        ],
                        "Resource": f"{arn}/*",
                    },
                    {
                        "Effect": "Allow",
                        "Action": [
                            "s3:ListBucket",
                            "s3:GetBucketLocation",
                        ],
                        "Resource": arn,
                    },
                ],
            }
        )
    ),
)

# 2. Get current AWS Account ID for scoping
current_aws_caller = aws.get_caller_identity()
snowflake_role_arn = f"arn:aws:iam::{current_aws_caller.account_id}:role/{PREFIX_AWS}-snowflake-access-role"

# 3. Create Snowflake Storage Integration
storage_integration = snowflake.StorageIntegration(
    f"{PROJECT_PREFIX}_storage_integration",
    name="S3_STORAGE_INTEGRATION",
    type="EXTERNAL_STAGE",
    storage_provider="S3",
    enabled=True,
    storage_allowed_locations=[
        s3_bucket.arn.apply(lambda arn: f"s3://{arn.split(':')[-1]}/")
    ],
    storage_aws_role_arn=snowflake_role_arn,
)

# Build IAM Trust Policy allowing Snowflake's IAM User & External ID to assume this role
def make_assume_role_policy(args):
    iam_user_arn, describe_outputs, account_id = args[0], args[1], args[2]

    external_id = None
    if describe_outputs:
        for out in describe_outputs:
            items = out.get("storage_aws_external_ids") or out.get("storageAwsExternalIds") or []
            for item in items:
                if item.get("name") == "STORAGE_AWS_EXTERNAL_ID":
                    external_id = item.get("value")
                    break

    statement = {
        "Effect": "Allow",
        "Principal": {
            "AWS": iam_user_arn if iam_user_arn else f"arn:aws:iam::{account_id}:root"
        },
        "Action": "sts:AssumeRole",
    }
    if external_id:
        statement["Condition"] = {
            "StringEquals": {
                "sts:ExternalId": external_id
            }
        }

    return json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                statement,
                {
                    "Effect": "Allow",
                    "Principal": {
                        "AWS": f"arn:aws:iam::{account_id}:root"
                    },
                    "Action": "sts:AssumeRole",
                },
            ],
        }
    )

snowflake_assume_role_policy = pulumi.Output.all(
    storage_integration.storage_aws_iam_user_arn,
    storage_integration.describe_outputs,
    current_aws_caller.account_id,
).apply(make_assume_role_policy)

# Create IAM Role with updated trust policy
snowflake_role = aws.iam.Role(
    f"{PREFIX_AWS}-snowflake-role",
    name=f"{PREFIX_AWS}-snowflake-access-role",
    assume_role_policy=snowflake_assume_role_policy,
)

# Attach S3 Policy to IAM Role
aws.iam.RolePolicyAttachment(
    f"{PREFIX_AWS}-role-policy-attach",
    role=snowflake_role.name,
    policy_arn=s3_access_policy.arn,
)

# ==========================================
# STEP 3 RESOURCES: File Format, Stage & Pipe
# ==========================================

# 1. Create Stable File Format
json_file_format = snowflake.FileFormat(
    f"{PROJECT_PREFIX}_json_file_format",
    name="JSON_FILE_FORMAT",
    database=database.name,
    schema=schema.name,
    format_type="JSON",
    strip_outer_array=True,
    ignore_utf8_errors=True,
)

# 2. Create External Stage pointing to S3 Bucket
s3_stage = snowflake.StageExternalS3(
    f"{PROJECT_PREFIX}_s3_stage",
    name="S3_RAW_DATA_STAGE",
    database=database.name,
    schema=schema.name,
    url=s3_bucket.arn.apply(lambda arn: f"s3://{arn.split(':')[-1]}/"),
    storage_integration=storage_integration.name,
    file_format={
        "format_name": pulumi.Output.all(database.name, schema.name, json_file_format.name).apply(
            lambda args: f'"{args[0]}"."{args[1]}"."{args[2]}"'
        )
    },
)

# 3. Create Snowpipe
copy_statement = pulumi.Output.all(
    database.name, schema.name, table.name, s3_stage.name
).apply(
    lambda args: f'COPY INTO "{args[0]}"."{args[1]}"."{args[2]}" (EVENT_ID, PAYLOAD, INGESTED_AT) FROM (SELECT $1:EVENT_ID::VARCHAR, $1, CURRENT_TIMESTAMP() FROM @"{args[0]}"."{args[1]}"."{args[3]}") FILE_FORMAT = (TYPE = \'JSON\')'
)

snowflake_pipe = snowflake.Pipe(
    f"{PROJECT_PREFIX}_pipe",
    name="S3_TO_SNOWFLAKE_PIPE",
    database=database.name,
    schema=schema.name,
    copy_statement=copy_statement,
    auto_ingest=True,
    opts=pulumi.ResourceOptions(depends_on=[snowflake_role, s3_stage]),
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
pulumi.export("snowflake_stage_name", s3_stage.name)
pulumi.export("snowflake_pipe_name", snowflake_pipe.name)
pulumi.export("snowpipe_notification_channel", snowflake_pipe.notification_channel)