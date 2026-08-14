"""
Snowflake Database Component Resource.

Encapsulates Snowflake Database, Schema, and raw ingestion Table resources.
"""
from typing import Optional
import pulumi
import pulumi_snowflake as snowflake


class SnowflakeDatabaseComponent(pulumi.ComponentResource):
    """Encapsulates Snowflake Database, Schema, and raw events Table resources."""

    def __init__(
        self,
        name: str,
        db_name: str,
        schema_name: str,
        table_name: str,
        opts: Optional[pulumi.ResourceOptions] = None,
    ) -> None:
        super().__init__("enterprise:snowflake:DatabaseComponent", name, None, opts)

        child_opts = pulumi.ResourceOptions(parent=self)

        # 1. Snowflake Database
        self.database = snowflake.Database(
            f"{name}_db",
            name=db_name,
            comment="Database for S3 to Snowflake pipeline project",
            opts=child_opts,
        )

        # 2. Snowflake Schema
        self.schema = snowflake.Schema(
            f"{name}_schema",
            database=self.database.name,
            name=schema_name,
            comment="Schema holding raw loaded tables",
            opts=child_opts,
        )

        # 3. Target Ingestion Table
        self.table = snowflake.Table(
            f"{name}_table",
            database=self.database.name,
            schema=self.schema.name,
            name=table_name,
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
            opts=child_opts,
        )

        # Expose key outputs
        self.database_name = self.database.name
        self.schema_name = self.schema.name
        self.table_name = self.table.name

        self.register_outputs(
            {
                "database_name": self.database_name,
                "schema_name": self.schema_name,
                "table_name": self.table_name,
            }
        )
