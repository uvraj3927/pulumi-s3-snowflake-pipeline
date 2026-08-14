"""
Enterprise S3 to Snowflake Ingestion Pipeline.

Main entrypoint composing high-level modular infrastructure components:
1. S3StorageComponent: Secure AWS S3 bucket with public access block
2. SnowflakeDatabaseComponent: Snowflake Database, Schema, and raw Table
3. SnowflakeIngestionPipelineComponent: Storage Integration, IAM Role, Stage, and Snowpipe
"""
import pulumi
from components import (
    S3StorageComponent,
    SnowflakeDatabaseComponent,
    SnowflakeIngestionPipelineComponent,
)
from config import config

# 1. Instantiate AWS S3 Raw Data Bucket Component
s3_storage = S3StorageComponent(
    f"{config.project_prefix}-s3",
    bucket_name=config.s3_bucket_name,
    tags=config.tags,
)

# 2. Instantiate Snowflake Core Resources (DB, Schema, Table)
snowflake_db = SnowflakeDatabaseComponent(
    config.project_prefix,
    db_name=config.snowflake_db_name,
    schema_name=config.snowflake_schema_name,
    table_name=config.snowflake_table_name,
)

# 3. Instantiate Snowflake Data Ingestion Pipeline & AWS IAM Integration
pipeline = SnowflakeIngestionPipelineComponent(
    config.project_prefix,
    project_prefix=config.project_prefix,
    aws_prefix=config.project_prefix,
    s3_bucket_arn=s3_storage.bucket_arn,
    database_name=snowflake_db.database_name,
    schema_name=snowflake_db.schema_name,
    table_name=snowflake_db.table_name,
    storage_integration_name=config.storage_integration_name,
    file_format_name=config.file_format_name,
    stage_name=config.stage_name,
    pipe_name=config.pipe_name,
)

# Consolidated Enterprise Stack Outputs
pulumi.export("s3_bucket_name", s3_storage.bucket_id)
pulumi.export("s3_bucket_arn", s3_storage.bucket_arn)
pulumi.export("snowflake_database", snowflake_db.database_name)
pulumi.export("snowflake_schema", snowflake_db.schema_name)
pulumi.export("snowflake_table", snowflake_db.table_name)
pulumi.export("storage_integration_name", pipeline.storage_integration_name)
pulumi.export("snowflake_iam_user_arn", pipeline.storage_aws_iam_user_arn)
pulumi.export("snowflake_role_arn", pipeline.iam_role_arn)
pulumi.export("snowflake_stage_name", pipeline.stage_name)
pulumi.export("snowflake_pipe_name", pipeline.pipe_name)
pulumi.export("snowpipe_notification_channel", pipeline.notification_channel)