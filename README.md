# A note for you

A small Streamlit app for writing and sharing a heartfelt note with your partner.

Notes are stored in the local SQLite file `notes.db`, and uploaded images/videos are stored in the `media` folder. The app shows saved notes under **Saved notes on this device**, and **Delete note** removes the selected note and its media. On Streamlit Cloud, local files can reset when the app restarts, so use this deployment for sharing the experience rather than permanent cloud storage.

## Azure Blob Storage

To keep uploaded media after deployment, create a private Azure Blob container and configure these secrets:

```text
AZURE_STORAGE_CONNECTION_STRING=your Azure connection string
AZURE_STORAGE_CONTAINER=mooo-media
```

The app uploads media to Azure when both values are configured. It keeps a temporary local cache only for displaying media. Add the values in Streamlit Cloud under **App settings > Secrets**, or set them as environment variables on your server. Never commit the connection string to GitHub.

## Run locally

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe main.py
```

Open http://localhost:8501. The database is created automatically when the app first runs.

## Run with Docker

Build the image:

```powershell
docker build -t mooo-app .
```

Run the app:

```powershell
docker run --name mooo-app -p 8501:8501 mooo-app
```

The container starts with `python main.py`, which launches Streamlit on port 8501.

Open http://localhost:8501. To preserve the SQLite database across container removal, mount the database file:

```powershell
docker run --name mooo-app -p 8501:8501 -v "${PWD}\notes.db:/app/notes.db" -v "${PWD}\media:/app/media" mooo-app
```

## Deploy to Azure App Service with Key Vault

Azure App Service runs the existing Docker image. Azure Key Vault stores the SQL password and Blob Storage connection string; App Service injects them as environment variables through Key Vault references. Keep App Service, Azure SQL, Blob Storage, and Key Vault in the same region.

Set these PowerShell variables first:

```powershell
$RG = "mooo-rg"
$LOCATION = "centralindia"
$ACR = "moooregistry2026"
$PLAN = "mooo-plan"
$APP = "mooo-web"
$KV = "mooo-vault-2026"
```

Create the resource group, registry, App Service plan, and Key Vault:

```powershell
az group create --name $RG --location $LOCATION
az acr create --resource-group $RG --name $ACR --sku Basic --admin-enabled true
az appservice plan create --name $PLAN --resource-group $RG --location $LOCATION --is-linux --sku B1
az keyvault create --name $KV --resource-group $RG --location $LOCATION --enable-rbac-authorization true
az acr login --name $ACR
```

Build and push the image:

```powershell
docker build -t "$ACR.azurecr.io/mooo:latest" .
docker push "$ACR.azurecr.io/mooo:latest"
```

Create the App Service with the container. The registry credentials are used only during initial setup; the app is switched to managed identity immediately afterward:

```powershell
az webapp create `
	--name $APP `
	--resource-group $RG `
	--plan $PLAN `
	--deployment-container-image-name "$ACR.azurecr.io/mooo:latest" `
	--docker-registry-server-url "https://$ACR.azurecr.io" `
	--docker-registry-server-user "<acr-admin-username>" `
	--docker-registry-server-password "<acr-admin-password>"
```

Enable a system-assigned identity and grant it access to ACR and Key Vault:

```powershell
$WEB_PRINCIPAL_ID = az webapp identity assign --name $APP --resource-group $RG --query principalId --output tsv
$ACR_ID = az acr show --name $ACR --resource-group $RG --query id --output tsv
$KV_ID = az keyvault show --name $KV --resource-group $RG --query id --output tsv

az role assignment create --assignee $WEB_PRINCIPAL_ID --role AcrPull --scope $ACR_ID
az role assignment create --assignee $WEB_PRINCIPAL_ID --role "Key Vault Secrets User" --scope $KV_ID
az webapp config set --name $APP --resource-group $RG --generic-configurations '{"acrUseManagedIdentityCreds":true}'
```

Create Key Vault secrets. Replace the placeholders locally and never commit these values:

```powershell
az keyvault secret set --vault-name $KV --name azure-sql-password --value "<your-sql-password>"
az keyvault secret set --vault-name $KV --name azure-storage-connection --value "<your-storage-connection-string>"
```

Configure App Service settings. Key Vault references are resolved at runtime:

```powershell
az webapp config appsettings set `
	--name $APP `
	--resource-group $RG `
	--settings `
		WEBSITES_PORT=8501 `
		STREAMLIT_SERVER_PORT=8501 `
		AZURE_SQL_SERVER="moo-server-2026.database.windows.net" `
		AZURE_SQL_DATABASE="<database-name>" `
		AZURE_SQL_USER="<database-user>" `
		AZURE_SQL_PASSWORD="@Microsoft.KeyVault(VaultName=$KV;SecretName=azure-sql-password)" `
		AZURE_STORAGE_CONNECTION_STRING="@Microsoft.KeyVault(VaultName=$KV;SecretName=azure-storage-connection)" `
		AZURE_STORAGE_CONTAINER="mooo-media"
```

Restart and open the site:

```powershell
az webapp restart --name $APP --resource-group $RG
az webapp show --name $APP --resource-group $RG --query defaultHostName --output tsv
```

Open `https://<returned-hostname>`. Add the App Service outbound IP addresses to the Azure SQL firewall:

```powershell
az webapp show --name $APP --resource-group $RG --query outboundIpAddresses --output tsv
```

For future releases, build and push a new image with the same tag, then restart the App Service. Do not put SQL passwords, Blob connection strings, or Key Vault values in GitHub.

## GitHub Actions deployment

The workflow at `.github/workflows/deploy.yml` deploys every push to `main`:

```text
GitHub Actions -> Azure Container Registry -> Azure App Service
```

Create an Azure Entra application/service principal and configure a federated credential for this GitHub repository and the `main` branch. Grant the service principal `Contributor` on the App Service resource group and `AcrPush` on the registry. Add these GitHub repository secrets under **Settings > Secrets and variables > Actions**:

```text
AZURE_CLIENT_ID
AZURE_TENANT_ID
AZURE_SUBSCRIPTION_ID
AZURE_ACR_NAME
REGISTRY_LOGIN_SERVER
AZURE_WEBAPP_NAME
```

`REGISTRY_LOGIN_SERVER` must be copied from **Container Registry > Overview > Login server**, including any generated suffix. `AZURE_ACR_NAME` is the registry resource name, such as `mooregistry2026`. `AZURE_WEBAPP_NAME` is the App Service name.

The App Service must already have its system-assigned identity configured with `AcrPull`, and its SQL/Blob settings must use the Key Vault references described above. The workflow does not store or deploy application secrets.
