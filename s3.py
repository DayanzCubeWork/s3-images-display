import os
import json
import requests
import base64
import logging
from pathlib import Path
from typing import Optional, Dict, List, Tuple
import datetime
import traceback
import sys
from dotenv import load_dotenv
import boto3
from botocore.exceptions import ClientError

# Load environment variables from .env file if present
load_dotenv()

# Configuration: load from environment variables
NETWORK_PATH = os.getenv("NETWORK_PATH")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION", "us-west-1")

# Ensure required configuration is provided
if not NETWORK_PATH or not S3_BUCKET_NAME or not AWS_ACCESS_KEY_ID or not AWS_SECRET_ACCESS_KEY:
    print("❌ Missing required environment variables. Please set NETWORK_PATH, S3_BUCKET_NAME, AWS_ACCESS_KEY_ID, and AWS_SECRET_ACCESS_KEY in your environment or .env file.")
    sys.exit(1)

# Initialize S3 client
s3_client = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION
)

CATEGORIES = {
    "exterior_warehouse": ["warehouse exterior", "trucks",  "car", "parking", "tree", "building",  "warehouse", "parking lot",  "building", "tree", "clear sky", "sidewalk", "space", "glass door", "car", "entrance", "outdoor",  "clear", "warehouse building", "solar panel", "sky", "roof", "exterior", "flat roof", "open space", "birds eye view", "outside", "commercial building", "eye", "open", "view", "large", "storage facility", "space", "flat", "concrete surface", "loading dock", "shipping area", "receiving area", "exterior", "concrete floors", "metal beams", "industrial exterior", "warehouse facade", "vehicles", "distribution center exterior", "logistics facility exterior", "truck loading", "delivery bay", "warehouse compound"],
    
    "interior_warehouse": ["warehouse interior", "empty space", "empty", "pallet racking", "yellow equipment", "industrial area", "metal", "sheets", "high ceiling", "metal sheets", "aisle", "concrete floor", "unit",  "units","shelving",  "lights", "shelving units", "metal walls", "warehouse",  "industrial interior", "pallet jack", "interior", "metal walls",  "logistics", "distribution", "supply chain", "shelves", "storage unit", "warehouse shelves", "storage", "forklift", "forklifts", "cardboard boxes", "inventory", "pallets", "boxes", "stockroom", "fulfillment", "distribution center", "high-bay racking", "ceiling", "conveyor system", "bulk storage", "cross-docking", "material handling", "shelving units", "pallet racks", "staging area", "warehouse aisles", "storage shelves", "storage", "warehouse floor", "fork lift"],
    
    "interior_office": ["office interior", "cafe" , "tables", "green wall", "white ceiling", "office space", "blinds", "room", "office", "workspace", "modern office", "basketball", "hoop", "stylish office", "elegant office", "sophisticated office", "chairs", "desk", "chair", "table", "office furniture", "office supplies", "office equipment", "cabinet","recreation room", "game room", "pool table", "billiard table", "recreation area", "storage", "shelving", "blind shade", "floor lamp", "glass window", "windows", "blinds", "lobby", "reception", "reception area", "waiting area", "dining table", "entrance", "brand", "interior", "carpet", "modern", "computer", "tv", "workspace", "stylish", "elegant", "white walls", "sophisticated", "staircase", "wood", "wood flooring", "stairs", "furniture"],
    
    # "conference_room": ["conference room", "meeting room", "boardroom", "video conference", "conference table", "office meeting", "presentation room", "projector", "screen", "TV", "whiteboard", "seating", "chairs", "desk", "long table", "glass walls", "interior office", "office meeting space", "corporate meeting", "roundtable", "monitor", "remote meeting", "speakerphone", "teleconference", "zoom meeting", "business meeting", "formal seating", "presentation screen", "conference setup", "office chairs", "team meeting"],
    
    "parking_lot": ["parking lot", "parking", "parking area", "parking space", "cars", "vehicles", "parking lines", "outdoor parking", "parking facility", "car park", "parking garage", "vehicle parking", "parking spots", "parking structure", "pavement"],
    
    # "unis": ["unis", "logistics solutions", "supply chain optimization", "global logistics", "transportation", "shipping", "truck", "trailer", "container", "cargo", "transport logistics", "logistics company", "freight", "delivery", "logistics services"],
    
    "breakroom": ["breakroom", "break room", "kitchen", "commercial kitchen", "office break room", "break", "refrigerator", "sink", "coffee area", "lunch room", "employee kitchen", "cafeteria", "dining area", "microwave", "coffee machine", "kitchen appliances", "eating area", "staff kitchen", "break area"],
    
    "office_gym": ["office gym", "gym","workout room",  "fitness facility", "gym equipment", "treadmill", "elliptical", "weight room", "strength training", "cardio equipment", "exercise machines", "fitness studio", "workout area","gymnasium", "athletic facility"],
    
    "bathroom": ["bathroom", "restroom", "washroom", "toilet", "lavatory", "public restroom", "employee restroom", "facilities", "WC", "powder room", "men's room", "women's room", "unisex bathroom"],
    
    "company": ["corporate", "business", "startup", "enterprise", "organization", "firm", "management", "industry experts"],
    
    "e-commerce": ["online shopping", "e-commerce", "retail", "dropshipping", "marketplace", "digital store", "checkout", "cart", "customer orders"],
    
    "support": ["customer service", "helpdesk", "technical support", "assistance", "troubleshooting", "service center"],
    
    "resources": ["training", "learning materials", "guides", "knowledge base", "industry insights", "best practices"],
    
    "tracking_technology_platform": ["tracking", "gps", "rfid", "iot sensors", "analytics", "real-time monitoring", "asset tracking"],
    
    "marketing": ["advertising", "two women", "fashionable attire",  "logo", "signage", "work", "blazer", "blonde", "blonde hair", "white jacket" , "woman", " black pants", "attire", "dress", "streetwear", "high heels", "red dress", "sunglasses", "cube work", "sign", "sticker" ,"toy fork lift", "toy", "model", "toy forklift", "toy model", " remote control toy car", "lego truck", "miniature", "scale model", "polo shirt", "branded apparel", "promotional item",  "branded", "shirt", "black polo shirt", "black shirt", "embroidered","embroidered text", "logo on shirt", "polo", "cube work shirt", "t-shirt", "promotion", "branding", "social media", "marketing campaign", "seo", "content marketing", "email marketing"],
    
    "warehousing": ["logistics hub", "inventory management"],
    
    "item_com": ["item.com", "e-commerce solutions", "supply chain automation", "digital commerce"],
}

