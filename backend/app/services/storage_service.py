import os
import uuid
import shutil
from pathlib import Path
from fastapi import UploadFile, HTTPException, status
from PIL import Image, UnidentifiedImageError
import io

from app.core.config import settings

ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
MAX_SIZE_BYTES = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024

class StorageService:
    def __init__(self):
        self.storage_base = Path(settings.STORAGE_PATH)
        self.uploads_dir = self.storage_base / "uploads"
        self.evidence_dir = self.storage_base / "evidence"
        self.reports_dir = self.storage_base / "reports"
        
        # Ensure directories exist
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    async def save_upload(self, file: UploadFile) -> tuple[str, str, str]:
        """
        Validates and saves an uploaded image.
        Returns: (file_path_str, filename, content_type)
        """
        # 1. Check empty file
        file.file.seek(0, 2) # go to end
        size = file.file.tell()
        file.file.seek(0) # reset to start
        
        if size == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Empty file uploaded"
            )

        # 2. Check file size
        if size > MAX_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File exceeds maximum size of {settings.MAX_UPLOAD_SIZE_MB}MB"
            )

        # 3. Validate image content
        try:
            content = await file.read()
            img = Image.open(io.BytesIO(content))
            img.verify()  # Verify it's actually an image
            
            if img.format not in ALLOWED_FORMATS:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unsupported image format: {img.format}. Allowed: {', '.join(ALLOWED_FORMATS)}"
                )
            
            # Reset file pointer after reading
            file.file.seek(0)
        except UnidentifiedImageError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid image file"
            )
        except Exception as e:
            if isinstance(e, HTTPException):
                raise
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not process image"
            )

        # 4. Generate safe unique filename
        ext = ".jpg" # Default
        if img.format == "PNG": ext = ".png"
        elif img.format == "WEBP": ext = ".webp"
            
        filename = f"{uuid.uuid4()}{ext}"
        save_path = self.uploads_dir / filename

        # 5. Save file
        try:
            with open(save_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save image"
            )
            
        # img.format is already validated, but type-checkers need safety
        format_str = img.format if img.format else "JPEG"
        content_type = f"image/{format_str.lower()}"
        return str(save_path), filename, content_type

    def get_upload_path(self, filename: str) -> Path:
        """Securely get path for a filename, preventing path traversal."""
        # Clean filename to just the name itself
        clean_name = os.path.basename(filename)
        path = self.uploads_dir / clean_name
        
        if not path.exists() or not path.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Image not found"
            )
            
        return path

    def delete_file(self, file_path: str):
        """Clean up a file (e.g. if DB transaction fails)"""
        path = Path(file_path)
        if path.exists() and path.is_file():
            try:
                path.unlink()
            except:
                pass # Best effort cleanup

storage_service = StorageService()
