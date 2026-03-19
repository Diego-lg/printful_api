import os
import time
import uuid
import json
import logging
import werkzeug
from datetime import datetime
from flask import Flask, render_template, jsonify, request, send_from_directory
from dotenv import load_dotenv
from printful_client import PrintfulClient
from r2_client import r2_client


# ============================================================
# LOGGING CONFIGURATION
# ============================================================

# Create logger
logger = logging.getLogger("printful_mockups")

# Set log level
logger.setLevel(logging.DEBUG)

# Create console handler with formatting
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)

# Create formatter with timestamp, level, file:line, and message
formatter = logging.Formatter(
    "%(asctime)s [%(levelname)s] [%(filename)s:%(lineno)d] %(message)s"
)
formatter.default_msec_format = "%s.%03d"
console_handler.setFormatter(formatter)

# Add handler to logger
logger.addHandler(console_handler)

# Log startup
logger.info("=" * 60)
logger.info("Application starting up - Logging initialized")
logger.info("=" * 60)


# Load environment variables
load_dotenv()

# Fixed product configuration from environment
PRODUCT_ID = int(os.getenv("PRODUCT_ID", "257"))
VARIANT_ID = int(os.getenv("VARIANT_ID", "8852"))

logger.info(f"Product configuration loaded: PRODUCT_ID={PRODUCT_ID}, VARIANT_ID={VARIANT_ID}")

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key-change-in-production")
logger.debug(f"Flask app initialized with secret_key (first 10 chars): {app.secret_key[:10]}...")

# Configure file upload settings (kept for backward compatibility)
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp", "bmp", "tiff"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max file size
logger.debug(f"Upload folder: {UPLOAD_FOLDER}")
logger.debug(f"Max content length: {app.config['MAX_CONTENT_LENGTH']} bytes")
logger.debug(f"Allowed extensions: {ALLOWED_EXTENSIONS}")

# Ensure upload folder exists (kept for backward compatibility)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
logger.info(f"Upload folder ensured: {UPLOAD_FOLDER}")

# Initialize Printful client
printful_client = PrintfulClient(
    api_key=os.getenv("PRINTFUL_API_KEY", ""),
    store_id=os.getenv("PRINTFUL_STORE_ID", "")
)
logger.info("Printful client initialized")


def allowed_file(filename):
    """Check if the file extension is allowed."""
    result = "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    logger.debug(f"allowed_file('{filename}'): {result}")
    return result


def secure_filename_with_ext(filename):
    """Create a secure filename with original extension."""
    # Get the original extension
    if "." in filename:
        ext = filename.rsplit(".", 1)[1].lower()
        # Use the allowed extension or default to jpg
        if ext not in ALLOWED_EXTENSIONS:
            ext = "jpg"
            logger.warning(f"Extension '{ext}' not in allowed list, defaulting to 'jpg'")
    else:
        ext = "jpg"
        logger.warning(f"No extension found in filename '{filename}', defaulting to 'jpg'")
    
    # Generate a unique filename
    unique_filename = f"{uuid.uuid4().hex}_{int(time.time())}.{ext}"
    logger.debug(f"Generated secure filename: {unique_filename}")
    return unique_filename


# ============================================================
# BEFORE REQUEST LOGGING
# ============================================================