def get_image_description(image_path: str) -> Optional[str]:
    """Get AI-generated description using llama3.2-vision with a focus on concise, comma-separated keywords"""
    max_retries = 3
    base_timeout = 300  # Increased timeout for larger images

    for attempt in range(max_retries):
        try:
            print(f"📤 Reading image file: {image_path}")
            with open(image_path, "rb") as image_file:
                image_data = image_file.read()
                print(f"📊 Image size: {len(image_data) / (1024*1024):.2f} MB")
                base64_image = base64.b64encode(image_data).decode('utf-8')
            
            payload = {
                "model": "llava",
                "prompt": """Provide a list of keywords from the image, formatted as: keyword1, keyword2, keyword3, etc.
    Focus on the most prominent elements, limiting to 35 words. No introductory text, bullet points, or narrative.
    Be specific about location type: specify if it's interior or exterior for warehouses and offices.
    Be specific about object size: if the forklift is miniature/toy or full-size.
    Include any visible text, logos, or branding.""",
                "stream": False,
                "images": [base64_image]
            }

            print("🔄 Sending request to Ollama server...")
            response = requests.post(
                "http://localhost:11434/api/generate",
                json=payload,
                timeout=base_timeout
            )
            
            if response.status_code == 200:
                description = response.json().get('response', '').strip()
                print(f"🔎 Raw model output: {description}")

                # Post-process to ensure format and limit
                keywords = [kw.strip() for kw in description.split(',') if kw.strip()]
                
                # Limit to 35 keywords as specified
                keywords = keywords[:35]
                
                return ', '.join(keywords)
            
            else:
                print(f"❌ Error: HTTP {response.status_code} - {response.text}")

        except requests.exceptions.Timeout:
            print(f"⚠️ Timeout occurred on attempt {attempt + 1}/{max_retries}")
            if attempt < max_retries - 1:
                print("Retrying...")
        
        except Exception as e:
            print(f"❌ Description error on attempt {attempt + 1}/{max_retries}: {str(e)}")
            print(f"Error details: {traceback.format_exc()}")
            if attempt < max_retries - 1:
                print("Retrying...")

    print("❌ Failed to get description after multiple attempts")
    return None

