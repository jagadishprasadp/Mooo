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
.\venv\Scripts\python.exe -m streamlit run app.py --server.port 8502
```

Open http://localhost:8502. The database is created automatically when the app first runs.

## Run with Docker

Build the image:

```powershell
docker build -t mooo-app .
```

Run the app:

```powershell
docker run --name mooo-app -p 8501:8501 mooo-app
```

Open http://localhost:8501. To preserve the SQLite database across container removal, mount the database file:

```powershell
docker run --name mooo-app -p 8501:8501 -v "${PWD}\notes.db:/app/notes.db" -v "${PWD}\media:/app/media" mooo-app
```

## Deploy publicly

1. Commit and push the project to GitHub.
2. Open https://share.streamlit.io/.
3. Choose `jagadishprasadp/Mooo`, branch `main`, and file `app.py`.
4. Click **Deploy**.

Streamlit Cloud will provide a public URL that you can send to your partner.
