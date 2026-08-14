# Enterprise S3 to Snowflake Data Pipeline (Pulumi Python)

An enterprise-grade, modular Infrastructure-as-Code (IaC) repository built with **Pulumi** and **Python**. This architecture provisions a secure, automated data ingestion pipeline connecting AWS S3 and Snowflake using **Snowpipe**.

---

## 🏛️ Enterprise Modular Architecture

```
                                  AWS Cloud                                        |               Snowflake Cloud
                                                                                  |
   ┌───────────────────────┐         ┌────────────────────────┐                   |         ┌────────────────────────┐
   │    S3 Raw Data        │         │   AWS IAM Access Role  │                   |         │  Storage Integration   │
   │    (S3StorageComponent)│ <───────│(SnowflakeIamRoleComp)  │ <─────────────────┼─────────│  (External S3 Stage)   │
   └───────────────────────┘         └────────────────────────┘  AssumeRole Trust │         └────────────────────────┘
               │                                                                  |                      │
               │ Auto-ingest Notification                                         |                      ▼
               └──────────────────────────────────────────────────────────────────┼─────────> ┌────────────────────┐
                                                                                  |           │      Snowpipe      │
                                                                                  |           └────────────────────┘
                                                                                  |                      │
                                                                                  |                      ▼
                                                                                  |         ┌────────────────────┐
                                                                                  |         │  INCOMING_EVENTS   │
                                                                                  |         │ (SnowflakeDBComp)  │
                                                                                  |         └────────────────────┘
```

---

## 📁 Repository Structure

```text
basic_pro/
├── config.py                 # Centralized Pulumi configuration parser & enterprise tagging
├── components/               # Enterprise Pulumi ComponentResources
│   ├── __init__.py           # Package export declarations
│   ├── aws_s3.py             # S3StorageComponent: Secure S3 bucket & public access block
│   ├── aws_iam.py            # SnowflakeIamRoleComponent: AWS IAM policy & STS trust policy
│   ├── snowflake_db.py       # SnowflakeDatabaseComponent: Database, Schema, & Table DDL
│   └── snowflake_pipeline.py # SnowflakeIngestionPipelineComponent: Integration, Stage, Format & Snowpipe
├── __main__.py               # Clean top-level orchestration entrypoint
├── Pulumi.yaml               # Pulumi project metadata & runtime settings
├── Pulumi.dev.yaml           # Stack configuration & encrypted credentials
├── requirements.txt          # Python dependencies
└── README.md                 # Technical documentation
```

---

## 🌟 Key Enterprise Principles Implemented

### 1. Object-Oriented Component Resource Pattern (`pulumi.ComponentResource`)
Rather than placing all resources flat in `__main__.py`, resources are encapsulated into reusable, modular `ComponentResource` classes. This provides clean namespaces, isolated state tracking, and reusability across multiple stacks/environments (e.g., `dev`, `staging`, `prod`).

### 2. Configuration-Driven Architecture (`config.py`)
No hardcoded resource names, regions, or tags exist in the resource logic. Configuration is centralized in `config.py` using `pulumi.Config()`, supporting multi-environment deployments via `Pulumi.<stack>.yaml`.

### 3. Enterprise Security & Trust Management
- **S3 Public Access Block**: Enforces `block_public_acls`, `block_public_policy`, `ignore_public_acls`, and `restrict_public_buckets`.
- **Dynamic Cross-Account IAM Trust**: Synthesizes AWS STS `AssumeRole` policies with conditional `sts:ExternalId` verification dynamically retrieved from Snowflake's storage integration.
- **Least-Privilege IAM**: Scopes S3 permissions to required read-only actions (`s3:GetObject`, `s3:ListBucket`).

### 4. Enterprise Tagging Strategy
Every AWS resource inherits global enterprise metadata tags:
```python
{
    "Environment": "dev",
    "Project": "S3-Snowflake-Pipeline",
    "ManagedBy": "Pulumi",
    "Stack": "dev"
}
```

---

## 🚀 Deployment Guide

### Prerequisites
- [Pulumi CLI](https://www.pulumi.com/docs/get-started/install/)
- Python 3.9+
- AWS CLI configured with administrator access
- Snowflake account credentials configured in Pulumi

### Installation & Setup

1. **Activate Environment & Install Dependencies**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure Snowflake Credentials**:
   ```bash
   pulumi config set snowflake:user <YOUR_USER>
   pulumi config set --secret snowflake:password <YOUR_PASSWORD>
   pulumi config set snowflake:role ACCOUNTADMIN
   pulumi config set snowflake:warehouse COMPUTE_WH
   pulumi config set snowflake:accountName <YOUR_ACCOUNT_NAME>
   pulumi config set snowflake:organizationName <YOUR_ORG_NAME>
   ```

3. **Preview & Deploy Infrastructure**:
   ```bash
   pulumi up
   ```

4. **Verify Stack Outputs**:
   ```bash
   pulumi stack output
   ```

---

## 🧪 Pipeline Flow

1. JSON files are uploaded to the S3 bucket (`<project_prefix>-raw-data-bucket`).
2. Snowpipe automatically detects incoming files using S3 event notifications / notification channels.
3. Data is automatically ingested into Snowflake table `DEMO_PIPELINE_DB.RAW_DATA.INCOMING_EVENTS`.