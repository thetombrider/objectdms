import os
from datetime import datetime
from typing import Optional, BinaryIO
import aioboto3
from fastapi import UploadFile
from ..core.config import settings

class StorageService:
    def __init__(self):
        self.session = aioboto3.Session()
        self.endpoint_url = settings.S3_ENDPOINT_URL
        self.access_key = settings.S3_ACCESS_KEY
        self.secret_key = settings.S3_SECRET_KEY
        self.bucket_name = settings.S3_BUCKET_NAME
        self.region = settings.S3_REGION
    
    async def _get_client(self):
        """Get an S3 client."""
        return self.session.client(
            's3',
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region
        )
    
    def _generate_file_path(self, user_id: str, filename: str) -> str:
        """Generate a unique file path for storage."""
        timestamp = datetime.now().strftime('%Y/%m/%d/%H%M%S')
        _, ext = os.path.splitext(filename)
        return f"documents/{user_id}/{timestamp}{ext}"
    
    async def upload_file(
        self,
        user_id: str,
        file: UploadFile,
        content_type: Optional[str] = None
    ) -> str:
        """
        Upload a file to storage and return its path.
        
        Args:
            user_id: The ID of the user uploading the file
            file: The file to upload
            content_type: The MIME type of the file
        
        Returns:
            str: The path where the file was stored
        """
        file_path = self._generate_file_path(user_id, file.filename)
        
        async with self._get_client() as client:
            await client.upload_fileobj(
                file.file,
                self.bucket_name,
                file_path,
                ExtraArgs={
                    'ContentType': content_type or file.content_type,
                    'ACL': 'private'
                }
            )
        
        return file_path
    
    async def get_file(self, file_path: str) -> BinaryIO:
        """
        Get a file from storage.
        
        Args:
            file_path: The path of the file to retrieve
        
        Returns:
            BinaryIO: The file object
        """
        async with self._get_client() as client:
            response = await client.get_object(
                Bucket=self.bucket_name,
                Key=file_path
            )
            return response['Body']
    
    async def delete_file(self, file_path: str) -> bool:
        """
        Delete a file from storage.
        
        Args:
            file_path: The path of the file to delete
        
        Returns:
            bool: True if deletion was successful
        """
        try:
            async with self._get_client() as client:
                await client.delete_object(
                    Bucket=self.bucket_name,
                    Key=file_path
                )
            return True
        except Exception:
            return False
    
    async def get_presigned_url(
        self,
        file_path: str,
        expires_in: int = 3600,
        operation: str = 'get_object'
    ) -> str:
        """
        Generate a presigned URL for file access.
        
        Args:
            file_path: The path of the file
            expires_in: URL expiration time in seconds
            operation: The S3 operation ('get_object' or 'put_object')
        
        Returns:
            str: The presigned URL
        """
        async with self._get_client() as client:
            url = await client.generate_presigned_url(
                operation,
                Params={
                    'Bucket': self.bucket_name,
                    'Key': file_path
                },
                ExpiresIn=expires_in
            )
            return url

# Global instance
storage = StorageService() 