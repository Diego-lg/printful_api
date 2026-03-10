"""
R2 Client for Cloudflare R2 Storage Operations

This module provides functionality to upload images to Cloudflare R2
and generate public URLs that can be accessed by external services like Printful.
"""

import os
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError, EndpointConnectionError, ConnectTimeoutError, ReadTimeoutError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class R2Client:
    """Client for interacting with Cloudflare R2 storage."""
    
    def __init__(self):
        """Initialize R2 client with credentials from environment."""
        self.access_key_id = os.getenv("R2_ACCESS_KEY_ID", "")
        self.secret_access_key = os.getenv("R2_SECRET_ACCESS_KEY", "")
        self.bucket_name = os.getenv("R2_BUCKET_NAME", "")
        self.account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID", "")
        self.endpoint = os.getenv("R2_ENDPOINT", "")
        self.public_bucket_url = os.getenv("R2_PUBLIC_BUCKET_URL", "")
        
        # Validate credentials
        if not all([self.access_key_id, self.secret_access_key, self.bucket_name, self.endpoint]):
            raise ValueError("Missing required R2 configuration. Check R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET_NAME, and R2_ENDPOINT in .env")
        
        # Configure boto3 client for R2 with timeouts
        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_access_key,
            endpoint_url=self.endpoint,
            config=Config(
                signature_version="s3v4",
                connect_timeout=10,
                read_timeout=30,
                retries={"max_attempts": 3}
            ),
            region_name="auto"
        )
        
        self.folder = "tests"
    
    def upload_file(self, file_path, filename=None):
        """
        Upload a file to R2 bucket.
        
        Args:
            file_path: Path to the local file to upload
            filename: Optional custom filename. If not provided, uses the original filename.
        
        Returns:
            dict: Contains 'key' (R2 object key) and 'public_url' (publicly accessible URL)
        
        Raises:
            Exception: If upload fails, with descriptive error message
        """
        # Determine the filename to use
        if filename is None:
            filename = os.path.basename(file_path)
        
        # Create the R2 object key with folder prefix
        key = f"{self.folder}/{filename}"
        
        # Determine content type based on file extension
        content_type = self._get_content_type(filename)
        
        # Upload the file to R2 with error handling
        # Using put_object instead of upload_fileobj for more reliable uploads
        try:
            with open(file_path, "rb") as f:
                file_data = f.read()
                self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=key,
                    Body=file_data,
                    ContentType=content_type
                )
        except ConnectTimeoutError as e:
            raise Exception(f"R2 connection timeout: Could not connect to R2 endpoint. Please check your network and R2_ENDPOINT configuration. Details: {str(e)}")
        except ReadTimeoutError as e:
            raise Exception(f"R2 read timeout: The request timed out while waiting for a response from R2. Details: {str(e)}")
        except EndpointConnectionError as e:
            raise Exception(f"R2 endpoint connection error: Could not connect to R2 at {self.endpoint}. Please verify R2_ENDPOINT is correct. Details: {str(e)}")
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_message = e.response.get("Error", {}).get("Message", str(e))
            if error_code in ["InvalidAccessKeyId", "SignatureDoesNotMatch"]:
                raise Exception(f"R2 authentication failed: Invalid credentials. Please check R2_ACCESS_KEY_ID and R2_SECRET_ACCESS_KEY. Details: {error_message}")
            elif error_code == "NoSuchBucket":
                raise Exception(f"R2 bucket not found: The bucket '{self.bucket_name}' does not exist. Please check R2_BUCKET_NAME. Details: {error_message}")
            else:
                raise Exception(f"R2 client error ({error_code}): {error_message}")
        except Exception as e:
            raise Exception(f"R2 upload failed: {str(e)}")
        
        # Generate public URL
        public_url = self.get_public_url(key)
        
        return {
            "key": key,
            "public_url": public_url
        }
    
    def upload_file_data(self, file_data, filename):
        """
        Upload file data (bytes) to R2 bucket.
        
        Args:
            file_data: Bytes data to upload
            filename: Name for the file in R2
        
        Returns:
            dict: Contains 'key' (R2 object key) and 'public_url' (publicly accessible URL)
        """
        # Create the R2 object key with folder prefix
        key = f"{self.folder}/{filename}"
        
        # Determine content type based on file extension
        content_type = self._get_content_type(filename)
        
        # Upload the file data to R2
        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=key,
            Body=file_data,
            ContentType=content_type
        )
        
        # Generate public URL
        public_url = self.get_public_url(key)
        
        return {
            "key": key,
            "public_url": public_url
        }
    
    def get_public_url(self, key):
        """
        Get the public URL for a file in R2.
        
        Args:
            key: The R2 object key (including folder path)
        
        Returns:
            str: Publicly accessible URL
        """
        # Use the public bucket URL
        return f"{self.public_bucket_url}/{key}"
    
    def delete_file(self, key):
        """
        Delete a file from R2 bucket.
        
        Args:
            key: The R2 object key to delete
        
        Returns:
            bool: True if deletion was successful
        """
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=key
            )
            return True
        except Exception:
            return False
    
    def file_exists(self, key):
        """
        Check if a file exists in R2 bucket.
        
        Args:
            key: The R2 object key to check
        
        Returns:
            bool: True if file exists
        """
        try:
            self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=key
            )
            return True
        except Exception:
            return False
    
    @staticmethod
    def _get_content_type(filename):
        """Determine content type based on file extension."""
        ext = filename.rsplit(".", 1)[1].lower() if "." in filename else ""
        
        content_types = {
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "gif": "image/gif",
            "webp": "image/webp",
            "bmp": "image/bmp",
            "tiff": "image/tiff",
            "tif": "image/tiff"
        }
        
        return content_types.get(ext, "application/octet-stream")


    def test_connection(self):
        """
        Test the R2 connection by listing buckets.
        
        Returns:
            dict: Contains 'success' boolean and 'message' string
        """
        try:
            # Try to list objects in the bucket (lightweight check)
            self.s3_client.list_objects_v2(Bucket=self.bucket_name, MaxKeys=1)
            return {"success": True, "message": "R2 connection successful"}
        except ConnectTimeoutError as e:
            return {"success": False, "message": f"R2 connection timeout: {str(e)}"}
        except EndpointConnectionError as e:
            return {"success": False, "message": f"R2 endpoint unreachable: {str(e)}"}
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            if error_code == "NoSuchBucket":
                return {"success": False, "message": f"R2 bucket '{self.bucket_name}' not found"}
            return {"success": False, "message": f"R2 error: {error_code}"}
        except Exception as e:
            return {"success": False, "message": f"R2 connection failed: {str(e)}"}


# Create a singleton instance with error handling
try:
    r2_client = R2Client()
except Exception as e:
    print(f"WARNING: Failed to initialize R2 client: {str(e)}")
    # Create a dummy client that will fail gracefully
    class DummyR2Client:
        def __init__(self, error_message):
            self.error_message = error_message
        def upload_file(self, file_path, filename=None):
            raise Exception(f"R2 not available: {self.error_message}")
        def test_connection(self):
            return {"success": False, "message": f"R2 initialization failed: {self.error_message}"}
    r2_client = DummyR2Client(str(e))
