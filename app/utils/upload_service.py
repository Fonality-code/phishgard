"""
Upload service for handling file uploads
"""
import os
import uuid
from pathlib import Path
from typing import Optional, Tuple
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename
from PIL import Image
import hashlib


class UploadService:
    """Base upload service interface"""

    def upload_file(self, file: FileStorage, folder: str = 'uploads') -> Optional[str]:
        """Upload a file and return the URL"""
        raise NotImplementedError

    def delete_file(self, file_url: str) -> bool:
        """Delete a file by URL"""
        raise NotImplementedError

    def get_file_path(self, file_url: str) -> Optional[str]:
        """Get local file path from URL"""
        raise NotImplementedError


class LocalUploadService(UploadService):
    """Local file system upload service"""

    def __init__(self, upload_folder: str = 'app/static/uploads', base_url: str = '/static/uploads'):
        self.upload_folder = Path(upload_folder)
        self.base_url = base_url
        self.upload_folder.mkdir(parents=True, exist_ok=True)

        # Allowed file extensions
        self.allowed_extensions = {
            'image': {'png', 'jpg', 'jpeg', 'gif', 'webp'},
            'document': {'pdf', 'doc', 'docx', 'txt'},
            'archive': {'zip', 'rar', '7z'}
        }

        # Max file sizes (in bytes)
        self.max_file_sizes = {
            'image': 5 * 1024 * 1024,  # 5MB
            'document': 10 * 1024 * 1024,  # 10MB
            'archive': 50 * 1024 * 1024,  # 50MB
        }

    def _get_file_type(self, filename: str) -> Optional[str]:
        """Determine file type based on extension"""
        extension = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''

        for file_type, extensions in self.allowed_extensions.items():
            if extension in extensions:
                return file_type
        return None

    def _is_allowed_file(self, filename: str) -> bool:
        """Check if file extension is allowed"""
        return self._get_file_type(filename) is not None

    def _generate_unique_filename(self, original_filename: str) -> str:
        """Generate a unique filename while preserving extension"""
        filename = secure_filename(original_filename)
        name, ext = os.path.splitext(filename)
        unique_id = str(uuid.uuid4())
        return f"{unique_id}{ext}"

    def _create_thumbnail(self, image_path: Path, size: Tuple[int, int] = (300, 300)) -> Optional[Path]:
        """Create thumbnail for image files"""
        try:
            with Image.open(image_path) as img:
                # Convert to RGB if necessary (for PNG with transparency)
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')

                # Create thumbnail
                img.thumbnail(size, Image.Resampling.LANCZOS)

                # Save thumbnail
                thumbnail_path = image_path.parent / f"thumb_{image_path.name}"
                img.save(thumbnail_path, 'JPEG', quality=85, optimize=True)
                return thumbnail_path
        except Exception as e:
            print(f"Error creating thumbnail: {e}")
            return None

    def upload_file(self, file: FileStorage, folder: str = 'uploads',
                   create_thumbnail: bool = True) -> Optional[str]:
        """Upload a file to local storage"""
        if not file or not file.filename:
            return None

        if not self._is_allowed_file(file.filename):
            raise ValueError(f"File type not allowed: {file.filename}")

        file_type = self._get_file_type(file.filename)

        # Check file size
        file.seek(0, 2)  # Seek to end
        file_size = file.tell()
        file.seek(0)  # Reset to beginning

        if file_size > self.max_file_sizes.get(file_type, 5 * 1024 * 1024):
            raise ValueError(f"File too large. Maximum size: {self.max_file_sizes.get(file_type, 5 * 1024 * 1024)} bytes")

        # Create folder structure
        upload_path = self.upload_folder / folder
        upload_path.mkdir(parents=True, exist_ok=True)

        # Generate unique filename
        filename = self._generate_unique_filename(file.filename)
        file_path = upload_path / filename

        try:
            # Save file
            file.save(str(file_path))

            # Create thumbnail for images
            if file_type == 'image' and create_thumbnail:
                self._create_thumbnail(file_path)

            # Return URL
            relative_path = file_path.relative_to(self.upload_folder)
            return f"{self.base_url}/{relative_path}".replace('\\', '/')

        except Exception as e:
            # Clean up on error
            if file_path.exists():
                file_path.unlink()
            raise e

    def delete_file(self, file_url: str) -> bool:
        """Delete a file by URL"""
        try:
            # Convert URL to file path
            relative_path = file_url.replace(self.base_url, '').lstrip('/')
            file_path = self.upload_folder / relative_path

            if file_path.exists():
                # Delete main file
                file_path.unlink()

                # Delete thumbnail if exists
                thumbnail_path = file_path.parent / f"thumb_{file_path.name}"
                if thumbnail_path.exists():
                    thumbnail_path.unlink()

                return True
            return False
        except Exception as e:
            print(f"Error deleting file: {e}")
            return False

    def get_file_path(self, file_url: str) -> Optional[str]:
        """Get local file path from URL"""
        try:
            relative_path = file_url.replace(self.base_url, '').lstrip('/')
            file_path = self.upload_folder / relative_path
            return str(file_path) if file_path.exists() else None
        except Exception:
            return None

    def get_thumbnail_url(self, file_url: str) -> Optional[str]:
        """Get thumbnail URL for an image"""
        try:
            relative_path = file_url.replace(self.base_url, '').lstrip('/')
            file_path = self.upload_folder / relative_path
            thumbnail_path = file_path.parent / f"thumb_{file_path.name}"

            if thumbnail_path.exists():
                thumbnail_relative = thumbnail_path.relative_to(self.upload_folder)
                return f"{self.base_url}/{thumbnail_relative}".replace('\\', '/')
            return None
        except Exception:
            return None


