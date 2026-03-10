import os
import requests
import logging
from typing import Optional, List, Dict, Any

# Create logger for Printful client
logger = logging.getLogger("printful_mockups.printful_client")


class PrintfulClient:
    """Printful API Client for interacting with Printful services."""
    
    BASE_URL = "https://api.printful.com"
    
    def __init__(self, api_key: str, store_id: str):
        """
        Initialize the Printful API client.
        
        Args:
            api_key: Printful API key
            store_id: Printful Store ID
        """
        self.api_key = api_key
        self.store_id = store_id
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "X-PF-Store-ID": store_id,
            "Content-Type": "application/json"
        })
        logger.debug(f"PrintfulClient initialized with store_id: {store_id}")
    
    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        Make an API request to Printful.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            **kwargs: Additional arguments to pass to requests
            
        Returns:
            JSON response from API
            
        Raises:
            requests.HTTPError: If the API returns an error
        """
        url = f"{self.BASE_URL}{endpoint}"
        
        # Log the request details for debugging
        logger.debug(f"Printful API Request: {method} {url}")
        if 'json' in kwargs:
            logger.debug(f"Request body: {kwargs['json']}")
        if 'params' in kwargs:
            logger.debug(f"Request params: {kwargs['params']}")
        
        response = self.session.request(method, url, **kwargs)
        
        # Log the response details
        logger.debug(f"Printful API Response status: {response.status_code}")
        try:
            response_json = response.json()
            logger.debug(f"Response body: {response_json}")
        except:
            logger.debug(f"Response raw: {response.text[:500]}")
        
        response.raise_for_status()
        return response.json()
    
    def get_products(self) -> Dict[str, Any]:
        """
        Fetch all products from the Printful catalog.
        
        Returns:
            Dictionary containing products information
        """
        return self._request("GET", "/products")
    
    def get_product(self, product_id: int) -> Dict[str, Any]:
        """
        Get a specific product with its variants.
        
        Args:
            product_id: The ID of the product to retrieve
            
        Returns:
            Dictionary containing product details and variants
        """
        return self._request("GET", f"/products/{product_id}")
    
    def get_layout_templates(self, product_id: int) -> Dict[str, Any]:
        """
        Get mockup templates for a product.
        
        Args:
            product_id: The ID of the product
            
        Returns:
            Dictionary containing layout templates
        """
        return self._request("GET", f"/mockup-generator/templates/{product_id}")
    
    def create_mockup_task(
        self, 
        product_id: int, 
        variant_ids: List[int], 
        image_url: str,
        placement: str = "default",
        format: str = "jpg",
        product_template_id: int = None,
        position: dict = None
    ) -> Dict[str, Any]:
        """
        Create a mockup generation task.
        
        Args:
            product_id: The ID of the product
            variant_ids: List of variant IDs to generate mockups for
            image_url: URL of the image to use for the mockup
            placement: The placement on the product (default: "default")
            format: The output format (default: "jpg")
            product_template_id: Optional product template ID
            position: Optional position dict with area_width, area_height, width, height, top, left
            
        Returns:
            Dictionary containing task information with task_key
        """
        # Build the payload according to Printful API format
        # Reference: https://www.printful.com/docs/mockup-generator
        
        # Default position based on product 257 templates (template_id 3920)
        # print_area_width: 2332.0, print_area_height: 3000.0, print_area_top: 0.0, print_area_left: 334.0
        if position is None:
            position = {
                "area_width": 2332,
                "area_height": 3000,
                "width": 2332,
                "height": 3000,
                "top": 0,
                "left": 334
            }
        
        # Build the files array with position (without extra options)
        files = [
            {
                "placement": placement,
                "image_url": image_url,
                "position": position
            }
        ]
        
        # Build the payload matching the exact API format from Postman collection
        payload = {
            "variant_ids": variant_ids,
            "format": format,
            "width": 0,
            "product_options": {},
            "files": files
        }
        
        # Add optional parameters if provided
        if product_template_id:
            payload["product_template_id"] = product_template_id
        
        return self._request(
            "POST", 
            f"/mockup-generator/create-task/{product_id}",
            json=payload
        )
    
    def get_task_result(self, task_key: str) -> Dict[str, Any]:
        """
        Poll for mockup generation task result.
        
        Args:
            task_key: The task key returned from create_mockup_task
            
        Returns:
            Dictionary containing task status and result (if completed)
        """
        return self._request(
            "GET", 
            f"/mockup-generator/task",
            params={"task_key": task_key}
        )
    
    def upload_file(self, file_data: bytes, filename: str) -> Dict[str, Any]:
        """
        Upload a file to Printful's file storage.
        
        Args:
            file_data: The binary content of the file
            filename: The name of the file
            
        Returns:
            Dictionary containing file information including the URL
        """
        import io
        
        # Create a file-like object from the bytes
        files = {
            "file": (filename, io.BytesIO(file_data), "image/jpeg")
        }
        
        # Remove content-type header for multipart form data
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "X-PF-Store-ID": self.store_id
        }
        
        url = f"{self.BASE_URL}/files"
        response = self.session.post(url, files=files, headers=headers)
        response.raise_for_status()
        return response.json()
