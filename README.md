# Mooo

Mooo is a private Streamlit space for two partners to share love notes, replies, images, videos, and memories.

## Features

- Account registration and password-based sign-in.
- The first registered account becomes an administrator.
- Persistent sign-in across browser refreshes using a random browser cookie and a hashed server-side session token.
- Sessions expire after 30 days and are removed when the user signs out.
- Love notes with preset feelings or a custom feeling typed directly into the editable dropdown.
- Optional image or video attachments on notes.
- Replies on notes, with delete controls for note owners/admin workflows already present in the UI.
- Memories gallery for images and videos, including duplicate-content detection.
- Image thumbnails and paginated memories.
- Admin panel for:
  - Uploading or replacing the Memories page background.
  - Removing the custom background and restoring the built-in love illustration.
  - Resetting another user's password.
  - Viewing registered users.
  - Deleting users while preventing deletion of the final administrator.
- Streamlit toolbar hidden in the app UI; sign out is available on the main page and in the sidebar.

## Storage model

The app selects its database backend from environment variables:

- If all four `AZURE_SQL_*` settings are present, it uses Azure SQL.
- Otherwise, it uses SQLite at `notes.db` in the project root.

Media files are written to the local `media` directory as a cache. When Azure Blob Storage is configured, uploads are also stored in the configured Blob container and can be restored after an App Service restart or redeployment.

The admin-managed Memories background is stored as `memories-background.jpg`. New uploads replace the existing background. Removing it deletes the custom object and returns to the built-in background.

For production, configure both Azure SQL and Blob Storage. App Service local files are not a reliable permanent data store.

## Configuration

### Azure SQL settings

```text
AZURE_SQL_SERVER=moo-server-2026.database.windows.net
AZURE_SQL_DATABASE=moo-db
AZURE_SQL_USER=your-database-user
AZURE_SQL_PASSWORD=your-database-password
```

### Azure Blob Storage settings

```text
AZURE_STORAGE_CONNECTION_STRING=your-storage-connection-string
AZURE_STORAGE_CONTAINER=mooo-media
```

When both Blob settings are present, the app creates the container if necessary and stores uploaded media and the custom Memories background there. Keep the container private.

Never commit passwords, connection strings, cookies, or Key Vault values to GitHub.

## Run locally

Create or activate a virtual environment, then install dependencies:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Start the app:

```powershell
python main.py
```

Open `http://localhost:8501`.

### Local SQLite mode

For local-only development, remove the Azure SQL variables from the current PowerShell session before starting Streamlit:

```powershell
Remove-Item Env:AZURE_SQL_SERVER, Env:AZURE_SQL_DATABASE, Env:AZURE_SQL_USER, Env:AZURE_SQL_PASSWORD -ErrorAction SilentlyContinue
python main.py
```

SQLite tables are created automatically. This mode uses local `notes.db`. Configure Blob settings separately if local uploads should be shared with Azure.

### Local Azure mode

To use the same Azure SQL and Blob Storage as App Service, set the configuration variables in the local environment or in Streamlit secrets. The local public IP must be allowed by the Azure SQL firewall.

## Run with Docker

Build and run:

```powershell
docker build -t mooo-app .
docker run --name mooo-app -p 8501:8501 mooo-app
```

The image starts `python main.py`, which launches Streamlit on `0.0.0.0:8501`.

For local SQLite and media persistence across container replacement, mount both paths:

```powershell
docker run --name mooo-app -p 8501:8501 `
  -v "${PWD}\notes.db:/app/notes.db" `
  -v "${PWD}\media:/app/media" `
  mooo-app
