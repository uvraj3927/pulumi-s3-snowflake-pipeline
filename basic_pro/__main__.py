import pulumi
import pulumi_aws as aws
import pulumi_snowflake as snowflake

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

# Outputs
pulumi.export("s3_bucket_name", s3_bucket.id)
pulumi.export("snowflake_database", database.name)
pulumi.export("snowflake_schema", schema.name)
pulumi.export("snowflake_table", table.name)