def categorize_image(description: str) -> Tuple[str, Dict[str, int]]:
    """
    Categorize image based on description keywords
    Returns the category and a dictionary of match scores for debugging
    """
    if not description:
        print("⚠️ Warning: Empty description provided to categorizer")
        return "interior_warehouse", {"empty_description": 1}
    
    # Process description keywords - improved to handle various formats
    description = description.lower()
    # Handle both comma-separated and space-separated keywords
    description_keywords = set()
    
    # First try comma splitting
    if ',' in description:
        for kw in description.split(','):
            kw = kw.strip()
            if kw:
                description_keywords.add(kw)
                # Also add individual words for better matching
                for word in kw.split():
                    if len(word) > 2:  # Skip very short words
                        description_keywords.add(word)
    else:
        # If no commas, just use word splitting
        for word in description.split():
            if len(word) > 2:  # Skip very short words
                description_keywords.add(word)
    
    print(f"🔍 Extracted keywords: {', '.join(description_keywords)}")
    
    # Track match scores for each category
    match_scores = {}
    
    for category, keywords in CATEGORIES.items():
        # Process keywords in order, giving priority to longer/more specific keywords
        sorted_keywords = sorted(keywords, key=len, reverse=True)
        score = 0
        matches = []
        matched_keywords = set()  # Track what we've already matched
        
        for cat_keyword in sorted_keywords:
            # Check if this keyword is already covered by a longer keyword we matched
            already_covered = any(cat_keyword in longer_kw for longer_kw in matched_keywords)
            
            if not already_covered:
                # Check if category keyword is a direct match
                if cat_keyword in description_keywords:
                    score += 2
                    matches.append(cat_keyword)
                    matched_keywords.add(cat_keyword)
                else:
                    # Check if category keyword appears within any description keyword
                    for desc_keyword in description_keywords:
                        if cat_keyword in desc_keyword:
                            score += 1
                            matches.append(f"{cat_keyword}(in {desc_keyword})")
                            matched_keywords.add(cat_keyword)
                            break
        
        # Special priority for UNIS category when "unis" is detected
        if category == "unis" and "unis" in description_keywords:
            score += 5  # Extra bonus for UNIS detection
            matches.append("unis_priority_bonus")
        
        # Special bonus for toy/miniature terms in marketing category
        if category == "marketing":
            toy_miniature_terms = ['toy', 'miniature', 'model', 'scale model', 'toy model', 'miniature model', 'toy car', 'toy truck', 'toy forklift', 'remote control', 'lego']
            for term in toy_miniature_terms:
                if term in description_keywords:
                    score += 4  # Add 4 points for each toy/miniature term
                    matches.append(f"toy_miniature_bonus({term})")
        
        # Special bonus for refrigerator/fridge terms in breakroom category
        if category == "breakroom":
            fridge_terms = ['refrigerator', 'fridge', 'freezer', 'cooler', 'refrigerated']
            for term in fridge_terms:
                if term in description_keywords:
                    score += 3  # Add 3 bonus points for each fridge term
                    matches.append(f"fridge_bonus({term})")
        
        if score > 0:
            match_scores[category] = score
            print(f"  - Category '{category}' score: {score}, matches: {', '.join(matches)}")
    
    # Find highest scoring category
    if match_scores:
        best_category = max(match_scores.items(), key=lambda x: x[1])[0]
        print(f"✅ Best category match: {best_category} with score {match_scores[best_category]}")
        return best_category, match_scores
    
    # Default category with explanation
    print("⚠️ No category matches found in description")
    return "interior_warehouse", {"no_matches": 0}

