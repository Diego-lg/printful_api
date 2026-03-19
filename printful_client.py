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
        option_groups: List[str] = ['On Hanger'],
        placement: str = "default",
        format: str = "jpg",
        product_template_id: int = None,
        design_params: list = None
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
            design_params: Optional list of design parameters with x, y, scale, rotation
            
        Returns:
            Dictionary containing task information with task_key
        """
        # Build the payload according to Printful API format
        # Reference: https://www.printful.com/docs/mockup-generator
        
        # Log the design_params for debugging
        logger.debug(f"create_mockup_task called with design_params: {design_params}")
        
        # Default position based on product 257 templates (template_id 3920)
        # print_area_width: 2332.0, print_area_height: 3000.0, print_area_top: 0.0, print_area_left: 334.0
        position = {
            "area_width": 2332,
            "area_height": 3000,
            "width": 2332,
            "height": 3000,
            "top": 0,
            "left": 334
        }
        
        # Apply design_params if provided
        if design_params and len(design_params) > 0:
            logger.info(f"Processing design_params: {design_params}")
            params = design_params[0]  # Get first layer's params
            
            # Debug: Log what we got from params
            logger.debug(f"params type: {type(params)}, params: {params}")
            
            # Convert percentage-based position to Printful coordinates
            # x and y are in percentages (0-100), need to convert to pixels
            # Printful uses area_width/area_height as the print area
            x_pct = params.get("x", 50) if isinstance(params, dict) else 50  # Default center
            y_pct = params.get("y", 50) if isinstance(params, dict) else 50  # Default center
            scale = params.get("scale", 100) if isinstance(params, dict) else 100  # Default 100%
            rotation = params.get("rotation", 0) if isinstance(params, dict) else 0  # Default 0 degrees
            
            # Debug: Log extracted values
            logger.debug(f"x_pct: {x_pct} (type: {type(x_pct)}), y_pct: {y_pct} (type: {type(y_pct)}), scale: {scale} (type: {type(scale)}), rotation: {rotation} (type: {type(rotation)})")
            
            # Validate types before calculation
            if not isinstance(x_pct, (int, float)):
                raise ValueError(f"x_pct should be int/float, got {type(x_pct)}: {x_pct}")
            if not isinstance(y_pct, (int, float)):
                raise ValueError(f"y_pct should be int/float, got {type(y_pct)}: {y_pct}")
            if not isinstance(scale, (int, float)):
                raise ValueError(f"scale should be int/float, got {type(scale)}: {scale}")
            
            # Calculate actual dimensions based on scale
            # Scale 100% = full print area width
            scale_factor = scale / 100.0
            position["width"] = int(position["area_width"] * scale_factor)
            position["height"] = int(position["area_height"] * scale_factor)
            
            # Calculate position (centered on x, y percentage)
            # x = 50% means center horizontally
            # y = 50% means center vertically
            position["left"] = int((position["area_width"] * x_pct / 100) - (position["width"] / 2))
            position["top"] = int((position["area_height"] * y_pct / 100) - (position["height"] / 2))
            
            # Add rotation to position if provided (Printful API expects rotation in degrees)
            if rotation is not None and rotation != 0:
                position["rotation"] = rotation
            
            logger.info(f"Converted position: {position}")
            logger.info(f"Scale: {scale}%, Rotation: {rotation}°")
        
        # Build the files array with position (without extra options)
        files = [
            {
                "placement": placement,
                "image_url": image_url,
                "position": position
            }
        ]
        
        # Log the final files array for debugging
        logger.info(f"Printful API files payload: {files}")
        
        # Build the payload matching the exact API format from Postman collection
        payload = {
            "variant_ids": variant_ids,
            "format": format,
            "width": 0,
            "product_options": {},
            "option_groups": option_groups,
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