@app.before_request
def log_request_info():
    """Log incoming request details before processing."""
    logger.info("=" * 60)
    logger.info(f"Incoming HTTP Request: {request.method} {request.path}")
    logger.info(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Log query parameters
    if request.query_string:
        logger.debug(f"Query parameters: {request.args.to_dict()}")
    else:
        logger.debug("Query parameters: None")
    
    # Log headers (excluding sensitive ones)
    safe_headers = {k: v for k, v in request.headers.items() 
                    if k.lower() not in ['authorization', 'cookie', 'x-api-key']}
    logger.debug(f"Request headers: {safe_headers}")
    
    # Log content type
    logger.debug(f"Content-Type: {request.content_type}")
    
    # Log form data if present
    if request.form:
        form_data = dict(request.form)
        # Mask sensitive fields
        for key in form_data:
            if 'key' in key.lower() or 'secret' in key.lower() or 'password' in key.lower():
                form_data[key] = '***REDACTED***'
        logger.debug(f"Form data: {form_data}")
    
    # Log JSON body if present
    if request.is_json:
        try:
            json_data = request.get_json()
            # Mask sensitive fields
            masked_data = {}
            for key, value in json_data.items():
                if 'key' in key.lower() or 'secret' in key.lower() or 'password' in key.lower() or 'token' in key.lower():
                    masked_data[key] = '***REDACTED***'
                else:
                    masked_data[key] = value
            logger.debug(f"JSON body: {masked_data}")
        except Exception as e:
            logger.warning(f"Failed to parse JSON body: {e}")
    
    logger.info(f"Request starting - {request.method} {request.path}")


# ============================================================
# AFTER REQUEST LOGGING
# ============================================================

@app.after_request
def log_response_info(response):
    """Log response details after processing."""
    logger.info(f"Response: {response.status_code} {response.status}")
    logger.info("=" * 60)
    return response


@app.route("/")
def index():
    """Serve the main interface."""
    logger.info("Serving index page")
    return render_template("index.html")


@app.route("/api/upload", methods=["POST"])
def upload_file():
    """Handle file upload and optionally create a mockup."""
    start_time = time.time()
    logger.info("=" * 60)
    logger.info("POST /api/upload - Starting request")
    
    try:
        # Check if file is in the request
        if "file" not in request.files:
            logger.warning("No file provided in request")
            return jsonify({
                "success": False,
                "error": "No file provided"
            }), 400
        
        file = request.files["file"]
        logger.debug(f"File object: {file}")
        logger.debug(f"Original filename: {file.filename}")
        
        if file.filename == "":
            logger.warning("No file selected (empty filename)")
            return jsonify({
                "success": False,
                "error": "No file selected"
            }), 400
        
        if not allowed_file(file.filename):
            logger.warning(f"File type not allowed: {file.filename}")
            return jsonify({
                "success": False,
                "error": f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
            }), 400
        
        logger.info(f"File validation passed: {file.filename}")
        
        # Generate secure filename
        filename = secure_filename_with_ext(file.filename)
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        logger.info(f"Generated filepath: {filepath}")
        
        # Save the file locally first
        logger.debug(f"Saving file to: {filepath}")
        file.save(filepath)
        
        # Get file size
        file_size = os.path.getsize(filepath)
        logger.info(f"File saved: {filename} ({file_size} bytes)")
        
        # Log file upload details
        logger.debug(f"File details - name: {filename}, path: {filepath}, size: {file_size}")
        
        # Try to upload to R2, but fall back to local file if it fails
        r2_key = None
        r2_public_url = None
        r2_uploaded = False
        r2_start_time = time.time()
        
        logger.info("Attempting R2 upload...")
        
        try:
            logger.debug(f"R2 upload params - filepath: {filepath}, filename: {filename}")
            r2_result = r2_client.upload_file(filepath, filename)
            r2_public_url = r2_result["public_url"]
            r2_key = r2_result["key"]
            r2_uploaded = True
            r2_duration = (time.time() - r2_start_time) * 1000
            logger.info(f"R2 upload successful - key: {r2_key}, duration: {r2_duration:.2f}ms")
            logger.debug(f"R2 public URL: {r2_public_url}")
        except Exception as r2_error:
            r2_duration = (time.time() - r2_start_time) * 1000
            logger.error(f"R2 upload failed after {r2_duration:.2f}ms: {str(r2_error)}")
            logger.warning("Falling back to local file URL")
            # Use local URL as fallback
            r2_public_url = request.host_url + "uploads/" + filename
            logger.debug(f"Using local fallback URL: {r2_public_url}")
        
        # Check if we should also create a mockup
        create_mockup = request.form.get("create_mockup", "false").lower() == "true"
        logger.debug(f"create_mockup flag: {create_mockup}")
        
        # DEBUG: Log design_params received from frontend
        design_params_str = request.form.get("design_params")
        logger.debug(f"design_params received: {design_params_str}")
        
        if design_params_str:
            import json
            try:
                design_params = json.loads(design_params_str)
                logger.info(f"Parsed design_params: {design_params}")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse design_params: {e}")
                design_params = []
        else:
            logger.warning("No design_params received from frontend!")
            design_params = []
        
        if create_mockup:
            logger.info("Creating mockup requested")
            # Use the R2 public URL for Printful to fetch
            # R2 provides a public URL that Printful can access
            logger.debug(f"Using R2 public URL for Printful: {r2_public_url}")
            
            mockup_start_time = time.time()
            
            # Add timeout to prevent hanging using threading (works on Windows)
            from functools import wraps
            import threading
            
            def timeout(seconds):
                def decorator(func):
                    @wraps(func)
                    def wrapper(*args, **kwargs):
                        result = [None]
                        exception = [None]
                        
                        def target():
                            try:
                                result[0] = func(*args, **kwargs)
                            except Exception as e:
                                exception[0] = e
                        
                        thread = threading.Thread(target=target)
                        thread.daemon = True
                        thread.start()
                        thread.join(timeout=seconds)
                        
                        if thread.is_alive():
                            raise TimeoutError(f"Printful API request timed out after {seconds} seconds")
                        if exception[0]:
                            raise exception[0]
                        return result[0]
                    return wrapper
                return decorator
            
            try:
                # Create mockup task with the R2 public URL
                # Printful will fetch the image from this public URL
                logger.info(f"Calling Printful API: create_mockup_task")
                logger.debug(f"Printful API params - product_id: {PRODUCT_ID}, variant_ids: {[VARIANT_ID]}, image_url: {r2_public_url}")
                
                # Call with timeout
                mockup_response = timeout(30)(printful_client.create_mockup_task)(
                    product_id=PRODUCT_ID,
                    variant_ids=[VARIANT_ID],
                    image_url=r2_public_url,
                    design_params=design_params
                )
                
                mockup_duration = (time.time() - mockup_start_time) * 1000
                logger.info(f"Printful API response: success (took {mockup_duration:.2f}ms)")
                logger.debug(f"Printful response data: {mockup_response}")
                
                # Extract task_key if available
                task_key = mockup_response.get("task_key") or mockup_response.get("result", {}).get("task_key")
                if task_key:
                    logger.info(f"Mockup task_key: {task_key}")
                else:
                    logger.warning(f"No task_key in response. Full response: {mockup_response}")
                
                total_duration = (time.time() - start_time) * 1000
                logger.info(f"Total request duration: {total_duration:.2f}ms")
                
                return jsonify({
                    "success": True,
                    "data": {
                        "filename": filename,
                        "local_path": filepath,
                        "r2_key": r2_key,
                        "r2_public_url": r2_public_url,
                        "r2_uploaded": r2_uploaded,
                        "mockup_task": mockup_response
                    },
                    "product_info": {
                        "product_id": PRODUCT_ID,
                        "variant_id": VARIANT_ID
                    }
                })
                
            except TimeoutError as te:
                mockup_duration = (time.time() - mockup_start_time) * 1000
                logger.error(f"Printful API timed out after {mockup_duration:.2f}ms: {str(te)}")
                return jsonify({
                    "success": False,
                    "error": f"Printful API request timed out. Please try again."
                }), 504
            except Exception as e:
                mockup_duration = (time.time() - mockup_start_time) * 1000
                logger.error(f"Printful API error after {mockup_duration:.2f}ms: {str(e)}")
                logger.exception("Full stack trace for mockup creation error:")
                return jsonify({
                    "success": False,
                    "error": f"Failed to create mockup: {str(e)}"
                }), 500
        else:
            logger.info("No mockup creation requested, returning upload result only")
            
            total_duration = (time.time() - start_time) * 1000
            logger.info(f"Total request duration: {total_duration:.2f}ms")
            
            # Return the R2 public URL
            return jsonify({
                "success": True,
                "data": {
                    "filename": filename,
                    "r2_key": r2_key,
                    "r2_public_url": r2_public_url,
                    "r2_uploaded": r2_uploaded,
                    "local_path": filepath
                }
            })
            
    except Exception as e:
        logger.error(f"Unexpected error in upload_file: {str(e)}")
        logger.exception("Full stack trace:")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/uploads/<filename>")
def serve_upload(filename):
    """Serve uploaded files."""
    logger.debug(f"Serving uploaded file: {filename}")
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


@app.route("/api/products", methods=["GET"])
def get_products():
    """List all available products from Printful catalog."""
    start_time = time.time()
    logger.info("GET /api/products - Starting request")
    
    try:
        logger.info("Calling Printful API: get_products")
        
        response = printful_client.get_products()
        
        duration = (time.time() - start_time) * 1000
        logger.info(f"Printful API response: success (took {duration:.2f}ms)")
        
        # Log product count if available
        if isinstance(response, dict) and "products" in response:
            logger.debug(f"Number of products: {len(response.get('products', []))}")
        
        return jsonify({
            "success": True,
            "data": response
        })
    except Exception as e:
        duration = (time.time() - start_time) * 1000
        logger.error(f"Printful API error after {duration:.2f}ms: {str(e)}")
        logger.exception("Full stack trace for get_products error:")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/config", methods=["GET"])
def get_config():
    """Get the current product/variant configuration."""
    logger.debug("GET /api/config - Returning configuration")
    logger.debug(f"Configuration: product_id={PRODUCT_ID}, variant_id={VARIANT_ID}")
    
    return jsonify({
        "success": True,
        "product_id": PRODUCT_ID,
        "variant_id": VARIANT_ID
    })


@app.route("/api/test-r2", methods=["GET"])
def test_r2():
    """Test R2 connectivity."""
    start_time = time.time()
    logger.info("GET /api/test-r2 - Starting request")
    
    try:
        logger.info("Testing R2 connectivity...")
        
        result = r2_client.test_connection()
        
        duration = (time.time() - start_time) * 1000
        logger.info(f"R2 test completed in {duration:.2f}ms")
        logger.debug(f"R2 test result: {result}")
        
        return jsonify(result)
    except Exception as e:
        duration = (time.time() - start_time) * 1000
        logger.error(f"R2 test failed after {duration:.2f}ms: {str(e)}")
        logger.exception("Full stack trace for R2 test error:")
        return jsonify({
            "success": False,
            "message": f"R2 initialization error: {str(e)}"
        }), 500


@app.route("/api/products/<int:product_id>", methods=["GET"])
def get_product(product_id):
    """Get product details with variants."""
    start_time = time.time()
    logger.info(f"GET /api/products/{product_id} - Starting request")
    
    try:
        logger.info(f"Calling Printful API: get_product with product_id={product_id}")
        
        response = printful_client.get_product(product_id)
        
        duration = (time.time() - start_time) * 1000
        logger.info(f"Printful API response: success (took {duration:.2f}ms)")
        
        # Log variant count if available
        if isinstance(response, dict):
            variants = response.get("variants", [])
            logger.debug(f"Number of variants: {len(variants)}")
        
        return jsonify({
            "success": True,
            "data": response
        })
    except Exception as e:
        duration = (time.time() - start_time) * 1000
        logger.error(f"Printful API error after {duration:.2f}ms: {str(e)}")
        logger.exception("Full stack trace for get_product error:")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/templates/<int:product_id>", methods=["GET"])
def get_templates(product_id):
    """Get layout templates for a product."""
    start_time = time.time()
    logger.info(f"GET /api/templates/{product_id} - Starting request")
    
    try:
        logger.info(f"Calling Printful API: get_layout_templates with product_id={product_id}")
        
        response = printful_client.get_layout_templates(product_id)
        
        duration = (time.time() - start_time) * 1000
        logger.info(f"Printful API response: success (took {duration:.2f}ms)")
        
        # Log template count if available
        if isinstance(response, dict):
            layouts = response.get("layouts", [])
            logger.debug(f"Number of layouts: {len(layouts)}")
        
        return jsonify({
            "success": True,
            "data": response
        })
    except Exception as e:
        duration = (time.time() - start_time) * 1000
        logger.error(f"Printful API error after {duration:.2f}ms: {str(e)}")
        logger.exception("Full stack trace for get_templates error:")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/mockups", methods=["POST"])
def create_mockup():
    """Create a mockup generation task with fixed product/variant."""
    start_time = time.time()
    logger.info("POST /api/mockups - Starting request")
    
    try:
        # Log request body
        logger.debug(f"Request content type: {request.content_type}")
        
        data = request.get_json()
        logger.debug(f"Request JSON data: {data}")
        
        if not data:
            logger.warning("No JSON data provided in request")
            return jsonify({
                "success": False,
                "error": "No JSON data provided"
            }), 400
        
        image_url = data.get("image_url")
        logger.debug(f"image_url from request: {image_url}")
        
        if not image_url:
            logger.warning("image_url is required but not provided")
            return jsonify({
                "success": False,
                "error": "image_url is required"
            }), 400
        
        logger.info(f"Calling Printful API: create_mockup_task")
        logger.debug(f"Printful API params - product_id: {PRODUCT_ID}, variant_ids: {[VARIANT_ID]}, image_url: {image_url}")
        
        # Use fixed product_id and variant_id from environment
        response = printful_client.create_mockup_task(
            product_id=PRODUCT_ID,
            variant_ids=[VARIANT_ID],
            image_url=image_url
        )
        
        duration = (time.time() - start_time) * 1000
        logger.info(f"Printful API response: success (took {duration:.2f}ms)")
        
        # Extract and log task_key
        task_key = response.get("task_key") or response.get("result", {}).get("task_key")
        if task_key:
            logger.info(f"Mockup task_key: {task_key}")
        else:
            logger.warning("No task_key found in Printful response")
        
        logger.debug(f"Printful response data: {response}")
        
        return jsonify({
            "success": True,
            "data": response,
            "product_info": {
                "product_id": PRODUCT_ID,
                "variant_id": VARIANT_ID
            }
        })
    except Exception as e:
        duration = (time.time() - start_time) * 1000
        logger.error(f"Printful API error after {duration:.2f}ms: {str(e)}")
        logger.exception("Full stack trace for create_mockup error:")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/mockups/<task_key>", methods=["GET"])
def get_mockup_result(task_key):
    """Poll for mockup generation task result."""
    start_time = time.time()
    logger.info(f"GET /api/mockups/{task_key} - Starting request")
    logger.debug(f"Polling for task_key: {task_key}")
    
    try:
        logger.info(f"Calling Printful API: get_task_result with task_key={task_key}")
        
        response = printful_client.get_task_result(task_key)
        
        duration = (time.time() - start_time) * 1000
        logger.info(f"Printful API response: success (took {duration:.2f}ms)")
        
        # DEBUG: Log the full Printful API response
        logger.info(f"Printful full response: {response}")
        
        # Check the task status
        task_data = response.get("result", {})
        status = task_data.get("status", "unknown")
        
        logger.info(f"Task status: {status}")
        logger.debug(f"Task data keys: {task_data.keys() if isinstance(task_data, dict) else 'not a dict'}")
        logger.debug(f"Full task data: {task_data}")
        
        # Build the response
        result = {
            "success": True,
            "status": status,
            "task_key": task_key
        }
        
        # If completed, include the generated mockup files
        if status == "completed":
            logger.info(f"Task is completed, extracting mockups...")
            # Printful returns mockups in task_data.get("mockups", [])
            mockups_data = task_data.get("mockups", [])
            logger.info(f"Mockups from Printful: {mockups_data}")
            
            if not mockups_data:
                logger.warning(f"No mockups found in response. Full task_data: {task_data}")
            
            # Extract mockup URLs - Printful uses "mockup_url" field
            mockups = []
            for m in mockups_data:
                # Main mockup URL
                if m.get("mockup_url"):
                    mockups.append({
                        "url": m.get("mockup_url"),
                        "name": m.get("title", "Front"),
                        "type": "mockup"
                    })
                # Extra mockups (back, left, right, etc.)
                for extra in m.get("extra", []):
                    if extra.get("url"):
                        mockups.append({
                            "url": extra.get("url"),
                            "name": extra.get("title", "Extra"),
                            "type": "mockup"
                        })
            
            result["mockups"] = mockups
            logger.info(f"Mockup generation completed - {len(mockups)} mockups extracted")
            logger.debug(f"Extracted mockup URLs: {mockups}")
        elif status == "pending":
            logger.info("Mockup generation still pending")
        elif status == "failed":
            logger.error(f"Mockup generation failed - task_key: {task_key}")
            error_message = task_data.get("error", "Unknown error")
            logger.error(f"Error message: {error_message}")
        else:
            logger.warning(f"Unknown task status: {status}")
        
        return jsonify(result)
    except Exception as e:
        duration = (time.time() - start_time) * 1000
        logger.error(f"Printful API error after {duration:.2f}ms: {str(e)}")
        logger.exception("Full stack trace for get_mockup_result error:")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ============================================================
# BATCH MOCKUP GENERATION
# ============================================================

# Create mockup variations folder
MOCKUP_VARIATIONS_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mockup_variations")
os.makedirs(MOCKUP_VARIATIONS_FOLDER, exist_ok=True)
logger.info(f"Mockup variations folder: {MOCKUP_VARIATIONS_FOLDER}")

# Serve mockup variations folder
@app.route("/mockup_variations/<path:filename>")
def serve_mockup_variation(filename):
    """Serve mockup variation images."""
    return send_from_directory(MOCKUP_VARIATIONS_FOLDER, filename)


def create_batch_folder(batch_id):
    """Create a folder for a batch."""
    batch_folder = os.path.join(MOCKUP_VARIATIONS_FOLDER, batch_id)
    os.makedirs(batch_folder, exist_ok=True)
    return batch_folder


def save_mockup_image(mockup_url, batch_folder, config_index):
    """Download and save mockup image from URL."""
    try:
        import urllib.request
        import urllib.error
        
        # Generate filename
        filename = f"mockup_{config_index}.png"
        filepath = os.path.join(batch_folder, filename)
        
        # Download image
        logger.info(f"Downloading mockup from: {mockup_url}")
        urllib.request.urlretrieve(mockup_url, filepath)
        
        logger.info(f"Mockup saved to: {filepath}")
        return filepath
    except Exception as e:
        logger.error(f"Failed to save mockup image: {e}")
        return None


def process_single_configuration(config, index, design_url):
    """Process a single configuration - called by background thread.
    
    Creates a mockup task via Printful API and returns the result.
    """
    try:
        # Create design_params for Printful
        design_params = [{
            "name": f"Layer {index + 1}",
            "x": config.get("x", 50),
            "y": config.get("y", 50),
            "scale": config.get("scale", 100),
            "rotation": config.get("rotation", 0)
        }]
        
        # DEBUG: Log design_params before calling API
        logger.info(f"Background: Creating mockup for config {index + 1}: {config}")
        logger.info(f"Background: design_params for config {index + 1}: {design_params}")
        
        # DEBUG: Log all params being passed
        logger.info(f"Background: Calling create_mockup_task with:")
        logger.info(f"  product_id: {PRODUCT_ID}")
        logger.info(f"  variant_ids: {[VARIANT_ID]}")
        logger.info(f"  image_url: {design_url}")
        logger.info(f"  design_params: {design_params}")
        
        response = printful_client.create_mockup_task(
            product_id=PRODUCT_ID,
            variant_ids=[VARIANT_ID],
            image_url=design_url,
            design_params=design_params
        )
        
        # Log full Printful response for debugging
        logger.info(f"Background: Printful create-task response: {response}")
        
        task_key = response.get("task_key") or response.get("result", {}).get("task_key")
        logger.info(f"Background: Extracted task_key: {task_key}")
        
        return {
            "index": index,
            "config": config,
            "task_key": task_key,
            "status": "created",
            "error": None
        }
    except Exception as e:
        import traceback
        logger.error(f"Background: Error creating mockup for config {index}: {e}")
        logger.error(f"Background: Full traceback: {traceback.format_exc()}")
        return {
            "index": index,
            "config": config,
            "task_key": None,
            "status": "error",
            "error": str(e)
        }


@app.route("/api/batch-mockups", methods=["POST"])
def create_batch_mockups():
    """Create multiple mockups with different configurations.
    
    This endpoint returns immediately after saving metadata.
    Configurations are processed in a background thread to avoid
    client timeouts due to Printful API rate limiting.
    """
    start_time = time.time()
    logger.info("POST /api/batch-mockups - Starting request")
    
    try:
        data = request.get_json()
        logger.debug(f"Request JSON data: {data}")
        
        if not data:
            return jsonify({
                "success": False,
                "error": "No JSON data provided"
            }), 400
        
        # Get configurations
        configurations = data.get("configurations", [])
        design_url = data.get("design_url", "")
        
        if not configurations:
            return jsonify({
                "success": False,
                "error": "No configurations provided"
            }), 400
        
        if not design_url:
            return jsonify({
                "success": False,
                "error": "design_url is required"
            }), 400
        
        logger.info(f"Creating {len(configurations)} mockup variations")
        
        # Create batch ID
        batch_id = f"batch_{uuid.uuid4().hex[:12]}_{int(time.time())}"
        
        # Create batch folder first to ensure it exists
        batch_folder = os.path.join(MOCKUP_VARIATIONS_FOLDER, batch_id)
        os.makedirs(batch_folder, exist_ok=True)
        logger.info(f"Created batch folder: {batch_folder}")
        
        # Prepare initial batch metadata with status "pending" - configs not yet processed
        batch_metadata = {
            "batch_id": batch_id,
            "created_at": datetime.now().isoformat(),
            "design_url": design_url,
            "configurations": configurations,
            "variations": [],
            "status": "pending",  # Changed from "processing" - configs not started yet
            "task_keys": [],
            "pending_indices": list(range(len(configurations))),  # Track which configs need processing
            "completed_indices": [],
            "failed_indices": []
        }
        
        # Save initial metadata BEFORE starting background processing
        metadata_path = os.path.join(batch_folder, "metadata.json")
        with open(metadata_path, "w") as f:
            json.dump(batch_metadata, f, indent=2)
        
        logger.info(f"Batch {batch_id} metadata saved, returning immediately. Configurations will be processed in background.")
        
        # Return immediately to client with batch_id
        # Background thread will process configurations
        # Read task_keys from metadata (may be empty if background thread hasn't processed yet)
        with open(metadata_path, "r") as f:
            current_metadata = json.load(f)
        
        response_data = {
            "success": True,
            "batch_id": batch_id,
            "configurations_count": len(configurations),
            "task_keys": current_metadata.get("task_keys", []),
            "status": current_metadata.get("status", "pending"),
            "message": "Batch created. Configurations are being processed in background. Use GET /api/batch-mockups/poll/{batch_id} to check status."
        }
        
        # Start background thread to process configurations
        import threading
        
        def background_process_configs(batch_id, configurations, design_url, batch_folder, metadata_path):
            """Process configurations in background thread."""
            logger.info(f"Background thread started for batch {batch_id}")
            
            # Load metadata
            with open(metadata_path, "r") as f:
                batch_metadata = json.load(f)
            
            results = []
            max_retries = 3
            
            for index, config in enumerate(configurations):
                result = None
                retry_count = 0
                retry_delay = 3  # Start with 3 second delay
                
                while retry_count < max_retries:
                    result = process_single_configuration(config, index, design_url)
                    
                    logger.info(f"Background: Config {index + 1} result: status={result.get('status')}, task_key={result.get('task_key')}, error={result.get('error')}")
                    
                    # Check if we got a rate limit error
                    if result.get("error") and "429" in str(result.get("error", "")):
                        retry_count += 1
                        logger.warning(f"Background: Rate limited on config {index + 1}, retry {retry_count}/{max_retries} after {retry_delay}s")
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                    else:
                        break
                
                results.append(result)
                
                # Update metadata after each config
                with open(metadata_path, "r") as f:
                    batch_metadata = json.load(f)
                
                if result.get("task_key"):
                    batch_metadata["task_keys"].append(result["task_key"])
                    batch_metadata["completed_indices"].append(index)
                else:
                    batch_metadata["failed_indices"].append(index)
                
                batch_metadata["pending_indices"] = [i for i in range(len(configurations)) if i not in batch_metadata["completed_indices"] and i not in batch_metadata["failed_indices"]]
                
                if batch_metadata["pending_indices"]:
                    batch_metadata["status"] = "processing"
                else:
                    batch_metadata["status"] = "completed"
                
                with open(metadata_path, "w") as f:
                    json.dump(batch_metadata, f, indent=2)
                
                # Add delay between requests to avoid rate limiting
                if index < len(configurations) - 1:
                    time.sleep(2.0)  # Reduced to 2 seconds for background processing
            
            logger.info(f"Background thread completed for batch {batch_id}. Processed {len(results)} configurations.")
        
        # Start background thread
        background_thread = threading.Thread(
            target=background_process_configs,
            args=(batch_id, configurations, design_url, batch_folder, metadata_path),
            daemon=True
        )
        background_thread.start()
        
        logger.info(f"Background thread started for batch {batch_id}")
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error creating batch mockups: {e}")
        logger.exception("Full stack trace:")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/batch-mockups", methods=["GET"])
def list_batch_mockups():
    """List all saved batch mockups."""
    logger.info("GET /api/batch-mockups - Listing all batches")
    
    try:
        batches = []
        
        # List all batch folders
        for batch_folder in os.listdir(MOCKUP_VARIATIONS_FOLDER):
            batch_path = os.path.join(MOCKUP_VARIATIONS_FOLDER, batch_folder)
            if os.path.isdir(batch_path):
                metadata_path = os.path.join(batch_path, "metadata.json")
                if os.path.exists(metadata_path):
                    with open(metadata_path, "r") as f:
                        metadata = json.load(f)
                        batches.append(metadata)
                else:
                    # Folder without metadata
                    batches.append({
                        "batch_id": batch_folder,
                        "created_at": datetime.fromtimestamp(os.path.getctime(batch_path)).isoformat(),
                        "status": "unknown"
                    })
        
        # Sort by created_at descending
        batches.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        
        return jsonify({
            "success": True,
            "batches": batches,
            "total": len(batches)
        })
        
    except Exception as e:
        logger.error(f"Error listing batches: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/batch-mockups/<batch_id>", methods=["GET"])
def get_batch_mockup(batch_id):
    """Get specific batch details and poll for results."""
    logger.info(f"GET /api/batch-mockups/{batch_id} - Getting batch details")
    
    try:
        batch_folder = os.path.join(MOCKUP_VARIATIONS_FOLDER, batch_id)
        
        if not os.path.exists(batch_folder):
            return jsonify({
                "success": False,
                "error": "Batch not found"
            }), 404
        
        # Load metadata
        metadata_path = os.path.join(batch_folder, "metadata.json")
        if os.path.exists(metadata_path):
            with open(metadata_path, "r") as f:
                metadata = json.load(f)
        else:
            metadata = {"batch_id": batch_id, "status": "unknown"}
        
        # Check if we need to poll for results
        task_keys = metadata.get("task_keys", [])
        
        if task_keys and metadata.get("status") == "processing":
            completed_variations = []
            pending_tasks = []
            
            for task_key in task_keys:
                try:
                    response = printful_client.get_task_result(task_key)
                    task_data = response.get("result", {})
                    status = task_data.get("status", "unknown")
                    
                    if status == "completed":
                        mockups_data = task_data.get("mockups", [])
                        for m in mockups_data:
                            if m.get("mockup_url"):
                                # Download and save the mockup
                                local_path = save_mockup_image(
                                    m.get("mockup_url"),
                                    batch_folder,
                                    len(completed_variations)
                                )
                                if local_path:
                                    variation = {
                                        "url": m.get("mockup_url"),
                                        "local_url": f"/mockup_variations/{batch_id}/{os.path.basename(local_path)}",
                                        "name": m.get("title", "Front"),
                                        "placement": metadata.get("configurations", [{}])[len(completed_variations)].get("placement", "front")
                                    }
                                    completed_variations.append(variation)
                    elif status == "pending" or status == "in_progress":
                        pending_tasks.append(task_key)
                    else:
                        # Failed or unknown
                        pass
                        
                except Exception as e:
                    logger.error(f"Error polling task {task_key}: {e}")
            
            # Update metadata
            metadata["variations"] = completed_variations
            metadata["pending_tasks"] = pending_tasks
            
            if pending_tasks:
                metadata["status"] = "processing"
            else:
                metadata["status"] = "completed" if completed_variations else "failed"
            
            # Save updated metadata
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)
        
        return jsonify({
            "success": True,
            "batch": metadata
        })
        
    except Exception as e:
        logger.error(f"Error getting batch: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/batch-mockups/<batch_id>", methods=["DELETE"])