def get_xmp_data(image_path: str) -> dict:
    """Get XMP data from image using ExifTool"""
    try:
        import subprocess
        # Check multiple zip code field names like extract_exif.py does
        xmp_fields = ['XMP:City', 'XMP:State', 'XMP:Location', 'XMP:PostalCode', 'XMP:Zipcode', 'XMP-xmp:ZipCode']
        
        cmd = ['./exiftool/exiftool.exe', '-j'] + [f'-{field}' for field in xmp_fields] + [image_path]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            if data and len(data) > 0:
                xmp_data = {}
                
                # Extract the fields we want
                for field in xmp_fields:
                    if field == 'XMP-xmp:ZipCode':
                        key = 'xmp:ZipCode'
                    else:
                        key = field.split(':')[1]
                    
                    value = data[0].get(key)
                    if value is not None:
                        if key in ['City', 'State', 'Location']:
                            xmp_data[key] = value
                        elif key in ['PostalCode', 'Zipcode', 'ZipCode']:
                            xmp_data['PostalCode'] = value  # Standardize to PostalCode
                
                # Extract street address from Location field
                if 'Location' in xmp_data:
                    location = xmp_data['Location']
                    # Extract street address from the beginning of the location string
                    # Format: "120 n 83rd ave, Tolleson, AZ, 85353"
                    import re
                    # Look for street address pattern at the beginning
                    street_match = re.match(r'^([^,]+)', location)
                    if street_match:
                        street = street_match.group(1).strip()
                        xmp_data['Street'] = street
                
                # Extract zip code from Location field if not found separately
                if 'PostalCode' not in xmp_data and 'Location' in xmp_data:
                    location = xmp_data['Location']
                    # Look for zip code pattern (5 digits) at the end of the location string
                    # Format: "120 n 83rd ave, Tolleson, AZ, 85353"
                    import re
                    # Look for zip code at the end, after the last comma
                    zip_match = re.search(r',\s*(\d{5})\s*$', location)
                    if zip_match:
                        xmp_data['PostalCode'] = zip_match.group(1)
                    else:
                        # Fallback: look for any 5-digit number that's not at the beginning (to avoid street numbers)
                        # This is more conservative and only matches if it's not the first number in the string
                        zip_match = re.search(r'(?<!^\d{1,4})\b(\d{5})\b', location)
                        if zip_match:
                            xmp_data['PostalCode'] = zip_match.group(1)
                
                return xmp_data
        return {}
    except Exception as e:
        print(f"Error getting XMP data: {e}")
        return {}

def generate_clean_filename(category: str, description: str, xmp_data: dict, original_extension: str = '.jpg') -> str:
    """
    Generate a clean filename based on category, street, city, state, and zip code.
    Preserves the original file extension.
    """
    # Get location data
    street = xmp_data.get('Street', '').lower()
    city = xmp_data.get('City', '').lower()
    state = xmp_data.get('State', '').lower()
    zipcode = xmp_data.get('PostalCode', '').lower()
    
    # Clean location data
    street = ''.join(c for c in street if c.isalnum()).replace(' ', '')  # Remove all non-alphanumeric chars and spaces
    city = ''.join(c for c in city if c.isalnum() or c.isspace()).replace(' ', '_')
    state = ''.join(c for c in state if c.isalnum() or c.isspace()).replace(' ', '_')
    zipcode = ''.join(c for c in zipcode if c.isalnum())  # Clean zip code
    
    # Build base filename with format: category_street_city_zipcode
    filename_parts = [category]
    if street:
        filename_parts.append(street)
    if city:
        filename_parts.append(city)
    if state:
        filename_parts.append(state)
    if zipcode:
        filename_parts.append(zipcode)
    
    # Join parts with underscores
    base_filename = '_'.join(filename_parts)
    
    return f"{base_filename}{original_extension}"

def create_location_folder(xmp_data: dict) -> str:
    """
    Create a location-based folder name from XMP data
    Returns a clean folder name like '120n83rdave_tolleson_az' or '123main_walnut_ca'
    """
    street = xmp_data.get('Street', '').lower()
    city = xmp_data.get('City', '').lower()
    state = xmp_data.get('State', '').lower()
    
    # Clean the data
    street = ''.join(c for c in street if c.isalnum()).replace(' ', '')  # Remove all non-alphanumeric chars and spaces
    city = ''.join(c for c in city if c.isalnum() or c.isspace()).replace(' ', '_')
    state = ''.join(c for c in state if c.isalnum() or c.isspace()).replace(' ', '_')
    
    # Build location folder name: street_city_state
    location_parts = []
    if street:
        location_parts.append(street)
    if city:
        location_parts.append(city)
    if state:
        location_parts.append(state)
    
    if location_parts:
        return '_'.join(location_parts)
    else:
        return "unknown_location"

