# SharePoint & Power Automate Setup Guide

This guide sets up the automated trigger so that dropping a BrightHR CSV into a SharePoint folder automatically kicks off the review and delivers an Excel workbook — with no local software and no manual steps.

---

## How It Works

```
BrightHR export (CSV)
        │
        ▼
 SharePoint folder          ← you drop the file here (private, access-controlled)
        │
        ▼  (Power Automate detects new file)
        │
        ▼
 GitHub Actions workflow    ← runs entirely in GitHub's cloud
        │
        ▼
 Excel workbook artifact    ← download from the Actions tab
```

The CSV never enters the GitHub repository.  It travels directly from SharePoint to the workflow runner's temporary storage and is discarded after the run.

---

## Prerequisites

| What | Where to get it |
|---|---|
| A SharePoint site and document library folder to receive BrightHR exports | Your Microsoft 365 admin |
| A GitHub Personal Access Token (PAT) with **Contents: Read** and **Actions: Write** permissions | [github.com → Settings → Developer settings → Personal access tokens → Fine-grained tokens](https://github.com/settings/personal-access-tokens/new) |
| Access to Power Automate (part of Microsoft 365) | [make.powerautomate.com](https://make.powerautomate.com) |

> **PAT scope note:** Create a fine-grained token scoped only to this repository, with *Actions: Read and write* permission. Do not give it broader access.

---

## Step 1 — Create the GitHub Personal Access Token

1. Go to **GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens**.
2. Click **Generate new token**.
3. Set:
   - **Token name:** `brighthr-time-review-power-automate`
   - **Expiration:** 1 year (set a calendar reminder to renew it)
   - **Repository access:** Only this repository
   - **Permissions → Repository permissions → Actions:** Read and write
4. Click **Generate token** and copy it immediately — you cannot see it again.

Keep this token **private**.  It will be stored as a secure credential inside Power Automate.

---

## Step 2 — Create the Power Automate Flow

1. Go to [make.powerautomate.com](https://make.powerautomate.com) and sign in with your Microsoft 365 account.
2. Click **+ Create → Automated cloud flow**.
3. Name the flow **BrightHR Time Review Trigger** and search for trigger **"When a file is created (properties only)"** (SharePoint).  Click **Create**.

### Configure the trigger

| Field | Value |
|---|---|
| **Site Address** | Your SharePoint site URL |
| **Library Name** | The document library where BrightHR exports will be dropped |
| **Folder** | The specific folder to watch (e.g. `/BrightHR Exports/Pending`) |

### Add action: Get file content

1. Click **+ New step**.
2. Search for **"Get file content"** (SharePoint).
3. Set:
   - **Site Address:** same as trigger
   - **File Identifier:** select **ID** from the trigger's dynamic content

### Add action: HTTP request to GitHub

1. Click **+ New step**.
2. Search for **"HTTP"** and select the **HTTP** action.
3. Configure:

| Field | Value |
|---|---|
| **Method** | POST |
| **URI** | `https://api.github.com/repos/margojanosi/blippython/dispatches` |
| **Headers** | `Accept`: `application/vnd.github+json` |
| | `Authorization`: `****** (paste the token you created in Step 1) |
| | `X-GitHub-Api-Version`: `2022-11-28` |
| | `Content-Type`: `application/json` |
| **Body** | See below |

**Body** (use the Expression editor for the base64 function):

```json
{
  "event_type": "brighthr-csv-ready",
  "client_payload": {
    "csv_content": "@{base64(body('Get_file_content'))}"
  }
}
```

> In Power Automate, click into the Body field, switch to **Expression** mode, and use `base64(body('Get_file_content'))` to generate the encoded content dynamically.

4. Click **Save**.

### Test the flow

1. Drop a CSV file into the watched SharePoint folder.
2. In Power Automate, click **My flows → BrightHR Time Review Trigger → Run history** — you should see a successful run within a minute or two.
3. In GitHub, go to the **Actions** tab — a **BrightHR Time Review** run should appear and complete within 1–2 minutes.
4. Click the completed run and download the **brighthr-time-review-workbook** artifact.

---

## Step 3 — Ongoing Use (Every Payroll Period)

Once the flow is set up, the process is:

1. **Export the CSV** from BrightHR → Timesheets section.
2. **Drop it** into the designated SharePoint folder.
3. **Wait 1–2 minutes** for GitHub Actions to complete.
4. **Download the workbook** from GitHub → Actions → latest run → Artifacts.
5. **Open the workbook** and review the Exception Report tab.
6. **Correct confirmed issues** in BrightHR and save the workbook as payroll documentation.

---

## Keeping Credentials Secure

- The PAT is stored only in Power Automate's secure credential store — never in a spreadsheet or email.
- The SharePoint folder should be restricted to the payroll team only.
- The GitHub repository **must remain private** while this integration is in use.
- Rotate the PAT when it expires (set a calendar reminder at creation time).

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Power Automate run fails at HTTP step | PAT expired or wrong permissions | Regenerate PAT; ensure Actions: Read and write is set |
| GitHub Actions run never appears | Wrong `event_type` in the HTTP body | Body must say `"event_type": "brighthr-csv-ready"` exactly |
| Workflow fails: "invalid base64" | CSV content not encoded correctly | Check the Power Automate expression: `base64(body('Get_file_content'))` |
| Workbook artifact not produced | CSV format doesn't match expected columns | Check the workflow run logs; compare CSV headers to the sample file |
| PAT gives 403 forbidden | PAT scoped to wrong repo, or repo is public | Check PAT repository scope; confirm repo is private |
