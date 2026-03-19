"""
Test Script for Batch Mockup Generation
=========================================
This script tests the batch mockup generation functionality by:
1. Creating a batch with multiple configurations
2. Polling for results until completion
3. Verifying the generated mockups
"""

import requests
import time
import json
import os
import sys
from datetime import datetime

# Configuration
BASE_URL = "http://127.0.0.1:5000"
POLL_INTERVAL = 5  # seconds
MAX_POLL_ATTEMPTS = 60  # 5 minutes max

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def log_info(msg):
    print(f"{Colors.BLUE}[INFO]{Colors.RESET} {msg}")

def log_success(msg):
    print(f"{Colors.GREEN}[SUCCESS]{Colors.RESET} {msg}")

def log_warning(msg):
    print(f"{Colors.YELLOW}[WARNING]{Colors.RESET} {msg}")

def log_error(msg):
    print(f"{Colors.RED}[ERROR]{Colors.RESET} {msg}")

def test_r2_connection():
    """Test R2 connectivity."""
    log_info("Testing R2 connection...")
    try:
        response = requests.get(f"{BASE_URL}/api/test-r2", timeout=10)
        result = response.json()
        
        if result.get("success"):
            log_success("R2 connection successful")
            return True
        else:
            log_error(f"R2 connection failed: {result.get('message')}")
            return False
    except Exception as e:
        log_error(f"R2 connection error: {e}")
        return False

def test_list_batches():
    """Test listing all batches."""
    log_info("Testing list batches endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/api/batch-mockups", timeout=10)
        result = response.json()
        
        if result.get("success"):
            batches = result.get("batches", [])
            log_success(f"Found {len(batches)} existing batches")
            return True
        else:
            log_error(f"List batches failed: {result.get('error')}")
            return False
    except Exception as e:
        log_error(f"List batches error: {e}")
        return False

def get_config():
    """Get current product configuration."""
    log_info("Getting product configuration...")
    try:
        response = requests.get(f"{BASE_URL}/api/config", timeout=10)
        result = response.json()
        
        if result.get("success"):
            config = {
                "product_id": result.get("product_id"),
                "variant_id": result.get("variant_id")
            }
            log_success(f"Product config: {config}")
            return config
        else:
            log_error(f"Get config failed: {result.get('error')}")
            return None
    except Exception as e:
        log_error(f"Get config error: {e}")
        return None

def upload_test_image():
    """Upload test.png to R2 and return the URL."""
    log_info("Uploading test.png to R2...")
    
    try:
        # Check if test.png exists
        test_png_path = os.path.join(os.path.dirname(__file__), "test.png")
        if not os.path.exists(test_png_path):
            log_error(f"test.png not found at {test_png_path}")
            return None
        
        # Upload via the app's upload endpoint
        with open(test_png_path, "rb") as f:
            files = {"file": ("test.png", f, "image/png")}
            data = {"create_mockup": "false"}
            response = requests.post(
                f"{BASE_URL}/api/upload",
                files=files,
                data=data,
                timeout=30
            )
        
        result = response.json()
        
        if result.get("success"):
            design_url = result.get("data", {}).get("r2_public_url")
            log_success(f"Uploaded to R2: {design_url}")
            return design_url
        else:
            log_error(f"Upload failed: {result.get('error')}")
            return None
    except Exception as e:
        log_error(f"Upload error: {e}")
        return None

def create_batch(design_url, configurations):
    """Create a batch with given configurations."""
    log_info(f"Creating batch with {len(configurations)} configurations...")
    
    payload = {
        "design_url": design_url,
        "configurations": configurations
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/batch-mockups",
            json=payload,
            timeout=30
        )
        
        result = response.json()
        
        if result.get("success"):
            batch_id = result.get("batch_id")
            task_keys = result.get("task_keys", [])
            log_success(f"Batch created: {batch_id}")
            log_info(f"Task keys: {task_keys}")
            return batch_id, task_keys
        else:
            log_error(f"Create batch failed: {result.get('error')}")
            return None, None
    except Exception as e:
        log_error(f"Create batch error: {e}")
        return None, None

