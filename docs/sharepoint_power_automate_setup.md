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
 Excel workbook             ← uploaded back to SharePoint via Microsoft Graph API
```

The CSV never enters the GitHub repository.  It travels directly from SharePoint to the workflow runner's temporary storage and is discarded after the run.  The output workbook is also never stored as a public GitHub artifact — it is written directly to a SharePoint document library.

---

## Prerequisites

| What | Where to get it |
|---|---|
| A SharePoint site and document library folder to receive BrightHR exports | Your Microsoft 365 admin |
| A GitHub Personal Access Token (PAT) with **Contents: Read** and **Actions: Write** permissions | [github.com → Settings → Developer settings → Personal access tokens → Fine-grained tokens](https://github.com/settings/personal-access-tokens/new) |
| Access to Power Automate (part of Microsoft 365) | [make.powerautomate.com](https://make.powerautomate.com) |
| An Azure AD app registration (for the output upload — see Step 0 below) | [portal.azure.com](https://portal.azure.com) |

> **PAT scope note:** Create a fine-grained token scoped only to this repository, with *Actions: Read and write* permission. Do not give it broader access.

---

## Step 0 — Register an Azure AD App (for workbook upload to SharePoint)

This step allows GitHub Actions to upload the generated workbook directly into SharePoint using the Microsoft Graph API, so it never needs to be a public GitHub artifact.

### 0a — Create the app registration

1. Go to [portal.azure.com](https://portal.azure.com) → **Azure Active Directory → App registrations → New registration**.
2. Set:
   - **Name:** `brighthr-time-review-uploader`
   - **Supported account types:** Accounts in this organisational directory only (single tenant)
3. Click **Register** and note the **Application (client) ID** and **Directory (tenant) ID** displayed on the overview page.

### 0b — Create a client secret

1. In the app registration, click **Certificates & secrets → New client secret**.
2. Set a description (e.g. `github-actions`) and an expiry (1–2 years).
3. Click **Add** and copy the **Value** immediately — you cannot see it again.

### 0c — Grant API permissions

1. Click **API permissions → Add a permission → Microsoft Graph → Application permissions**.
2. Search for and add **`Files.ReadWrite.All`** (or the narrower `Sites.Selected` if your admin prefers to restrict access to a single site).
3. Click **Grant admin consent** — a Global Administrator must approve this.

> **`Sites.Selected` (recommended for production):** With this permission, access must also be explicitly granted to the specific SharePoint site via the Graph API.  Ask your SharePoint admin to run:  
> `POST https://graph.microsoft.com/v1.0/sites/{site-id}/permissions` with the app's client ID.  See [Microsoft docs](https://learn.microsoft.com/en-us/graph/api/site-post-permissions) for details.

### 0d — Find your SharePoint site ID and drive ID

Use [Graph Explorer](https://developer.microsoft.com/en-us/graph/graph-explorer) (sign in with a Microsoft 365 account that has access to the site):

```
GET https://graph.microsoft.com/v1.0/sites/{hostname}:/sites/{site-path}
```
e.g. `https://graph.microsoft.com/v1.0/sites/contoso.sharepoint.com:/sites/HR`

Note the `id` field — this is your **site ID**.

Then list the document libraries (drives) on that site:
```
GET https://graph.microsoft.com/v1.0/sites/{site-id}/drives
```

Find the library you want to upload into and note its `id` — this is your **drive ID**.

### 0e — Add GitHub repository secrets

Go to **GitHub → this repository → Settings → Secrets and variables → Actions → New repository secret** and add the following:

| Secret name | Value |
|---|---|
| `SHAREPOINT_TENANT_ID` | Directory (tenant) ID from Step 0a |
| `SHAREPOINT_CLIENT_ID` | Application (client) ID from Step 0a |
| `SHAREPOINT_CLIENT_SECRET` | Client secret value from Step 0b |
| `SHAREPOINT_SITE_ID` | Site ID from Step 0d |
| `SHAREPOINT_DRIVE_ID` | Drive ID from Step 0d |
| `SHAREPOINT_FOLDER_PATH` | Destination folder path inside the drive, e.g. `BrightHR Reviews` |

> All six secrets must be present for the upload to work.  If any is missing the workflow will fail with a descriptive error.

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
4. **Open the workbook** from the SharePoint folder configured in `SHAREPOINT_FOLDER_PATH` (the tool uploads it there automatically).
5. **Review the Exception Report** tab.
6. **Correct confirmed issues** in BrightHR and save the workbook as payroll documentation.

---

## Keeping Credentials Secure

- The PAT is stored only in Power Automate's secure credential store — never in a spreadsheet or email.
- The Azure AD client secret is stored only as a GitHub repository secret — never in source code.
- The SharePoint folder should be restricted to the payroll team only.
- The GitHub repository **must remain private** while this integration is in use.
- Rotate the PAT and the Azure AD client secret when they expire (set calendar reminders at creation time).

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Power Automate run fails at HTTP step | PAT expired or wrong permissions | Regenerate PAT; ensure Actions: Read and write is set |
| GitHub Actions run never appears | Wrong `event_type` in the HTTP body | Body must say `"event_type": "brighthr-csv-ready"` exactly |
| Workflow fails: "invalid base64" | CSV content not encoded correctly | Check the Power Automate expression: `base64(body('Get_file_content'))` |
| Workbook not uploaded to SharePoint | CSV format doesn't match expected columns, or `SHAREPOINT_*` secrets missing | Check the workflow run logs; verify all six secrets are set |
| Workflow fails: "Required environment variable … is not set" | One or more `SHAREPOINT_*` secrets not configured | Add the missing secret in GitHub → Settings → Secrets → Actions |
| Workflow fails: "MSAL failed to acquire a token" | Client secret expired or wrong tenant/client ID | Rotate the client secret in Azure AD; update `SHAREPOINT_CLIENT_SECRET` |
| Workflow fails: "Graph API upload failed — HTTP 403" | App lacks Files.ReadWrite.All permission, or admin consent not granted | Re-check API permissions in Azure AD and ensure admin consent is granted |
| Workflow fails: "Graph API upload failed — HTTP 404" | Wrong site ID, drive ID, or folder path | Verify IDs using Graph Explorer; check `SHAREPOINT_FOLDER_PATH` exists in the library |
| PAT gives 403 forbidden | PAT scoped to wrong repo, or repo is public | Check PAT repository scope; confirm repo is private |
