# 5. Runbook – Redshift SQL Deploy via GitHub Actions

## Purpose

This workflow deploys ordered SQL changes into Amazon Redshift using GitHub Actions.  

It can run in two modes:

- **Discovery mode (no credentials):** lists the SQL files that would run.  
- **Execution mode (with credentials):** executes the SQL files against Redshift inside a single batch transaction.  

## Pre-Requisites

- GitHub repository with Actions enabled.  
- The following GitHub Secrets configured:  
  - `REDSHIFT_HOST`  
  - `REDSHIFT_PORT`  
  - `REDSHIFT_DB`  
  - `REDSHIFT_USER`  
  - `REDSHIFT_PASSWORD`  
- Redshift must allow network access from GitHub runners (VPC / security group).  

## Inputs

- `branch` → the Git ref to deploy from.  
- `sql_path` → a single SQL file or a folder (default: `sql/`).  
- `execution_order` (optional) → comma-separated list of filenames when running in folder mode.  

## Security & Compliance
- Credentials are injected securely via GitHub Secrets.
- No credentials are stored in code or artifacts.
- Evidence files contain only safe metadata (no secrets).
- Redshift access restricted via VPC/security groups (Hopefully).


## How to Run
1. Go to GitHub → Actions → select **Redshift SQL Deploy (manual)**.
2. Click **Run workflow** and provide branch, sql_path, and execution_order if required.
3. Monitor the logs. The workflow runs in this order:  
   Setup → Syntax check / Pytest → Discovery (always) → Execute SQL (only if credentials exist) → Upload evidence.

### When credentials are not available
- The workflow runs in **dry run mode**.  
- Only the discovery step is executed.  
- It lists the SQL files in order but does not connect to Redshift. 
    Setup → Syntax check / Pytest → Discovery (always) → Upload evidence (no SQL executed, creds not available)



### Logs and evidence

- Logs are available in the GitHub Actions job output.  
- If no credentials are set, the evidence artifact still contains:  
  - `evidence.json` showing the list of discovered SQL files and their order.  
- If credentials are set, evidence includes:  
- `run_id`, `started_at`, `finished_at`  
- `env_summary` (safe values only)  
- Per-step timings, row counts, success/failure status  

## Screenshots

The following screenshots illustrate how the workflow behaves in different scenarios.

### 1. Successful run (with credentials)
Shows a full execution where all SQL files succeed.  
The Actions log displays the **Evidence Summary** with `run_id`, files executed, timings, and row counts.  

![Successful Run](screenshots/successful-run.png)

---

### 2. Dry run (without credentials)
When secrets are not configured, the workflow runs in **discovery mode**.  
The Actions log lists the SQL files in order, but no connection is made to Redshift.  

![Dry Run](screenshots/dry-run.png)

---

### 3. Evidence artifact (`evidence.json`)
Each run produces structured evidence (`artifacts/run-<timestamp>/evidence.json`).  
This file records metadata, per-file status, timings, and rollback details.  

![Evidence JSON](screenshots/evidence-json.png)


## Outputs

- Logs showing discovered SQL files and results.  
- Evidence artifact uploaded:  
- `redshift-evidence-<run_id>/summary.json`  
- Per-file logs if SQL was executed.  
- **Rollback is automatic within a run:** if any file fails, all changes are rolled back.  
- For planned rollbacks of previous deployments, prepare a rollback SQL (e.g. prefixed with `900_`).  

## Rollback

- **Auto rollback:** Built-in. If any SQL file fails during execution, the entire transaction is rolled back automatically (no partial changes).  
- **Planned rollback:** For already-deployed changes, prepare a rollback SQL script (e.g. `DROP`, `ALTER`) and prefix it with `900_`. Re-run the workflow with this file included.  
- **Evidence:** The generated `evidence.json` and logs confirm whether the rollback executed successfully and in what order.  
  

## Troubleshooting

- **No artifact:** check that “Prepare artifacts” and “Discovery” steps ran successfully.  
- **Import/module error:** make sure the runner is invoked as a module (already in the workflow).  
- **Connection/authentication error:** check GitHub Secrets and Redshift network access.  
- **Policy block:** destructive SQL in prod blocked unless `ALLOW_DESTRUCTIVE=true`.  


## Ownership and Escalation
- Application owner: Data/BI team-                         TBD,           Phone: 123456789, Email:abc@xxx.com
- Pipeline owner: Release Engineer-                        Ashish Dev,    Phone: 123456789, Email:def@xxx.com
- Infrastructure owner: Cloud Platform (VPC and Redshift)- TBD,           Phone: 123456789, Email:ghy@xxx.com

---

[Back to top](#allwyn-test-2--redshift-sql-deploy-via-github-actions)
