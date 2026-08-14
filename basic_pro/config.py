"""
Centralized Configuration Module for Basic Pro Infrastructure.

Provides strongly-typed access to stack configuration parameters, falling back to sensible enterprise defaults.
"""
from typing import Dict
import pulumi


class AppConfig:
    """Manages Pulumi project configuration and metadata."""

    def __init__(self) -> None:
        self.pulumi_config = pulumi.Config()
        self.aws_config = pulumi.Config("aws")

        # Stack & Environment Identity
        self.stack = pulumi.get_stack()
        self.project_prefix = (
            self.pulumi_config.get("project_prefix") or "s3-snowflake-demo414"
        )
        self.environment = (
            self.pulumi_config.get("environment") or self.stack
        )

        # AWS Settings
        self.aws_region = self.aws_config.get("region") or "us-east-1"

        # S3 Settings
        self.s3_bucket_name = (
            self.pulumi_config.get("s3_bucket_name")
            or f"{self.project_prefix}-raw-data-bucket"
        )

        # Snowflake Naming Configurations
        self.snowflake_db_name = (
            self.pulumi_config.get("snowflake_db_name") or "DEMO_PIPELINE_DB"
        )
        self.snowflake_schema_name = (
            self.pulumi_config.get("snowflake_schema_name") or "RAW_DATA"
        )
        self.snowflake_table_name = (
            self.pulumi_config.get("snowflake_table_name") or "INCOMING_EVENTS"
        )
        self.storage_integration_name = (
            self.pulumi_config.get("storage_integration_name")
            or "S3_STORAGE_INTEGRATION"
        )
        self.file_format_name = (
            self.pulumi_config.get("file_format_name") or "JSON_FILE_FORMAT"
        )
        self.stage_name = (
            self.pulumi_config.get("stage_name") or "S3_RAW_DATA_STAGE"
        )
        self.pipe_name = (
            self.pulumi_config.get("pipe_name") or "S3_TO_SNOWFLAKE_PIPE"
        )

        # Global Tagging Strategy
        self.tags: Dict[str, str] = {
            "Environment": self.environment,
            "Project": "S3-Snowflake-Pipeline",
            "ManagedBy": "Pulumi",
            "Stack": self.stack,
        }


# Global Singleton Instance
config = AppConfig()