```

For production containers, use Azure SQL and Azure Blob Storage instead of relying on mounted local files.

## Azure App Service deployment

The Docker image is built in GitHub Actions, pushed to Azure Container Registry, and deployed to Linux App Service.

Use a Linux App Service plan that supports custom containers. Basic B1 or higher is recommended for this app. Keep App Service, Azure SQL, Blob Storage, Key Vault, and ACR in the same region where practical.

### Required App Service settings

Add these under **App Service > Configuration > Environment variables > App settings**:

```text
WEBSITES_PORT=8501
STREAMLIT_SERVER_PORT=8501
AZURE_SQL_SERVER=moo-server-2026.database.windows.net
AZURE_SQL_DATABASE=moo-db
AZURE_SQL_USER=your-database-user
AZURE_SQL_PASSWORD=@Microsoft.KeyVault(VaultName=mooo-vault-2026;SecretName=azure-sql-password)
AZURE_STORAGE_CONNECTION_STRING=@Microsoft.KeyVault(VaultName=mooo-vault-2026;SecretName=azure-storage-connection)
AZURE_STORAGE_CONTAINER=mooo-media
```

`WEBSITES_PORT` tells App Service which container port to route to. `STREAMLIT_SERVER_PORT` keeps Streamlit on the same port.

### ACR managed identity

Do not configure App Service Deployment Center with disabled ACR admin credentials. Use managed identity:

1. App Service > **Identity** > turn on **System assigned** and save.
2. ACR > **Access control (IAM)** > add role assignment.
3. Assign **AcrPull** to the `moo-web-2026` App Service identity.
4. App Service > **Configuration** > set `acrUseManagedIdentityCreds` to `true` if required by the portal.
5. Deployment Center > choose **Azure Container Registry** and **Managed Identity**.

The GitHub Actions identity needs `AcrPush` on the registry and permission to deploy to the App Service resource group.

### Azure SQL networking

Azure SQL must allow traffic from both local development and App Service:

- Add your current public IP for local testing.
- Add all App Service outbound IPv4 addresses for direct App Service connectivity.
- For a stable outbound address, integrate App Service with a VNet subnet attached to a NAT Gateway with a static public IP, then allow only that NAT IP in the SQL firewall.
- Keep NSG rules permissive enough for outbound TCP `1433` to Azure SQL and HTTPS `443` to Azure services and ACR. An NSG is optional.

If Azure SQL uses the Serverless tier, it can pause and return error `40613`. Provisioned compute avoids auto-pause latency but costs more. Error `40615` means the connecting IP is not allowed by the SQL firewall.

### First deployment with Azure CLI

Example resource variables:

```powershell
$RG = "moo-rg"
$LOCATION = "centralindia"
$ACR = "mooregistry2026"
$PLAN = "mooo-plan"
$APP = "moo-web-2026"
$KV = "mooo-vault-2026"
```

Create the main resources:

```powershell
az group create --name $RG --location $LOCATION
az acr create --resource-group $RG --name $ACR --sku Basic
az appservice plan create --name $PLAN --resource-group $RG --location $LOCATION --is-linux --sku B1
az keyvault create --name $KV --resource-group $RG --location $LOCATION --enable-rbac-authorization true
```

Build and push an initial image from a machine with Docker:

```powershell
az acr login --name $ACR
docker build -t "$ACR.azurecr.io/mooo:latest" .
docker push "$ACR.azurecr.io/mooo:latest"
```

After creating the App Service, configure its system identity and grant `AcrPull` and Key Vault access as described above. Use Key Vault references for SQL and Blob secrets rather than storing secret values in GitHub.

## GitHub Actions deployment

The workflow at `.github/workflows/deploy.yml` runs on pushes to `main` and can also be started manually. It:

1. Checks out the repository.
2. Signs in to Azure with OIDC.
3. Logs in to ACR.
4. Builds the Docker image.
5. Pushes both the commit SHA tag and `latest`.
6. Deploys the immutable commit SHA image to App Service.

Configure these GitHub repository secrets:

```text
AZURE_CLIENT_ID
AZURE_TENANT_ID
AZURE_SUBSCRIPTION_ID
AZURE_ACR_NAME
REGISTRY_LOGIN_SERVER
AZURE_WEBAPP_NAME
```

`REGISTRY_LOGIN_SERVER` must be the exact ACR login server from the registry Overview page, including any generated suffix. `AZURE_ACR_NAME` is the registry resource name, such as `mooregistry2026`. `AZURE_WEBAPP_NAME` is the App Service name.

After a green workflow run, restart the App Service if necessary and inspect **Monitoring > Log stream**. A `ModuleNotFoundError` usually means the Dockerfile did not copy a package or the image was not redeployed. A 503 usually means the container did not start, could not be pulled, or failed its port/health check.

## Troubleshooting

### `ModuleNotFoundError: No module named 'ui'`

Ensure the Dockerfile contains:

```dockerfile
COPY ui ./ui
```

Push a new commit and confirm the GitHub Actions deployment uses the new image SHA.

### Azure SQL `40613`

The database is paused or temporarily unavailable, commonly because it is Serverless. Resume it, wait for status `Online`, or use a Provisioned compute tier.

### Azure SQL `40615`

The client IP is blocked. Add the local public IP, App Service outbound IPs, or NAT Gateway static IP to SQL server Networking > Firewall rules.

### App Service 503

Check, in order:

1. Deployment Center image deployment status.
2. ACR `AcrPull` permission for the App Service managed identity.
3. `WEBSITES_PORT=8501` and `STREAMLIT_SERVER_PORT=8501`.
4. Azure SQL status and firewall rules.
5. App Service Log stream immediately after restart.

### `ModuleNotFoundError: No module named 'streamlit_cookies_controller'`

The persistent-login dependency is declared in `requirements.txt`. Reinstall dependencies in the active virtual environment:

```powershell
python -m pip install -r requirements.txt
```

Restart Streamlit after installation. The Docker image installs the same requirements during its build.

## Current limitations

- The app has account authentication, but post visibility and per-user permissions are not yet modeled separately. Authenticated users currently share the app's feed according to the existing repository behavior.
- App Service local cache files are disposable; durable media requires Azure Blob Storage.
- A failed upload during a database or Blob outage can fail the current operation. Successfully stored Blob objects remain durable.
- The app does not send password-reset email. An administrator resets another user's password from the Admin panel.
