"""
S3/MinIO storage manager with multipart upload support.

Provides comprehensive storage management including multipart uploads,
resumable transfers, metadata handling, and distributed file operations.
"""

import asyncio
import hashlib
import logging
import mimetypes
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

import aiofiles
import aioboto3
from botocore.exceptions import ClientError, NoCredentialsError
from pydantic import BaseModel, Field

from app.core.config import get_settings


logger = logging.getLogger(__name__)
settings = get_settings()


class UploadPart(BaseModel):
    """Represents a part in a multipart upload."""
    part_number: int = Field(..., ge=1, le=10000)
    etag: str
    size: int = Field(..., ge=0)
    checksum: Optional[str] = None


class MultipartUpload(BaseModel):
    """Multipart upload session information."""
    upload_id: str
    key: str
    bucket: str
    parts: List[UploadPart] = Field(default_factory=list)
    total_size: int = 0
    uploaded_size: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime
    metadata: Dict[str, str] = Field(default_factory=dict)

    @property
    def progress_percentage(self) -> float:
        """Calculate upload progress percentage."""
        if self.total_size == 0:
            return 0.0
        return (self.uploaded_size / self.total_size) * 100.0

    @property
    def is_complete(self) -> bool:
        """Check if upload is complete."""
        return self.uploaded_size >= self.total_size and len(self.parts) > 0


class StorageMetrics(BaseModel):
    """Storage system metrics."""
    total_uploads: int = 0
    active_multipart_uploads: int = 0
    total_bytes_uploaded: int = 0
    total_bytes_downloaded: int = 0
    average_upload_speed_mbps: float = 0.0
    average_download_speed_mbps: float = 0.0
    storage_quota_used_percentage: float = 0.0
    failed_uploads: int = 0
    resumed_uploads: int = 0


