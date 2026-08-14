"""
Snowflake Data Ingestion Pipeline Component Resource.

Encapsulates Storage Integration, AWS IAM Snowflake Role, JSON File Format,
External Stage, and Snowpipe automated ingestion into a cohesive enterprise component.
"""
from typing import Optional
import pulumi
import pulumi_aws as aws
import pulumi_snowflake as snowflake

from components.aws_iam import SnowflakeIamRoleComponent


class SnowflakeIngestionPipelineComponent(pulumi.ComponentResource):
    """Encapsulates Storage Integration, IAM Role, Stage, File Format, and Snowpipe resources."""

    def __init__(
        self,
        name: str,
        project_prefix: str,
        aws_prefix: str,
        s3_bucket_arn: pulumi.Input[str],
        database_name: pulumi.Input[str],
        schema_name: pulumi.Input[str],
        table_name: pulumi.Input[str],
        storage_integration_name: str,
        file_format_name: str,
        stage_name: str,
        pipe_name: str,
        opts: Optional[pulumi.ResourceOptions] = None,
    ) -> None:
        super().__init__(
            "enterprise:snowflake:IngestionPipelineComponent", name, None, opts
        )

        child_opts = pulumi.ResourceOptions(parent=self)

        # 1. Fetch caller identity to compose target AWS IAM role ARN for Snowflake integration
        current_aws_caller = aws.get_caller_identity()
        snowflake_role_arn = f"arn:aws:iam::{current_aws_caller.account_id}:role/{aws_prefix}-snowflake-access-role"

        # 2. Snowflake Storage Integration
        self.storage_integration = snowflake.StorageIntegration(
            f"{project_prefix}_storage_integration",
            name=storage_integration_name,
            type="EXTERNAL_STAGE",
            storage_provider="S3",
            enabled=True,
            storage_allowed_locations=[
                pulumi.Output.from_input(s3_bucket_arn).apply(
                    lambda arn: f"s3://{arn.split(':')[-1]}/"
                )
            ],
            storage_aws_role_arn=snowflake_role_arn,
            opts=child_opts,
        )

        # 3. AWS IAM Role Component for Snowflake (cross-account trust policy synthesis)
        self.iam_role_component = SnowflakeIamRoleComponent(
            f"{name}-iam-role",
            prefix=aws_prefix,
            s3_bucket_arn=s3_bucket_arn,
            storage_iam_user_arn=self.storage_integration.storage_aws_iam_user_arn,
            storage_describe_outputs=self.storage_integration.describe_outputs,
            opts=child_opts,
        )

        # 4. JSON File Format
        self.file_format = snowflake.FileFormat(
            f"{project_prefix}_json_file_format",
            name=file_format_name,
            database=database_name,
            schema=schema_name,
            format_type="JSON",
            strip_outer_array=True,
            ignore_utf8_errors=True,
            opts=child_opts,
        )

        # 5. External S3 Stage
        self.stage = snowflake.StageExternalS3(
            f"{project_prefix}_s3_stage",
            name=stage_name,
            database=database_name,
            schema=schema_name,
            url=pulumi.Output.from_input(s3_bucket_arn).apply(
                lambda arn: f"s3://{arn.split(':')[-1]}/"
            ),
            storage_integration=self.storage_integration.name,
            file_format={
                "format_name": pulumi.Output.all(
                    database_name, schema_name, self.file_format.name
                ).apply(lambda args: f'"{args[0]}"."{args[1]}"."{args[2]}"')
            },
            opts=child_opts,
        )

        # 6. Dynamic COPY INTO query statement
        copy_statement = pulumi.Output.all(
            database_name, schema_name, table_name, self.stage.name
        ).apply(
            lambda args: (
                f'COPY INTO "{args[0]}"."{args[1]}"."{args[2]}" (EVENT_ID, PAYLOAD, INGESTED_AT) '
                f'FROM (SELECT $1:EVENT_ID::VARCHAR, $1, CURRENT_TIMESTAMP() '
                f'FROM @"{args[0]}"."{args[1]}"."{args[3]}") FILE_FORMAT = (TYPE = \'JSON\')'
            )
        )

        # 7. Snowpipe Automatic Ingestion Pipe
        self.pipe = snowflake.Pipe(
            f"{project_prefix}_pipe",
            name=pipe_name,
            database=database_name,
            schema=schema_name,
            copy_statement=copy_statement,
            auto_ingest=True,
            opts=pulumi.ResourceOptions.merge(
                child_opts,
                pulumi.ResourceOptions(
                    depends_on=[self.iam_role_component.role, self.stage]
                ),
            ),
        )

        # Expose Key Outputs
        self.storage_integration_name = self.storage_integration.name
        self.storage_aws_iam_user_arn = (
            self.storage_integration.storage_aws_iam_user_arn
        )
        self.iam_role_arn = self.iam_role_component.role_arn
        self.stage_name = self.stage.name
        self.pipe_name = self.pipe.name
        self.notification_channel = self.pipe.notification_channel

        self.register_outputs(
            {
                "storage_integration_name": self.storage_integration_name,
                "storage_aws_iam_user_arn": self.storage_aws_iam_user_arn,
                "iam_role_arn": self.iam_role_arn,
                "stage_name": self.stage_name,
                "pipe_name": self.pipe_name,
                "notification_channel": self.notification_channel,
            }
        )
