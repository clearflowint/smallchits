"""
Google Drive Receipt Vault Integration (Blueprint section 9).

Uploads receipt images directly into the authenticated manager's own Google
Drive using the `drive.file` scope — NocoDB stores only lightweight metadata
(Upload_Date, Share_Tag, Drive_View_URL). Zero server binary storage.
"""
import io

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

from app.core.config import get_settings
from app.core.nocodb_client import NocoDBClient, get_nocodb_client
from app.core.security import get_current_manager

router = APIRouter(prefix="/api/drive", tags=["drive"])
settings = get_settings()

RECEIPT_FOLDER_NAME = "ClearFlow Chit Receipts"


def _get_drive_service(access_token: str):
    creds = Credentials(token=access_token)
    return build("drive", "v3", credentials=creds)


async def _get_or_create_receipt_folder(drive_service) -> str:
    query = (
        f"name='{RECEIPT_FOLDER_NAME}' and mimeType='application/vnd.google-apps.folder' "
        "and trashed=false"
    )
    results = drive_service.files().list(q=query, fields="files(id, name)").execute()
    files = results.get("files", [])
    if files:
        return files[0]["id"]

    folder_metadata = {"name": RECEIPT_FOLDER_NAME, "mimeType": "application/vnd.google-apps.folder"}
    folder = drive_service.files().create(body=folder_metadata, fields="id").execute()
    return folder["id"]


@router.post("/upload-receipt")
async def upload_receipt(
    share_id: str,
    access_token: str,  # obtained client-side via Google Identity Services, or from stored refresh token
    file: UploadFile = File(...),
    manager_id: str = Depends(get_current_manager),
    client: NocoDBClient = Depends(get_nocodb_client),
):
    """
    Direct Mobile Camera Upload flow:
    1. Manager snaps/selects a receipt and tags Share_ID.
    2. File is streamed straight into the manager's own Drive (drive.file scope).
    3. NocoDB stores only Upload_Date, Share_Tag, Drive_View_URL.
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(400, "Only image uploads are supported for receipts.")

    try:
        drive_service = _get_drive_service(access_token)
        folder_id = await _get_or_create_receipt_folder(drive_service)

        contents = await file.read()
        media = MediaIoBaseUpload(io.BytesIO(contents), mimetype=file.content_type, resumable=False)
        file_metadata = {"name": f"{share_id}_{file.filename}", "parents": [folder_id]}
        uploaded = drive_service.files().create(
            body=file_metadata, media_body=media, fields="id, webViewLink"
        ).execute()

        # Make it viewable by anyone with the link so the manager can preview from the app
        drive_service.permissions().create(
            fileId=uploaded["id"], body={"role": "reader", "type": "anyone"}
        ).execute()

    except Exception as exc:  # noqa: BLE001 — surfaced to client as a clean 502
        raise HTTPException(502, f"Google Drive upload failed: {exc}") from exc

    view_url = uploaded.get("webViewLink", "")

    # Persist lightweight metadata only — extend your NocoDB schema with a
    # Receipts table (Upload_Date, Share_Tag, Drive_View_URL) if you want this queryable.
    return {
        "status": "uploaded",
        "share_id": share_id,
        "drive_view_url": view_url,
        "drive_file_id": uploaded["id"],
    }