def delete_batch_mockup(batch_id):
    """Delete a batch and its variations."""
    logger.info(f"DELETE /api/batch-mockups/{batch_id} - Deleting batch")
    
    try:
        batch_folder = os.path.join(MOCKUP_VARIATIONS_FOLDER, batch_id)
        
        if not os.path.exists(batch_folder):
            return jsonify({
                "success": False,
                "error": "Batch not found"
            }), 404
        
        # Delete folder and all contents
        import shutil
        shutil.rmtree(batch_folder)
        
        logger.info(f"Batch {batch_id} deleted")
        
        return jsonify({
            "success": True,
            "message": f"Batch {batch_id} deleted successfully"
        })
        
    except Exception as e:
        logger.error(f"Error deleting batch: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/batch-mockups/poll/<batch_id>", methods=["GET"])
def poll_batch_results(batch_id):
    """Poll for batch mockup results."""
    logger.info(f"GET /api/batch-mockups/poll/{batch_id} - Polling results")
    
    try:
        batch_folder = os.path.join(MOCKUP_VARIATIONS_FOLDER, batch_id)
        
        if not os.path.exists(batch_folder):
            return jsonify({
                "success": False,
                "error": "Batch not found"
            }), 404
        
        # Load metadata
        metadata_path = os.path.join(batch_folder, "metadata.json")
        with open(metadata_path, "r") as f:
            metadata = json.load(f)
        
        task_keys = metadata.get("task_keys", [])
        
        if not task_keys:
            return jsonify({
                "success": True,
                "batch": metadata,
                "progress": {
                    "completed": 0,
                    "pending": 0,
                    "failed": 0,
                    "total": 0
                }
            })
        
        completed_variations = []
        pending_tasks = []
        failed_tasks = []
        
        for i, task_key in enumerate(task_keys):
            try:
                response = printful_client.get_task_result(task_key)
                task_data = response.get("result", {})
                status = task_data.get("status", "unknown")
                
                if status == "completed":
                    mockups_data = task_data.get("mockups", [])
                    for m in mockups_data:
                        if m.get("mockup_url"):
                            # Check if already saved locally
                            existing_files = [f for f in os.listdir(batch_folder) if f.startswith(f"mockup_{i}_")]
                            
                            if not existing_files:
                                local_path = save_mockup_image(
                                    m.get("mockup_url"),
                                    batch_folder,
                                    i
                                )
                            else:
                                local_path = os.path.join(batch_folder, existing_files[0])
                            
                            config = metadata.get("configurations", [{}])[i] if i < len(metadata.get("configurations", [])) else {}
                            
                            variation = {
                                "url": m.get("mockup_url"),
                                "local_url": f"/mockup_variations/{batch_id}/{os.path.basename(local_path)}" if local_path else None,
                                "name": m.get("title", "Front"),
                                "placement": config.get("placement", "front"),
                                "position": {"x": config.get("x"), "y": config.get("y")},
                                "scale": config.get("scale"),
                                "rotation": config.get("rotation"),
                                "config_index": i
                            }
                            completed_variations.append(variation)
                            
                elif status == "pending" or status == "in_progress":
                    pending_tasks.append(task_key)
                else:
                    failed_tasks.append(task_key)
                    
            except Exception as e:
                logger.error(f"Error polling task {task_key}: {e}")
                failed_tasks.append(task_key)
        
        # Update metadata
        metadata["variations"] = completed_variations
        metadata["pending_tasks"] = pending_tasks
        metadata["failed_tasks"] = failed_tasks
        
        if pending_tasks:
            metadata["status"] = "processing"
            metadata["progress"] = f"{len(completed_variations)}/{len(task_keys)} completed"
        else:
            metadata["status"] = "completed" if completed_variations else "failed"
        
        # Save updated metadata
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)
        
        return jsonify({
            "success": True,
            "batch": metadata,
            "progress": {
                "completed": len(completed_variations),
                "pending": len(pending_tasks),
                "failed": len(failed_tasks),
                "total": len(task_keys)
            }
        })
        
    except Exception as e:
        logger.error(f"Error polling batch results: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "progress": {
                "completed": 0,
                "pending": 0,
                "failed": 0,
                "total": 0
            }
        }), 500


