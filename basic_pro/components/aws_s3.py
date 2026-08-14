"""
S3 Storage Component Resource.

Encapsulates AWS S3 raw data bucket provisioned with strict public access blocks
and tags adhering to enterprise compliance standards.
"""
from typing import Dict, Optional
import pulumi
import pulumi_aws as aws


class S3StorageComponent(pulumi.ComponentResource):
    """Encapsulates AWS S3 bucket and security configurations."""

    def __init__(
        self,
        name: str,
        bucket_name: str,
        tags: Optional[Dict[str, str]] = None,
        opts: Optional[pulumi.ResourceOptions] = None,
    ) -> None:
        super().__init__("enterprise:aws:S3StorageComponent", name, None, opts)

        child_opts = pulumi.ResourceOptions(parent=self)

        # 1. AWS S3 Bucket
        self.bucket = aws.s3.Bucket(
            f"{name}-bucket",
            bucket=bucket_name,
            tags=tags,
            opts=child_opts,
        )

        # 2. S3 Public Access Block Enforcement
        self.public_access_block = aws.s3.BucketPublicAccessBlock(
            f"{name}-public-access-block",
            bucket=self.bucket.id,
            block_public_acls=True,
            block_public_policy=True,
            ignore_public_acls=True,
            restrict_public_buckets=True,
            opts=child_opts,
        )

        # Expose key outputs
        self.bucket_id = self.bucket.id
        self.bucket_arn = self.bucket.arn

        self.register_outputs(
            {
                "bucket_id": self.bucket_id,
                "bucket_arn": self.bucket_arn,
            }
        )
