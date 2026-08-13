
# S3 to Snowflake Data Pipeline using Pulumi

A beginner Infrastructure as Code project using Python and Pulumi
to create an AWS S3 to Snowflake data ingestion pipeline.

## Architecture

S3 Bucket
    ↓
Snowflake Storage Integration
    ↓
External Stage
    ↓
Snowpipe
    ↓
INCOMING_EVENTS table

## Technologies

- Python
- Pulumi
- AWS S3
- AWS IAM
- Snowflake
- Snowpipe

## What this project creates

### AWS
- S3 bucket
- S3 public access block
- IAM policy
- IAM role

### Snowflake
- Database
- Schema
- Table
- Storage integration
- JSON file format
- External S3 stage
- Snowpipe

## Data Flow

JSON files are uploaded to the S3 bucket.

Snowpipe automatically loads the JSON data into the
Snowflake INCOMING_EVENTS table.

The table contains:

- EVENT_ID
- PAYLOAD
- INGESTED_AT

## Current Status

Version 1 - Beginner project

The current goal is to understand how Pulumi can create
and connect AWS and Snowflake infrastructure.

Future versions will improve the data transformation
and pipeline architecture.