# ============================================================
# TEST ENDPOINT - Generate test batch with test.png
# ============================================================

@app.route("/api/batch-mockups/test", methods=["POST"])
def test_batch_mockups():
    """Test endpoint to generate batch mockups using test.png."""
    start_time = time.time()
    logger.info("POST /api/batch-mockups/test - Starting test batch")
    
    try:
        # Get test.png path
        test_png_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test.png")
        
        if not os.path.exists(test_png_path):
            return jsonify({
                "success": False,
                "error": "test.png not found in project root"
            }), 404
        
        logger.info(f"Found test.png at: {test_png_path}")
        
        # Upload to R2
        filename = "test.png"
        r2_result = r2_client.upload_file(test_png_path, filename)
        design_url = r2_result["public_url"]
        
        logger.info(f"Uploaded test.png to R2: {design_url}")
        
        # Create 4 test configurations as specified
        configurations = [
            {"name": "Center, 100%, 0°", "x": 50, "y": 50, "scale": 100, "rotation": 0, "placement": "front"},
            {"name": "Top-Left, 80%, 0°", "x": 30, "y": 30, "scale": 80, "rotation": 0, "placement": "front"},
            {"name": "Bottom-Right, 120%, 45°", "x": 70, "y": 70, "scale": 120, "rotation": 45, "placement": "front"},
            {"name": "Center, 150%, 90°", "x": 50, "y": 50, "scale": 150, "rotation": 90, "placement": "front"}
        ]
        
        # Create batch ID
        batch_id = f"test_batch_{uuid.uuid4().hex[:8]}_{int(time.time())}"
        batch_folder = create_batch_folder(batch_id)
        
        # Prepare batch metadata
        batch_metadata = {
            "batch_id": batch_id,
            "created_at": datetime.now().isoformat(),
            "design_url": design_url,
            "configurations": configurations,
            "variations": [],
            "status": "processing"
        }
        
        # Process configurations sequentially for better error handling
        results = []
        for index, config in enumerate(configurations):
            try:
                design_params = [{
                    "name": config["name"],
                    "x": config["x"],
                    "y": config["y"],
                    "scale": config["scale"],
                    "rotation": config["rotation"]
                }]
                
                logger.info(f"Creating mockup for config {index + 1}: {config}")
                logger.info(f"design_params: {design_params}")
                
                response = printful_client.create_mockup_task(
                    product_id=PRODUCT_ID,
                    variant_ids=[VARIANT_ID],
                    image_url=design_url,
                    design_params=design_params
                )
                
                logger.info(f"Printful response: {response}")
                
                task_key = response.get("task_key") or response.get("result", {}).get("task_key")
                logger.info(f"Task key: {task_key}")
                
                results.append({
                    "index": index,
                    "config": config,
                    "task_key": task_key,
                    "status": "created",
                    "error": None
                })
            except Exception as e:
                import traceback
                logger.error(f"Error creating mockup for config {index}: {e}")
                logger.error(traceback.format_exc())
                results.append({
                    "index": index,
                    "config": config,
                    "task_key": None,
                    "status": "error",
                    "error": str(e)
                })
        
        # Store task keys
        batch_metadata["task_keys"] = [r["task_key"] for r in results if r["task_key"]]
        
        # Save metadata
        metadata_path = os.path.join(batch_folder, "metadata.json")
        with open(metadata_path, "w") as f:
            json.dump(batch_metadata, f, indent=2)
        
        duration = (time.time() - start_time) * 1000
        logger.info(f"Test batch {batch_id} created in {duration:.2f}ms with {len(results)} configurations")
        
        return jsonify({
            "success": True,
            "batch_id": batch_id,
            "configurations_count": len(configurations),
            "task_keys": batch_metadata["task_keys"],
            "message": "Test batch created. Use GET /api/batch-mockups/poll/{batch_id} to check status."
        })
        
    except Exception as e:
        logger.error(f"Error creating test batch: {e}")
        logger.exception("Full stack trace:")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("Starting Flask development server")
    logger.info("=" * 60)
    app.run(debug=True, host="0.0.0.0", port=5000)