def upload_to_s3(local_file_path: str, s3_key: str, description: str, category: str, xmp_data: dict) -> bool:
    """
    Upload image to S3 with metadata
    """
    try:
        # Clean and truncate description for S3 metadata
        # Remove newlines, extra spaces, and other invalid characters
        cleaned_description = description.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
        # Remove multiple spaces
        cleaned_description = ' '.join(cleaned_description.split())
        
        # Remove numbered list formatting (like "1. Industrial 2. Warehouse" etc.)
        import re
        cleaned_description = re.sub(r'\d+\.\s*', '', cleaned_description)
        
        # Remove common prefixes that make descriptions too long
        prefixes_to_remove = [
            "The image depicts ",
            "The image shows ",
            "Keywords: ",
            "The image ",
            "This image "
        ]
        for prefix in prefixes_to_remove:
            if cleaned_description.startswith(prefix):
                cleaned_description = cleaned_description[len(prefix):]
        
        # Truncate to 150 characters (more aggressive) to avoid "Invalid header value" errors
        truncated_description = cleaned_description[:150] + "..." if len(cleaned_description) > 150 else cleaned_description
        
        # Prepare metadata
        metadata = {
            'description': truncated_description,
            'category': category,
            'xmp-city': xmp_data.get('City', ''),
            'xmp-state': xmp_data.get('State', ''),
            'xmp-zipcode': xmp_data.get('PostalCode', ''),
            'xmp-street': xmp_data.get('Street', ''),
            'processing-timestamp': str(datetime.datetime.now().isoformat()),
            'original-filename': os.path.basename(local_file_path)
        }
        
        # Get content type
        content_type = 'image/jpeg'  # Default
        if local_file_path.lower().endswith('.png'):
            content_type = 'image/png'
        elif local_file_path.lower().endswith('.jpg') or local_file_path.lower().endswith('.jpeg'):
            content_type = 'image/jpeg'
        
        # Upload file with metadata
        with open(local_file_path, 'rb') as file:
            s3_client.upload_fileobj(
                file,
                S3_BUCKET_NAME,
                s3_key,
                ExtraArgs={
                    'Metadata': metadata,
                    'ContentType': content_type
                }
            )
        
        print(f"✅ Successfully uploaded to S3: {s3_key}")
        return True
        
    except ClientError as e:
        print(f"❌ S3 upload error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error during S3 upload: {e}")
        return False

def check_s3_file_exists(s3_key: str) -> bool:
    """Check if a file already exists in S3"""
    try:
        s3_client.head_object(Bucket=S3_BUCKET_NAME, Key=s3_key)
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            return False
        else:
            # Re-raise other errors
            raise e

def generate_unique_s3_key(base_s3_key: str) -> str:
    """
    Generate a unique S3 key by adding a number suffix if the file already exists
    Returns the first available unique key
    """
    if not check_s3_file_exists(base_s3_key):
        return base_s3_key
    
    # Split the key into path and filename with extension
    key_parts = base_s3_key.rsplit('/', 1)
    if len(key_parts) == 1:
        # No path, just filename
        path = ""
        filename_with_ext = key_parts[0]
    else:
        path = key_parts[0]
        filename_with_ext = key_parts[1]
    
    # Split filename and extension
    name_parts = filename_with_ext.rsplit('.', 1)
    if len(name_parts) == 1:
        # No extension
        base_name = name_parts[0]
        extension = ""
    else:
        base_name = name_parts[0]
        extension = "." + name_parts[1]
    
    # Try with number suffixes
    counter = 1
    while True:
        new_filename = f"{base_name}_{counter}{extension}"
        new_s3_key = f"{path}/{new_filename}" if path else new_filename
        
        if not check_s3_file_exists(new_s3_key):
            return new_s3_key
        
        counter += 1
        # Safety check to prevent infinite loop
        if counter > 1000:
            raise Exception(f"Could not generate unique filename after 1000 attempts for base key: {base_s3_key}")

