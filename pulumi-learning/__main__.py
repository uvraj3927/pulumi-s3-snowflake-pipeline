"""An AWS Python Pulumi program"""

import pulumi
from pulumi_aws import s3

#Create an AWS resource (S3 Bucket)
bucket = s3.Bucket('my-bucket-using-pulumi-41412082026')

                    #output

#3 s3 buckets at once
for i in range(3):
    bucket = s3.Bucket(f"bucket-{i}")
    pulumi.export('bucket_name', bucket.id) 