class S3UploadService(UploadService):
    """AWS S3 upload service (placeholder for future implementation)"""

    def __init__(self, bucket_name: str, region: str = 'us-east-1'):
        self.bucket_name = bucket_name
        self.region = region
        # TODO: Initialize boto3 client

    def upload_file(self, file: FileStorage, folder: str = 'uploads') -> Optional[str]:
        """Upload file to S3"""
        # TODO: Implement S3 upload
        raise NotImplementedError("S3 upload service not implemented yet")

    def delete_file(self, file_url: str) -> bool:
        """Delete file from S3"""
        # TODO: Implement S3 delete
        raise NotImplementedError("S3 delete service not implemented yet")

    def get_file_path(self, file_url: str) -> Optional[str]:
        """S3 files don't have local paths"""
        return None


class CloudinaryUploadService(UploadService):
    """Cloudinary upload service (placeholder for future implementation)"""

    def __init__(self, cloud_name: str, api_key: str, api_secret: str):
        self.cloud_name = cloud_name
        self.api_key = api_key
        self.api_secret = api_secret
        # TODO: Initialize cloudinary

    def upload_file(self, file: FileStorage, folder: str = 'uploads') -> Optional[str]:
        """Upload file to Cloudinary"""
        # TODO: Implement Cloudinary upload
        raise NotImplementedError("Cloudinary upload service not implemented yet")

    def delete_file(self, file_url: str) -> bool:
        """Delete file from Cloudinary"""
        # TODO: Implement Cloudinary delete
        raise NotImplementedError("Cloudinary delete service not implemented yet")

    def get_file_path(self, file_url: str) -> Optional[str]:
        """Cloudinary files don't have local paths"""
        return None


# Upload service factory
def create_upload_service(service_type: str = 'local', **kwargs) -> UploadService:
    """Create upload service based on configuration"""
    if service_type == 'local':
        return LocalUploadService(**kwargs)
    elif service_type == 's3':
        return S3UploadService(**kwargs)
    elif service_type == 'cloudinary':
        return CloudinaryUploadService(**kwargs)
    else:
        raise ValueError(f"Unknown upload service type: {service_type}")


# Default upload service instance
upload_service = create_upload_service('local')