def process_images_in_folder(folder_path: str):
    """Process all images in the folder and upload to S3 with detailed monitoring"""
    try:
        folder = Path(folder_path)
        print(f"\n📂 Processing folder: {folder}")
        
        # Collect all image files (only JPG, JPEG, PNG - LLaVA supported formats)
        image_extensions = {'.jpg', '.jpeg', '.png', '.cr2', '.dng'}
        image_files = [
            f for f in folder.rglob('*')
            if f.is_file() and f.suffix.lower() in image_extensions
        ]
        
        total_files = len(image_files)
        processed_count = 0
        skipped_count = 0
        failed_count = 0
        
        print(f"\n📊 Statistics:")
        print(f"Total images found: {total_files}")
        print(f"Starting processing...\n")
        
        results = []

        for image_path in image_files:
            processed_count += 1
            print(f"\n🖼️  Processing image {processed_count}/{total_files}")
            print(f"File: {image_path.name}")
            
            # Skip DNG and CR2 files
            if image_path.suffix.lower() in ['.dng', '.cr2']:
                print(f"⏭️  Skipping RAW file: {image_path.name}")
                skipped_count += 1
                continue
            
            # Check if file is already processed using sophisticated logic
            def is_already_processed(filename, show_debug=True):
                try:
                    name_without_ext = filename.rsplit('.', 1)[0]
                    
                    # Check if filename starts with any known category name
                    category_found = None
                    for category in CATEGORIES.keys():
                        if name_without_ext.startswith(category):
                            category_found = category
                            break
                    
                    if not category_found:
                        if show_debug:
                            print(f"🔍 Debug: No known category found - returning False (process)")
                        return False
                    
                    # Remove the category prefix and split the remaining parts
                    remaining = name_without_ext[len(category_found):].lstrip('_')
                    parts = remaining.split('_') if remaining else []
                    
                    if show_debug:
                        print(f"🔍 Debug: Category '{category_found}', remaining parts: {parts}")
                    
                    # Check if we have at least 3 parts (street_city_zipcode minimum)
                    if len(parts) >= 3:
                        # Determine which part is the zipcode
                        zipcode_part = None
                        has_counter = False
                        
                        # Check if the last part is a numeric counter
                        if len(parts) >= 4:
                            try:
                                int(parts[-1])
                                has_counter = True
                                zipcode_part = parts[-2]  # Second-to-last part is zipcode
                                if show_debug:
                                    print(f"🔍 Debug: Last part '{parts[-1]}' is counter, zipcode is '{zipcode_part}'")
                            except ValueError:
                                zipcode_part = parts[-1]  # Last part is zipcode
                                if show_debug:
                                    print(f"🔍 Debug: Last part '{parts[-1]}' is zipcode")
                        else:
                            zipcode_part = parts[-1]  # Last part is zipcode
                            if show_debug:
                                print(f"🔍 Debug: Last part '{parts[-1]}' is zipcode")
                        
                        # Check if the zipcode part looks like a zipcode (5 digits)
                        if zipcode_part and len(zipcode_part) == 5 and zipcode_part.isdigit():
                            if show_debug:
                                print(f"🔍 Debug: Zipcode '{zipcode_part}' is valid")
                            
                            # Check if any of the earlier parts contain numbers (indicating street address)
                            has_street_address = False
                            # Skip the last part (zipcode) and the second-to-last if it's a counter
                            end_index = len(parts) - 2 if has_counter else len(parts) - 1
                            for i in range(end_index):
                                if any(c.isdigit() for c in parts[i]):
                                    has_street_address = True
                                    break
                            
                            if has_street_address:
                                if show_debug:
                                    print(f"🔍 Debug: Has street address and valid zipcode - returning True (skip)")
                                # This is already processed (has street address and valid zipcode)
                                return True
                            else:
                                if show_debug:
                                    print(f"🔍 Debug: No street address found - returning False (process)")
                                # No street address, so this might be old format
                                return False
                        else:
                            if show_debug:
                                print(f"🔍 Debug: Zipcode part '{zipcode_part}' is not a 5-digit zipcode - returning False (process)")
                            return False
                    
                    if show_debug:
                        print(f"🔍 Debug: Filename has {len(parts)} remaining parts (not enough for new format) - returning False (process)")
                    # Old format files or insufficient parts will return False to allow reprocessing
                    return False
                except Exception as e:
                    if show_debug:
                        print(f"🔍 Debug: Exception in is_already_processed: {e}")
                    return False
            
            # Check if current filename is already processed
            if is_already_processed(image_path.name):
                print(f"⏭️  Skipping already processed file: {image_path.name}")
                skipped_count += 1
                continue
            
            # Also check if a file with the new naming pattern already exists in the directory
            # This prevents processing files that would create duplicates
            try:
                # Get XMP data first to check for existing files
                xmp_data = get_xmp_data(str(image_path))
                
                # Generate what the new filename would be
                street = xmp_data.get('Street', '').lower()
                city = xmp_data.get('City', '').lower()
                zipcode = xmp_data.get('PostalCode', '').lower()
                
                # Clean location data
                street = ''.join(c for c in street if c.isalnum()).replace(' ', '')
                city = ''.join(c for c in city if c.isalnum() or c.isspace()).replace(' ', '_')
                zipcode = ''.join(c for c in zipcode if c.isalnum())
                
                # Build filename parts
                filename_parts = []
                if street:
                    filename_parts.append(street)
                if city:
                    filename_parts.append(city)
                if zipcode:
                    filename_parts.append(zipcode)
                
                # Check if any file with the new pattern already exists
                for existing_file in image_path.parent.glob('*'):
                    if existing_file.is_file() and existing_file != image_path:
                        if is_already_processed(existing_file.name, show_debug=False):  # No debug for directory check
                            # This existing file already has the new naming pattern
                            # Check if it would have the same location-based name
                            existing_name = existing_file.stem
                            if '_' in existing_name:
                                existing_parts = existing_name.split('_')
                                if len(existing_parts) >= 4:
                                    # Check if the location parts match
                                    existing_location_parts = existing_parts[1:4]  # Skip category
                                    if existing_location_parts == filename_parts:
                                        print(f"⏭️  Skipping - would create duplicate with existing file: {existing_file.name}")
                                        skipped_count += 1
                                        continue
            except Exception as e:
                print(f"⚠️  Warning: Could not check for duplicates: {e}")
                # Continue processing anyway
                
            try:
                # Get image description
                print("🤖 Getting description...")
                description = get_image_description(str(image_path))
                if description:
                    print(f"📝 Description: {description}")
                else:
                    print("⚠️ No description generated")
                
                # Get category with improved categorization
                category, match_scores = categorize_image(description if description else "")
                print(f"🏷️  Category: {category}")
                
                # Get XMP data
                xmp_data = get_xmp_data(str(image_path))
                
                # Generate new filename with full location: category_street_city_zipcode
                street = xmp_data.get('Street', '').lower()
                city = xmp_data.get('City', '').lower()
                zipcode = xmp_data.get('PostalCode', '').lower()
                
                # Clean location data
                street = ''.join(c for c in street if c.isalnum()).replace(' ', '')  # Remove all non-alphanumeric chars and spaces
                city = ''.join(c for c in city if c.isalnum() or c.isspace()).replace(' ', '_')
                zipcode = ''.join(c for c in zipcode if c.isalnum())  # Clean zip code
                
                # Build filename parts
                filename_parts = [category]
                if street:
                    filename_parts.append(street)
                if city:
                    filename_parts.append(city)
                if zipcode:
                    filename_parts.append(zipcode)
                
                # Join parts with underscores and add extension
                base_filename = '_'.join(filename_parts)
                new_filename = f"{base_filename}{image_path.suffix}"
                print(f"📝 New filename: {new_filename}")
                
                # Create location-based folder
                location_folder = create_location_folder(xmp_data)
                print(f"📍 Location folder: {location_folder}")
                
                # Create S3 key (path in S3) - organized by images/location/category/filename
                s3_key = f"images/{location_folder}/{category}/{new_filename}"
                print(f"📍 S3 key: {s3_key}")
                
                # Generate unique S3 key to prevent duplicates
                unique_s3_key = generate_unique_s3_key(s3_key)
                if unique_s3_key != s3_key:
                    print(f"🔄 Duplicate detected, using unique key: {unique_s3_key}")
                    s3_key = unique_s3_key
                    # Extract the unique suffix from S3 key to use for local rename
                    s3_filename = unique_s3_key.split('/')[-1]
                    local_filename = s3_filename
                else:
                    local_filename = new_filename
                
                # Upload to S3 with metadata
                print("☁️  Uploading to S3...")
                success = upload_to_s3(str(image_path), s3_key, description, category, xmp_data)
                
                if success:
                    # Rename the original local file to match the S3 filename
                    try:
                        # Check if local filename already exists and generate unique name if needed
                        local_filename_final = local_filename
                        counter = 1
                        while True:
                            new_file_path = image_path.parent / local_filename_final
                            if not new_file_path.exists():
                                break
                            # Add number suffix to make it unique locally
                            name_parts = local_filename.rsplit('.', 1)
                            if len(name_parts) == 1:
                                base_name = name_parts[0]
                                extension = ""
                            else:
                                base_name = name_parts[0]
                                extension = "." + name_parts[1]
                            local_filename_final = f"{base_name}_{counter}{extension}"
                            counter += 1
                            if counter > 1000:  # Safety check
                                raise Exception(f"Could not generate unique local filename after 1000 attempts")
                        
                        image_path.rename(new_file_path)
                        print(f"✅ Renamed local file to: {local_filename_final}")
                        # Update the image_path reference for the result data
                        image_path = new_file_path
                    except Exception as e:
                        print(f"⚠️ Could not rename local file: {str(e)}")
                    
                    # Prepare result data
                    result_data = {
                        's3_key': s3_key,
                        'local_file': str(image_path),
                        'description': description if description else f"Image from {category} category",
                        'category': category,
                        'location_folder': location_folder,
                        'uploaded_at': datetime.datetime.now().isoformat(),
                        'metadata': {
                            'xmp_data': xmp_data,
                            'processing_info': {
                                'has_description': bool(description),
                                'description_length': len(description.split(',')) if description else 0,
                                'original_filename': image_path.name
                            },
                            'category_matches': match_scores
                        }
                    }
                    results.append(result_data)
                    print("✅ Successfully processed and uploaded to S3")
                else:
                    print("❌ Failed to upload to S3")
                    failed_count += 1

            except Exception as e:
                print(f"❌ Error: {str(e)}")
                logging.error(traceback.format_exc())
                failed_count += 1
                continue
            
            # Show progress summary
            success_count = processed_count - failed_count - skipped_count
            print(f"\n📊 Progress Summary:")
            print(f"Processed: {processed_count}/{total_files}")
            print(f"Successful: {success_count}")
            print(f"Skipped: {skipped_count}")
            print(f"Failed: {failed_count}")
            print(f"Success Rate: {(success_count/processed_count)*100:.1f}%" if processed_count > 0 else "N/A")
            print("-" * 50)

        # Save results to JSON
        if results:
            output_file = folder / 's3_location_processed_images.json'
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            print(f"\n💾 Results saved to: {output_file}")
            
        # Final summary
        print(f"\n🎯 Final Results:")
        print(f"Total Images: {total_files}")
        print(f"Successfully Processed: {len(results)}")
        print(f"Skipped: {skipped_count}")
        print(f"Failed: {failed_count}")
        if total_files > 0:
            print(f"Overall Success Rate: {(len(results)/total_files)*100:.1f}%")

    except Exception as e:
        print(f"❌ Error during processing: {str(e)}")
        logging.error(traceback.format_exc())

