"""
AWS IAM Snowflake Access Component Resource.

Encapsulates S3 permission policies, cross-account IAM role creation,
dynamic STS trust policy synthesis, and policy attachments for Snowflake integration.
"""
import json
from typing import Any, Dict, List, Optional
import pulumi
import pulumi_aws as aws


class SnowflakeIamRoleComponent(pulumi.ComponentResource):
    """Encapsulates AWS IAM Role & Policy resources for Snowflake storage integration."""

    def __init__(
        self,
        name: str,
        prefix: str,
        s3_bucket_arn: pulumi.Input[str],
        storage_iam_user_arn: pulumi.Input[Optional[str]],
        storage_describe_outputs: pulumi.Input[Optional[List[Dict[str, Any]]]],
        opts: Optional[pulumi.ResourceOptions] = None,
    ) -> None:
        super().__init__("enterprise:aws:SnowflakeIamRoleComponent", name, None, opts)

        child_opts = pulumi.ResourceOptions(parent=self)

        # 1. AWS S3 Access Policy
        self.s3_access_policy = aws.iam.Policy(
            f"{prefix}-s3-policy",
            name=f"{prefix}-s3-access-policy",
            policy=pulumi.Output.from_input(s3_bucket_arn).apply(
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
            opts=child_opts,
        )

        # 2. Retrieve caller identity for AWS Account scoping
        current_aws_caller = aws.get_caller_identity()

        # 3. Dynamic STS AssumeRole Trust Policy generator
        def make_assume_role_policy(args):
            iam_user_arn, describe_outputs, account_id = args[0], args[1], args[2]

            external_id = None
            if describe_outputs:
                for out in describe_outputs:
                    items = (
                        out.get("storage_aws_external_ids")
                        or out.get("storageAwsExternalIds")
                        or []
                    )
                    for item in items:
                        if item.get("name") == "STORAGE_AWS_EXTERNAL_ID":
                            external_id = item.get("value")
                            break

            statement = {
                "Effect": "Allow",
                "Principal": {
                    "AWS": (
                        iam_user_arn
                        if iam_user_arn
                        else f"arn:aws:iam::{account_id}:root"
                    )
                },
                "Action": "sts:AssumeRole",
            }
            if external_id:
                statement["Condition"] = {
                    "StringEquals": {"sts:ExternalId": external_id}
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

        assume_role_policy = pulumi.Output.all(
            storage_iam_user_arn,
            storage_describe_outputs,
            current_aws_caller.account_id,
        ).apply(make_assume_role_policy)

        # 4. IAM Role for Snowflake Access
        self.role = aws.iam.Role(
            f"{prefix}-snowflake-role",
            name=f"{prefix}-snowflake-access-role",
            assume_role_policy=assume_role_policy,
            opts=child_opts,
        )

        # 5. Role Policy Attachment
        self.role_policy_attachment = aws.iam.RolePolicyAttachment(
            f"{prefix}-role-policy-attach",
            role=self.role.name,
            policy_arn=self.s3_access_policy.arn,
            opts=child_opts,
        )

        # Expose key outputs
        self.role_arn = self.role.arn
        self.role_name = self.role.name

        self.register_outputs(
            {
                "role_arn": self.role_arn,
                "role_name": self.role_name,
            }
        )