def poll_batch_results(batch_id, max_attempts=MAX_POLL_ATTEMPTS):
    """Poll for batch results until completion or timeout."""
    log_info(f"Polling batch results for {batch_id}...")
    
    for attempt in range(1, max_attempts + 1):
        try:
            response = requests.get(
                f"{BASE_URL}/api/batch-mockups/poll/{batch_id}",
                timeout=30
            )
            
            result = response.json()
            
            if not result.get("success"):
                log_error(f"Poll failed: {result.get('error')}")
                return None
            
            progress = result.get("progress", {})
            batch = result.get("batch", {})
            status = batch.get("status", "unknown")
            
            completed = progress.get("completed", 0)
            pending = progress.get("pending", 0)
            failed = progress.get("failed", 0)
            total = progress.get("total", 0)
            
            print(f"  Attempt {attempt}/{max_attempts}: {completed}/{total} completed, {pending} pending, {failed} failed - Status: {status}")
            
            # Check if all tasks are done
            if pending == 0:
                log_success(f"Batch {batch_id} finished with status: {status}")
                return result
            
            # Wait before next poll
            time.sleep(POLL_INTERVAL)
            
        except Exception as e:
            log_error(f"Poll error (attempt {attempt}): {e}")
            time.sleep(POLL_INTERVAL)
    
    log_warning(f"Max poll attempts reached for batch {batch_id}")
    return None

def get_batch_details(batch_id):
    """Get detailed batch information."""
    log_info(f"Getting batch details for {batch_id}...")
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/batch-mockups/{batch_id}",
            timeout=30
        )
        
        result = response.json()
        
        if result.get("success"):
            batch = result.get("batch", {})
            log_success(f"Batch details retrieved")
            return batch
        else:
            log_error(f"Get batch failed: {result.get('error')}")
            return None
    except Exception as e:
        log_error(f"Get batch error: {e}")
        return None

def verify_mockup_files(batch_id, batch_details):
    """Verify that mockup files were saved locally."""
    log_info(f"Verifying mockup files for batch {batch_id}...")
    
    variations = batch_details.get("variations", [])
    
    if not variations:
        log_warning("No variations found in batch")
        return False
    
    # Check if local files exist
    project_dir = os.path.dirname(__file__)
    batch_folder = os.path.join(project_dir, "mockup_variations", batch_id)
    
    if not os.path.exists(batch_folder):
        log_error(f"Batch folder not found: {batch_folder}")
        return False
    
    files = os.listdir(batch_folder)
    mockup_files = [f for f in files if f.startswith("mockup_") and f.endswith(".png")]
    
    log_success(f"Found {len(mockup_files)} mockup files in {batch_folder}")
    
    # List the files
    for f in mockup_files:
        file_path = os.path.join(batch_folder, f)
        size = os.path.getsize(file_path)
        log_info(f"  - {f} ({size} bytes)")
    
    return len(mockup_files) > 0

