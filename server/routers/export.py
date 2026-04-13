import os
import shutil
from pathlib import Path
from tempfile import NamedTemporaryFile
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter()

@router.get("/")
def export_tlcm():
    """
    Creates a Universal .tlcm Backup Format.
    Zips the SQLite database and ChromaDB vectors into a single portable payload.
    This fulfills the 'Export your mind' requirement, maintaining privacy parity.
    """
    try:
        data_dir = Path(__file__).parent.parent.parent / "data"
        if not data_dir.exists():
            raise HTTPException(status_code=404, detail="No data directory found to export.")

        # Create a temporary file for the zip archive
        # Ensure it is deleted after sending (using background tasks in production, but FileResponse handles local cleanups if configured, or we let OS clean tmp)
        import tempfile
        tmp_dir = tempfile.gettempdir()
        archive_name = os.path.join(tmp_dir, "mind_backup")
        
        # Create Zip archive
        shutil.make_archive(archive_name, 'zip', root_dir=data_dir)
        zip_path = archive_name + ".zip"

        # Rename to .tlcm extension logic could be applied client side or via filename
        return FileResponse(
            path=zip_path,
            filename="my_mind.tlcm",
            media_type="application/zip"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