def test_ollama_connection() -> bool:
    """Check if the Ollama server is running and accessible"""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            print("✅ Ollama server is running")
            return True
        else:
            print(f"❌ Unexpected response status: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Ollama server connection error: {str(e)}")
        return False

def test_s3_connection() -> bool:
    """Test S3 connection and bucket access"""
    try:
        # Test bucket access
        s3_client.head_bucket(Bucket=S3_BUCKET_NAME)
        print(f"✅ S3 bucket '{S3_BUCKET_NAME}' is accessible")
        return True
    except ClientError as e:
        print(f"❌ S3 connection error: {e}")
        return False

def validate_categories() -> None:
    """Validate that categories don't have overlapping keywords that could cause confusion"""
    overlaps = []
    for cat1, keywords1 in CATEGORIES.items():
        for cat2, keywords2 in CATEGORIES.items():
            if cat1 != cat2:
                common_keywords = set(keywords1).intersection(set(keywords2))
                if common_keywords:
                    overlaps.append(f"Categories '{cat1}' and '{cat2}' share keywords: {', '.join(common_keywords)}")
    
    if overlaps:
        print("\n⚠️ Warning: Category keyword overlaps detected:")
        for overlap in overlaps:
            print(f"  - {overlap}")
        print("This may cause inconsistent categorization.")
    else:
        print("\n✅ Category keywords are unique with no overlaps")

if __name__ == "__main__":
    try:
        print("🚀 Starting S3 Location-Based Image Processing System...")
        
        # Check Ollama first
        if not test_ollama_connection():
            exit(1)
        
        # Test S3 connection
        if not test_s3_connection():
            exit(1)
        
        # Validate categories for potential issues
        validate_categories()
        
        print(f"\n📂 Checking network path: {NETWORK_PATH}")
        if not os.path.exists(NETWORK_PATH):
            print(f"❌ Cannot access {NETWORK_PATH}")
            print("Please check your network connection")
            exit(1)
            
        print("✅ Network connection successful")
        process_images_in_folder(NETWORK_PATH)
        print("\n✨ S3 Location-Based Processing completed!")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        logging.error(traceback.format_exc()) 