def run_full_test():
    """Run the full batch mockup generation test."""
    print(f"\n{Colors.BOLD}{'='*60}")
    print("BATCH MOCKUP GENERATION TEST")
    print(f"{'='*60}{Colors.RESET}\n")
    
    # Test 1: Check if server is running
    log_info("Test 1: Server connectivity check...")
    try:
        response = requests.get(BASE_URL, timeout=5)
        log_success("Server is running")
    except Exception as e:
        log_error(f"Server not accessible: {e}")
        log_error("Make sure the Flask app is running (python app.py)")
        return False
    
    # Test 2: R2 connection
    log_info("\nTest 2: R2 connectivity...")
    if not test_r2_connection():
        log_error("R2 connection failed - some tests may not work")
    
    # Test 3: List existing batches
    log_info("\nTest 3: List existing batches...")
    test_list_batches()
    
    # Test 4: Get configuration
    log_info("\nTest 4: Get product configuration...")
    config = get_config()
    if not config:
        log_warning("Could not get product configuration")
    
    # Test 5: Upload test image
    log_info("\nTest 5: Upload test image to R2...")
    design_url = upload_test_image()
    if not design_url:
        log_error("Failed to upload test image")
        # Try using existing test batch instead
        log_info("Will test using existing batches...")
    
    # Test 6: Create a new batch
    log_info("\nTest 6: Create new batch mockups...")
    
    if design_url:
        # Define test configurations - 10 diverse variations
        configurations = [
            {"name": "Center, 100%, 0°", "x": 50, "y": 50, "scale": 100, "rotation": 0},
            {"name": "Top-Left, 80%, 0°", "x": 30, "y": 30, "scale": 80, "rotation": 0},
            {"name": "Bottom-Right, 80%, 0°", "x": 70, "y": 70, "scale": 80, "rotation": 0},
            {"name": "Top-Right, 70%, 0°", "x": 70, "y": 30, "scale": 70, "rotation": 0},
            {"name": "Bottom-Left, 70%, 0°", "x": 30, "y": 70, "scale": 70, "rotation": 0},
            {"name": "Center, 50%, 0°", "x": 50, "y": 50, "scale": 50, "rotation": 0},
            {"name": "Center, 80%, 15°", "x": 50, "y": 50, "scale": 80, "rotation": 15},
            {"name": "Center, 80%, -15°", "x": 50, "y": 50, "scale": 80, "rotation": -15},
            {"name": "Center, 60%, 30°", "x": 50, "y": 50, "scale": 60, "rotation": 30},
            {"name": "Center, 60%, -30°", "x": 50, "y": 50, "scale": 60, "rotation": -30},
        ]
        
        batch_id, task_keys = create_batch(design_url, configurations)
        
        if not batch_id:
            log_error("Failed to create batch")
            return False
        
        # Test 7: Poll for results
        log_info("\nTest 7: Poll for batch results...")
        print(f"\n{Colors.YELLOW}Polling will take several minutes. Press Ctrl+C to cancel.{Colors.RESET}\n")
        
        poll_result = poll_batch_results(batch_id)
        
        if not poll_result:
            log_warning("Polling did not complete successfully")
        
        # Test 8: Get batch details
        log_info("\nTest 8: Get batch details...")
        batch_details = get_batch_details(batch_id)
        
        if batch_details:
            log_success(f"Batch status: {batch_details.get('status')}")
            log_success(f"Variations count: {len(batch_details.get('variations', []))}")
            
            # Test 9: Verify mockup files
            log_info("\nTest 9: Verify mockup files...")
            verify_mockup_files(batch_id, batch_details)
        
    else:
        # Test using existing batches
        log_info("\nTesting with existing batches...")
        
        response = requests.get(f"{BASE_URL}/api/batch-mockups", timeout=10)
        result = response.json()
        
        batches = result.get("batches", [])
        
        if not batches:
            log_warning("No existing batches found")
            log_info("Creating a new test batch using the built-in test endpoint...")
            
            # Use the built-in test endpoint
            try:
                response = requests.post(f"{BASE_URL}/api/batch-mockups/test", timeout=30)
                result = response.json()
                
                if result.get("success"):
                    batch_id = result.get("batch_id")
                    log_success(f"Test batch created: {batch_id}")
                    
                    # Poll for results
                    print(f"\n{Colors.YELLOW}Polling will take several minutes. Press Ctrl+C to cancel.{Colors.RESET}\n")
                    poll_result = poll_batch_results(batch_id)
                    
                    if poll_result:
                        batch_details = get_batch_details(batch_id)
                        if batch_details:
                            log_success(f"Batch status: {batch_details.get('status')}")
                            verify_mockup_files(batch_id, batch_details)
                else:
                    log_error(f"Test batch creation failed: {result.get('error')}")
            except Exception as e:
                log_error(f"Test batch error: {e}")
        else:
            # Test with most recent batch
            latest_batch = batches[0]
            batch_id = latest_batch.get("batch_id")
            log_success(f"Testing with most recent batch: {batch_id}")
            
            poll_result = poll_batch_results(batch_id)
            
            if poll_result:
                batch_details = get_batch_details(batch_id)
                if batch_details:
                    status = batch_details.get("status")
                    variations = batch_details.get("variations", [])
                    
                    log_success(f"Batch status: {status}")
                    log_success(f"Variations: {len(variations)}")
                    
                    verify_mockup_files(batch_id, batch_details)
    
    print(f"\n{Colors.BOLD}{'='*60}")
    print("TEST COMPLETED")
    print(f"{'='*60}{Colors.RESET}\n")
    
    return True

if __name__ == "__main__":
    try:
        success = run_full_test()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Test interrupted by user{Colors.RESET}")
        sys.exit(1)