class S3StorageManager:
    """
    Advanced S3/MinIO storage manager with multipart upload support.
    
    Features:
    - Multipart uploads with resume capability
    - Chunked transfers for large files
    - Metadata management
    - Progress tracking
    - Error handling and retry mechanisms
    - Distributed processing support
    """

    def __init__(
        self,
        endpoint_url: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        bucket_name: Optional[str] = None,
        use_ssl: Optional[bool] = None,
        region_name: str = "us-east-1"
    ):
        """
        Initialize S3 storage manager.
        
        Args:
            endpoint_url: S3/MinIO endpoint URL
            access_key: Access key ID
            secret_key: Secret access key
            bucket_name: Default bucket name
            use_ssl: Whether to use SSL/TLS
            region_name: AWS region name
        """
        self.endpoint_url = endpoint_url or settings.MINIO_ENDPOINT
        self.access_key = access_key or settings.MINIO_ACCESS_KEY
        self.secret_key = secret_key or settings.MINIO_SECRET_KEY
        self.bucket_name = bucket_name or settings.MINIO_BUCKET_NAME
        self.use_ssl = use_ssl if use_ssl is not None else settings.MINIO_USE_SSL
        self.region_name = region_name
        
        # Configuration
        self.chunk_size = 8 * 1024 * 1024  # 8MB chunks
        self.max_concurrent_parts = 4
        self.multipart_threshold = 100 * 1024 * 1024  # 100MB
        self.max_retries = 3
        self.retry_delay = 1.0
        
        # Runtime state
        self.active_uploads: Dict[str, MultipartUpload] = {}
        self.metrics = StorageMetrics()
        self.session: Optional[aioboto3.Session] = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the storage manager and create bucket if needed."""
        if self._initialized:
            return
            
        logger.info("Initializing S3 storage manager")
        
        try:
            # Create aioboto3 session
            self.session = aioboto3.Session()
            
            # Test connection and create bucket if needed
            async with self._get_client() as client:
                await self._ensure_bucket_exists(client)
                
            self._initialized = True
            logger.info("S3 storage manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize S3 storage manager: {e}")
            raise

    async def shutdown(self) -> None:
        """Cleanup resources and abort pending uploads."""
        logger.info("Shutting down S3 storage manager")
        
        try:
            # Abort active multipart uploads
            async with self._get_client() as client:
                for upload in self.active_uploads.values():
                    try:
                        await client.abort_multipart_upload(
                            Bucket=upload.bucket,
                            Key=upload.key,
                            UploadId=upload.upload_id
                        )
                        logger.info(f"Aborted multipart upload {upload.upload_id}")
                    except Exception as e:
                        logger.warning(f"Failed to abort upload {upload.upload_id}: {e}")
            
            self.active_uploads.clear()
            self._initialized = False
            
        except Exception as e:
            logger.error(f"Error during S3 storage manager shutdown: {e}")

    async def upload_file(
        self,
        file_path: str,
        key: str,
        bucket: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        content_type: Optional[str] = None,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Upload a file to S3 with automatic multipart handling.
        
        Args:
            file_path: Local file path to upload
            key: S3 object key
            bucket: Bucket name (uses default if not specified)
            metadata: Custom metadata to attach
            content_type: MIME type of the file
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dict containing upload result information
        """
        bucket = bucket or self.bucket_name
        file_path_obj = Path(file_path)
        
        if not file_path_obj.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        file_size = file_path_obj.stat().st_size
        content_type = content_type or mimetypes.guess_type(file_path)[0] or "application/octet-stream"
        
        logger.info(f"Uploading file {file_path} to s3://{bucket}/{key} ({file_size} bytes)")
        
        start_time = datetime.utcnow()
        
        try:
            if file_size >= self.multipart_threshold:
                # Use multipart upload for large files
                result = await self._multipart_upload(
                    file_path=file_path,
                    key=key,
                    bucket=bucket,
                    metadata=metadata,
                    content_type=content_type,
                    progress_callback=progress_callback
                )
            else:
                # Use simple upload for small files
                result = await self._simple_upload(
                    file_path=file_path,
                    key=key,
                    bucket=bucket,
                    metadata=metadata,
                    content_type=content_type,
                    progress_callback=progress_callback
                )
            
            # Update metrics
            upload_time = (datetime.utcnow() - start_time).total_seconds()
            speed_mbps = (file_size / (1024 * 1024)) / max(upload_time, 0.001)
            
            self.metrics.total_uploads += 1
            self.metrics.total_bytes_uploaded += file_size
            self._update_average_speed(speed_mbps, is_upload=True)
            
            logger.info(f"Successfully uploaded {file_path} in {upload_time:.2f}s ({speed_mbps:.2f} MB/s)")
            
            return {
                "key": key,
                "bucket": bucket,
                "size": file_size,
                "etag": result.get("ETag", "").strip('"'),
                "upload_time": upload_time,
                "speed_mbps": speed_mbps,
                "multipart": file_size >= self.multipart_threshold
            }
            
        except Exception as e:
            self.metrics.failed_uploads += 1
            logger.error(f"Failed to upload {file_path}: {e}")
            raise

    async def download_file(
        self,
        key: str,
        file_path: str,
        bucket: Optional[str] = None,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Download a file from S3 with chunked transfer.
        
        Args:
            key: S3 object key
            file_path: Local file path to save to
            bucket: Bucket name (uses default if not specified)
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dict containing download result information
        """
        bucket = bucket or self.bucket_name
        
        logger.info(f"Downloading s3://{bucket}/{key} to {file_path}")
        
        start_time = datetime.utcnow()
        
        try:
            async with self._get_client() as client:
                # Get object metadata
                response = await client.head_object(Bucket=bucket, Key=key)
                file_size = response["ContentLength"]
                
                # Download with chunked transfer
                downloaded_size = 0
                
                async with aiofiles.open(file_path, "wb") as f:
                    async with client.get_object(Bucket=bucket, Key=key) as response:
                        async for chunk in response["Body"].iter_chunks(chunk_size=self.chunk_size):
                            await f.write(chunk)
                            downloaded_size += len(chunk)
                            
                            # Report progress
                            if progress_callback:
                                progress = (downloaded_size / file_size) * 100.0
                                await progress_callback(progress, downloaded_size, file_size)
                
                # Update metrics
                download_time = (datetime.utcnow() - start_time).total_seconds()
                speed_mbps = (file_size / (1024 * 1024)) / max(download_time, 0.001)
                
                self.metrics.total_bytes_downloaded += file_size
                self._update_average_speed(speed_mbps, is_upload=False)
                
                logger.info(f"Successfully downloaded {key} in {download_time:.2f}s ({speed_mbps:.2f} MB/s)")
                
                return {
                    "key": key,
                    "bucket": bucket,
                    "size": file_size,
                    "download_time": download_time,
                    "speed_mbps": speed_mbps
                }
                
        except Exception as e:
            logger.error(f"Failed to download {key}: {e}")
            raise

    async def start_multipart_upload(
        self,
        key: str,
        total_size: int,
        bucket: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        content_type: str = "application/octet-stream"
    ) -> str:
        """
        Start a multipart upload session.
        
        Args:
            key: S3 object key
            total_size: Total size of the file
            bucket: Bucket name
            metadata: Custom metadata
            content_type: MIME type
            
        Returns:
            str: Upload ID for the multipart session
        """
        bucket = bucket or self.bucket_name
        
        logger.info(f"Starting multipart upload for s3://{bucket}/{key} ({total_size} bytes)")
        
        try:
            async with self._get_client() as client:
                response = await client.create_multipart_upload(
                    Bucket=bucket,
                    Key=key,
                    ContentType=content_type,
                    Metadata=metadata or {}
                )
                
                upload_id = response["UploadId"]
                
                # Store upload session
                upload_session = MultipartUpload(
                    upload_id=upload_id,
                    key=key,
                    bucket=bucket,
                    total_size=total_size,
                    expires_at=datetime.utcnow() + timedelta(days=7),  # S3 default
                    metadata=metadata or {}
                )
                
                self.active_uploads[upload_id] = upload_session
                self.metrics.active_multipart_uploads += 1
                
                logger.info(f"Started multipart upload {upload_id}")
                return upload_id
                
        except Exception as e:
            logger.error(f"Failed to start multipart upload: {e}")
            raise

    async def upload_part(
        self,
        upload_id: str,
        part_number: int,
        data: bytes
    ) -> UploadPart:
        """
        Upload a single part in a multipart upload.
        
        Args:
            upload_id: Multipart upload ID
            part_number: Part number (1-based)
            data: Part data
            
        Returns:
            UploadPart: Information about the uploaded part
        """
        if upload_id not in self.active_uploads:
            raise ValueError(f"Unknown upload ID: {upload_id}")
        
        upload_session = self.active_uploads[upload_id]
        
        logger.debug(f"Uploading part {part_number} for upload {upload_id} ({len(data)} bytes)")
        
        try:
            async with self._get_client() as client:
                response = await client.upload_part(
                    Bucket=upload_session.bucket,
                    Key=upload_session.key,
                    PartNumber=part_number,
                    UploadId=upload_id,
                    Body=data
                )
                
                # Create upload part record
                part = UploadPart(
                    part_number=part_number,
                    etag=response["ETag"].strip('"'),
                    size=len(data),
                    checksum=hashlib.md5(data).hexdigest()
                )
                
                # Update upload session
                upload_session.parts.append(part)
                upload_session.uploaded_size += len(data)
                
                logger.debug(f"Uploaded part {part_number} with ETag {part.etag}")
                return part
                
        except Exception as e:
            logger.error(f"Failed to upload part {part_number}: {e}")
            raise

    async def complete_multipart_upload(self, upload_id: str) -> Dict[str, Any]:
        """
        Complete a multipart upload.
        
        Args:
            upload_id: Multipart upload ID
            
        Returns:
            Dict containing completion result
        """
        if upload_id not in self.active_uploads:
            raise ValueError(f"Unknown upload ID: {upload_id}")
        
        upload_session = self.active_uploads[upload_id]
        
        logger.info(f"Completing multipart upload {upload_id}")
        
        try:
            # Sort parts by part number
            parts = sorted(upload_session.parts, key=lambda p: p.part_number)
            
            # Prepare parts list for completion
            multipart_upload = {
                "Parts": [
                    {
                        "ETag": part.etag,
                        "PartNumber": part.part_number
                    }
                    for part in parts
                ]
            }
            
            async with self._get_client() as client:
                response = await client.complete_multipart_upload(
                    Bucket=upload_session.bucket,
                    Key=upload_session.key,
                    UploadId=upload_id,
                    MultipartUpload=multipart_upload
                )
                
                # Clean up
                del self.active_uploads[upload_id]
                self.metrics.active_multipart_uploads -= 1
                
                logger.info(f"Completed multipart upload {upload_id}")
                
                return {
                    "key": upload_session.key,
                    "bucket": upload_session.bucket,
                    "etag": response["ETag"].strip('"'),
                    "location": response.get("Location"),
                    "total_size": upload_session.total_size,
                    "parts_count": len(parts)
                }
                
        except Exception as e:
            logger.error(f"Failed to complete multipart upload {upload_id}: {e}")
            raise

    async def abort_multipart_upload(self, upload_id: str) -> None:
        """
        Abort a multipart upload and clean up.
        
        Args:
            upload_id: Multipart upload ID
        """
        if upload_id not in self.active_uploads:
            logger.warning(f"Unknown upload ID for abort: {upload_id}")
            return
        
        upload_session = self.active_uploads[upload_id]
        
        logger.info(f"Aborting multipart upload {upload_id}")
        
        try:
            async with self._get_client() as client:
                await client.abort_multipart_upload(
                    Bucket=upload_session.bucket,
                    Key=upload_session.key,
                    UploadId=upload_id
                )
                
                # Clean up
                del self.active_uploads[upload_id]
                self.metrics.active_multipart_uploads -= 1
                
                logger.info(f"Aborted multipart upload {upload_id}")
                
        except Exception as e:
            logger.error(f"Failed to abort multipart upload {upload_id}: {e}")
            raise

    async def list_multipart_uploads(self, bucket: Optional[str] = None) -> List[Dict[str, Any]]:
        """List active multipart uploads."""
        bucket = bucket or self.bucket_name
        
        try:
            async with self._get_client() as client:
                response = await client.list_multipart_uploads(Bucket=bucket)
                
                uploads = []
                for upload in response.get("Uploads", []):
                    uploads.append({
                        "key": upload["Key"],
                        "upload_id": upload["UploadId"],
                        "initiated": upload["Initiated"],
                        "storage_class": upload.get("StorageClass", "STANDARD")
                    })
                
                return uploads
                
        except Exception as e:
            logger.error(f"Failed to list multipart uploads: {e}")
            raise

    async def get_upload_progress(self, upload_id: str) -> Optional[Dict[str, Any]]:
        """Get progress information for a multipart upload."""
        if upload_id not in self.active_uploads:
            return None
        
        upload_session = self.active_uploads[upload_id]
        
        return {
            "upload_id": upload_id,
            "key": upload_session.key,
            "bucket": upload_session.bucket,
            "total_size": upload_session.total_size,
            "uploaded_size": upload_session.uploaded_size,
            "progress_percentage": upload_session.progress_percentage,
            "parts_count": len(upload_session.parts),
            "created_at": upload_session.created_at,
            "expires_at": upload_session.expires_at,
            "is_complete": upload_session.is_complete
        }

    async def resume_multipart_upload(
        self,
        upload_id: str,
        file_path: str,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Resume a multipart upload from where it left off.
        
        Args:
            upload_id: Existing upload ID
            file_path: Local file path
            progress_callback: Optional progress callback
            
        Returns:
            Dict containing resume result
        """
        if upload_id not in self.active_uploads:
            raise ValueError(f"Unknown upload ID: {upload_id}")
        
        upload_session = self.active_uploads[upload_id]
        
        logger.info(f"Resuming multipart upload {upload_id}")
        
        try:
            # Continue from where we left off
            result = await self._continue_multipart_upload(
                upload_session=upload_session,
                file_path=file_path,
                progress_callback=progress_callback
            )
            
            self.metrics.resumed_uploads += 1
            logger.info(f"Successfully resumed multipart upload {upload_id}")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to resume multipart upload {upload_id}: {e}")
            raise

    async def get_metrics(self) -> Dict[str, Any]:
        """Get storage system metrics."""
        return {
            **self.metrics.dict(),
            "active_multipart_uploads_list": list(self.active_uploads.keys()),
            "configuration": {
                "chunk_size_mb": self.chunk_size / (1024 * 1024),
                "multipart_threshold_mb": self.multipart_threshold / (1024 * 1024),
                "max_concurrent_parts": self.max_concurrent_parts,
                "max_retries": self.max_retries
            }
        }

    def _get_client(self):
        """Get S3 client with proper configuration."""
        if not self.session:
            raise RuntimeError("Storage manager not initialized")
        
        endpoint_url = f"{'https' if self.use_ssl else 'http'}://{self.endpoint_url}"
        
        return self.session.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region_name
        )

    async def _ensure_bucket_exists(self, client) -> None:
        """Ensure the bucket exists, create if it doesn't."""
        try:
            await client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"Bucket {self.bucket_name} exists")
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "NoSuchBucket":
                logger.info(f"Creating bucket {self.bucket_name}")
                await client.create_bucket(Bucket=self.bucket_name)
            else:
                raise

    async def _simple_upload(
        self,
        file_path: str,
        key: str,
        bucket: str,
        metadata: Optional[Dict[str, str]],
        content_type: str,
        progress_callback: Optional[callable]
    ) -> Dict[str, Any]:
        """Perform a simple (non-multipart) upload."""
        async with self._get_client() as client:
            async with aiofiles.open(file_path, "rb") as f:
                file_data = await f.read()
                
                if progress_callback:
                    await progress_callback(100.0, len(file_data), len(file_data))
                
                response = await client.put_object(
                    Bucket=bucket,
                    Key=key,
                    Body=file_data,
                    ContentType=content_type,
                    Metadata=metadata or {}
                )
                
                return {"ETag": response["ETag"]}

    async def _multipart_upload(
        self,
        file_path: str,
        key: str,
        bucket: str,
        metadata: Optional[Dict[str, str]],
        content_type: str,
        progress_callback: Optional[callable]
    ) -> Dict[str, Any]:
        """Perform a multipart upload."""
        file_size = Path(file_path).stat().st_size
        
        # Start multipart upload
        upload_id = await self.start_multipart_upload(
            key=key,
            total_size=file_size,
            bucket=bucket,
            metadata=metadata,
            content_type=content_type
        )
        
        try:
            # Upload parts concurrently
            await self._upload_parts_concurrent(
                upload_id=upload_id,
                file_path=file_path,
                progress_callback=progress_callback
            )
            
            # Complete the upload
            result = await self.complete_multipart_upload(upload_id)
            return result
            
        except Exception as e:
            # Abort upload on error
            await self.abort_multipart_upload(upload_id)
            raise

    async def _upload_parts_concurrent(
        self,
        upload_id: str,
        file_path: str,
        progress_callback: Optional[callable]
    ) -> None:
        """Upload file parts concurrently."""
        upload_session = self.active_uploads[upload_id]
        file_size = upload_session.total_size
        
        # Calculate part boundaries
        parts_info = []
        part_number = 1
        offset = 0
        
        while offset < file_size:
            part_size = min(self.chunk_size, file_size - offset)
            parts_info.append((part_number, offset, part_size))
            offset += part_size
            part_number += 1
        
        # Create semaphore to limit concurrent uploads
        semaphore = asyncio.Semaphore(self.max_concurrent_parts)
        
        async def upload_part_task(part_num: int, part_offset: int, part_size: int):
            async with semaphore:
                # Read part data
                async with aiofiles.open(file_path, "rb") as f:
                    await f.seek(part_offset)
                    part_data = await f.read(part_size)
                
                # Upload part with retries
                for attempt in range(self.max_retries):
                    try:
                        await self.upload_part(upload_id, part_num, part_data)
                        
                        # Report progress
                        if progress_callback:
                            progress = (upload_session.uploaded_size / upload_session.total_size) * 100.0
                            await progress_callback(progress, upload_session.uploaded_size, upload_session.total_size)
                        
                        break
                        
                    except Exception as e:
                        if attempt == self.max_retries - 1:
                            raise
                        
                        await asyncio.sleep(self.retry_delay * (2 ** attempt))
        
        # Upload all parts concurrently
        tasks = [
            upload_part_task(part_num, part_offset, part_size)
            for part_num, part_offset, part_size in parts_info
        ]
        
        await asyncio.gather(*tasks)

    async def _continue_multipart_upload(
        self,
        upload_session: MultipartUpload,
        file_path: str,
        progress_callback: Optional[callable]
    ) -> Dict[str, Any]:
        """Continue an existing multipart upload."""
        # Determine which parts still need to be uploaded
        uploaded_parts = {part.part_number for part in upload_session.parts}
        file_size = upload_session.total_size
        
        # Calculate remaining parts
        parts_to_upload = []
        part_number = 1
        offset = 0
        
        while offset < file_size:
            part_size = min(self.chunk_size, file_size - offset)
            
            if part_number not in uploaded_parts:
                parts_to_upload.append((part_number, offset, part_size))
            
            offset += part_size
            part_number += 1
        
        if not parts_to_upload:
            # All parts already uploaded, just complete
            return await self.complete_multipart_upload(upload_session.upload_id)
        
        # Upload remaining parts
        semaphore = asyncio.Semaphore(self.max_concurrent_parts)
        
        async def upload_remaining_part(part_num: int, part_offset: int, part_size: int):
            async with semaphore:
                async with aiofiles.open(file_path, "rb") as f:
                    await f.seek(part_offset)
                    part_data = await f.read(part_size)
                
                await self.upload_part(upload_session.upload_id, part_num, part_data)
                
                if progress_callback:
                    progress = (upload_session.uploaded_size / upload_session.total_size) * 100.0
                    await progress_callback(progress, upload_session.uploaded_size, upload_session.total_size)
        
        # Upload remaining parts
        tasks = [
            upload_remaining_part(part_num, part_offset, part_size)
            for part_num, part_offset, part_size in parts_to_upload
        ]
        
        await asyncio.gather(*tasks)
        
        # Complete the upload
        return await self.complete_multipart_upload(upload_session.upload_id)

    def _update_average_speed(self, speed_mbps: float, is_upload: bool) -> None:
        """Update average speed metrics."""
        if is_upload:
            if self.metrics.average_upload_speed_mbps == 0:
                self.metrics.average_upload_speed_mbps = speed_mbps
            else:
                # Exponential moving average
                alpha = 0.1
                self.metrics.average_upload_speed_mbps = (
                    alpha * speed_mbps + 
                    (1 - alpha) * self.metrics.average_upload_speed_mbps
                )
        else:
            if self.metrics.average_download_speed_mbps == 0:
                self.metrics.average_download_speed_mbps = speed_mbps
            else:
                alpha = 0.1
                self.metrics.average_download_speed_mbps = (
                    alpha * speed_mbps + 
                    (1 - alpha) * self.metrics.average_download_speed_mbps
                )