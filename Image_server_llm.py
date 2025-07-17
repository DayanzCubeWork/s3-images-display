import os
import json
import requests
import base64
import logging
from pathlib import Path
from supabase import create_client
from typing import Optional, Dict, List, Tuple
import datetime
import traceback
import sys
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

# Configuration: load from environment variables
NETWORK_PATH = os.getenv("NETWORK_PATH")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Ensure required configuration is provided
if not NETWORK_PATH or not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Missing required environment variables. Please set NETWORK_PATH, SUPABASE_URL, and SUPABASE_KEY in your environment or .env file.")
    sys.exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

CATEGORIES = {
    "exterior_warehouse": ["warehouse exterior", "trucks",  "car", "parking", "tree", "building",  "warehouse", "parking lot",  "building", "tree", "clear sky", "sidewalk", "space", "glass door", "car", "entrance", "outdoor",  "clear", "warehouse building", "solar panel", "sky", "roof", "exterior", "flat roof", "open space", "birds eye view", "outside", "commercial building", "eye", "open", "view", "large", "storage facility", "space", "flat", "concrete surface", "loading dock", "shipping area", "receiving area", "exterior", "concrete floors", "metal beams", "industrial exterior", "warehouse facade", "vehicles", "distribution center exterior", "logistics facility exterior", "truck loading", "delivery bay", "warehouse compound"],
    
    "interior_warehouse": ["warehouse interior", "industrial area", "metal", "sheets", "high ceiling", "metal sheets", "aisle", "concrete floor", "unit",  "units","shelving",  "lights", "shelving units", "metal walls", "warehouse",  "industrial interior", "pallet jack", "interior", "metal walls",  "logistics", "distribution", "supply chain", "shelves", "storage unit", "warehouse shelves", "storage", "forklift", "forklifts", "cardboard boxes", "inventory", "pallets", "boxes", "stockroom", "fulfillment", "distribution center", "high-bay racking", "ceiling", "conveyor system", "bulk storage", "cross-docking", "material handling", "shelving units", "pallet racks", "staging area", "warehouse aisles", "storage shelves", "storage", "warehouse floor", "fork lift"],
    
    "interior_office": ["office interior", "office", "workspace", "modern office", "basketball", "hoop", "stylish office", "elegant office", "sophisticated office", "chairs", "desk", "chair", "table", "office furniture", "office supplies", "office equipment", "cabinet","recreation room", "game room", "pool table", "billiard table", "recreation area", "storage", "shelving", "blind shade", "floor lamp", "glass window", "windows", "blinds", "lobby", "reception", "reception area", "waiting area", "dining table", "entrance", "brand", "interior", "carpet", "modern", "computer", "tv", "workspace", "stylish", "elegant", "white walls", "sophisticated", "staircase", "wood", "wood flooring", "stairs", "furniture"],
    
    "conference_room": ["conference room", "meeting room", "boardroom", "video conference", "conference table", "office meeting", "presentation room", "projector", "screen", "TV", "whiteboard", "seating", "chairs", "desk", "long table", "glass walls", "interior office", "office meeting space", "corporate meeting", "roundtable", "monitor", "remote meeting", "speakerphone", "teleconference", "zoom meeting", "business meeting", "formal seating", "presentation screen", "conference setup", "office chairs", "team meeting"],
    
    "parking_lot": ["parking lot", "parking", "parking area", "parking space", "cars", "vehicles", "parking lines", "outdoor parking", "parking facility", "car park", "parking garage", "vehicle parking", "parking spots", "parking structure", "pavement"],
    
    "unis": ["unis", "logistics solutions", "supply chain optimization", "global logistics", "transportation", "shipping", "truck", "trailer", "container", "cargo", "transport logistics", "logistics company", "freight", "delivery", "logistics services"],
    
    "breakroom": ["breakroom", "break room", "kitchen", "refrigerator", "sink", "coffee area", "lunch room", "employee kitchen", "cafeteria", "dining area", "microwave", "coffee machine", "kitchen appliances", "eating area", "staff kitchen", "break area"],
    
    "office_gym": ["office gym", "gym","workout room",  "fitness facility", "gym equipment", "treadmill", "elliptical", "weight room", "strength training", "cardio equipment", "exercise machines", "fitness studio", "workout area","gymnasium", "athletic facility"],
    
    "bathroom": ["bathroom", "restroom", "washroom", "toilet", "lavatory", "public restroom", "employee restroom", "facilities", "WC", "powder room", "men's room", "women's room", "unisex bathroom"],
    
    "company": ["corporate", "business", "startup", "enterprise", "organization", "firm", "management", "industry experts"],
    
    "e-commerce": ["online shopping", "e-commerce", "retail", "dropshipping", "marketplace", "digital store", "checkout", "cart", "customer orders"],
    
    "support": ["customer service", "helpdesk", "technical support", "assistance", "troubleshooting", "service center"],
    
    "resources": ["training", "learning materials", "guides", "knowledge base", "industry insights", "best practices"],
    
    "tracking_technology_platform": ["tracking", "gps", "rfid", "iot sensors", "analytics", "real-time monitoring", "asset tracking"],
    
    "marketing": ["advertising", "logo", "signage", "work", "blazer", "blonde", "blonde hair", "white jacket" , "woman", "high heels", "red dress", "sunglasses", "cube work", "sign", "sticker" ,"toy fork lift", "toy", "model", "toy forklift", "toy model", " remote control toy car", "lego truck", "miniature", "scale model", "polo shirt", "branded apparel", "promotional item",  "branded", "shirt", "black polo shirt", "black shirt", "embroidered","embroidered text", "logo on shirt", "polo", "cube work shirt", "t-shirt", "promotion", "branding", "social media", "marketing campaign", "seo", "content marketing", "email marketing"],
    
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
                            xmp_data['ZipCode'] = value  # Standardize to ZipCode
                
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
                if 'ZipCode' not in xmp_data and 'Location' in xmp_data:
                    location = xmp_data['Location']
                    # Look for zip code pattern (5 digits) in location
                    import re
                    zip_match = re.search(r'\b(\d{5})\b', location)
                    if zip_match:
                        xmp_data['ZipCode'] = zip_match.group(1)
                
                return xmp_data
        return {}
    except Exception as e:
        print(f"Error getting XMP data: {e}")
        return {}

def generate_clean_filename(category: str, description: str, xmp_data: dict, existing_files: set, original_extension: str = '.jpg', directory_path: str = None) -> str:
    """
    Generate a clean filename based on category, street, city, state, and zip code.
    If a file with the same name exists (in database or directory), append a number.
    Preserves the original file extension.
    """
    # Get location data
    street = xmp_data.get('Street', '').lower()
    city = xmp_data.get('City', '').lower()
    state = xmp_data.get('State', '').lower()
    zipcode = xmp_data.get('ZipCode', '').lower()  # Extract zip code from XMP data
    
    # Clean location data
    street = ''.join(c for c in street if c.isalnum()).replace(' ', '')  # Remove all non-alphanumeric chars and spaces
    city = ''.join(c for c in city if c.isalnum() or c.isspace()).replace(' ', '_')
    state = ''.join(c for c in state if c.isalnum() or c.isspace()).replace(' ', '_')
    zipcode = ''.join(c for c in zipcode if c.isalnum())  # Clean zip code (remove spaces, keep only alphanumeric)
    
    # Build base filename with new format: category_street_city_state_zipcode
    filename_parts = [category]
    if street:
        filename_parts.append(street)
    if city:
        filename_parts.append(city)
    if state:
        filename_parts.append(state)
    if zipcode:  # Add zip code to filename parts
        filename_parts.append(zipcode)
    
    # Join parts with underscores
    base_filename = '_'.join(filename_parts)
    
    # Check if filename exists (both in database and directory) and add number if needed
    filename = f"{base_filename}{original_extension}"
    counter = 1
    
    print(f"🔍 Checking filename availability for base: {base_filename}")
    
    while True:
        # Check if filename exists in Supabase database
        if filename in existing_files:
            print(f"  ❌ '{filename}' exists in Supabase database")
            filename = f"{base_filename}_{counter}{original_extension}"
            counter += 1
            continue
        
        # Check if filename exists in local directory
        if directory_path:
            file_path = Path(directory_path) / filename
            if file_path.exists():
                print(f"  ❌ '{filename}' exists in local directory")
                filename = f"{base_filename}_{counter}{original_extension}"
                counter += 1
                continue
        
        # If we get here, filename is unique
        print(f"  ✅ '{filename}' is available")
        break
    
    return filename

def is_already_processed(filename: str) -> bool:
    """
    Check if an image has already been processed by checking its filename format.
    Returns True only if the filename follows the new pattern with street address: 
    category_street_city_state_zipcode.jpg (5 parts) or category_street_city_state_zipcode_counter.jpg (6 parts)
    Old format files (category_city_state_zipcode_counter - 5 parts without street) will return False to allow reprocessing.
    """
    try:
        # Remove file extension
        name_without_ext = os.path.splitext(filename)[0]
        
        print(f"🔍 Debug: Checking filename '{filename}'")
        
        # Check if filename starts with any known category name
        category_found = None
        for category in CATEGORIES.keys():
            if name_without_ext.startswith(category):
                category_found = category
                break
        
        if not category_found:
            print(f"🔍 Debug: No known category found - returning False (process)")
            return False
        
        # Remove the category prefix and split the remaining parts
        remaining = name_without_ext[len(category_found):].lstrip('_')
        parts = remaining.split('_') if remaining else []
        
        print(f"🔍 Debug: Category '{category_found}', remaining parts: {parts}")
        
        # New format with street address requires 4 or 5 remaining parts:
        # 4 parts: street_city_state_zipcode
        # 5 parts: street_city_state_zipcode_counter
        if len(parts) == 4 or len(parts) == 5:
            # Check if the last part is a number (counter) for 5-part format
            if len(parts) == 5:
                try:
                    int(parts[-1])
                    print(f"🔍 Debug: 5 remaining parts with numeric counter - returning True (skip)")
                    # This is category_street_city_state_zipcode_counter format (new format)
                    return True
                except ValueError:
                    print(f"🔍 Debug: 5 remaining parts with non-numeric last part - returning False (process)")
                    # Last part is not a number, so this is not the expected new format
                    return False
            else:
                # 4 parts: need to check if it has a street address
                # Street addresses typically contain numbers (like 120n83rdave)
                # Old format: city_state_zipcode (no numbers in middle parts)
                # New format: street_city_state_zipcode (street has numbers)
                
                # Check if any part (except the last) contains numbers (indicating street address)
                has_street_address = False
                for i in range(len(parts) - 1):  # Skip last (zipcode)
                    if any(c.isdigit() for c in parts[i]):
                        has_street_address = True
                        break
                
                if has_street_address:
                    print(f"🔍 Debug: 4 remaining parts with street address - returning True (skip)")
                    # This is category_street_city_state_zipcode format (new format)
                    return True
                else:
                    print(f"🔍 Debug: 4 remaining parts without street address - returning False (process)")
                    # This is category_city_state_zipcode format (old format)
                    return False
        
        print(f"🔍 Debug: Filename has {len(parts)} remaining parts (not 4 or 5) - returning False (process)")
        # Old format files (3 parts or other formats) 
        # will return False to allow reprocessing
        return False
    except Exception as e:
        print(f"🔍 Debug: Exception in is_already_processed: {e}")
        return False

def process_images_in_folder(folder_path: str):
    """Process all images in the folder and upload to Supabase with detailed monitoring"""
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
        
        # Fetch already processed images from Supabase
        archived_images = supabase.table('images').select('image_file').execute()
        archived_image_files = {record['image_file'] for record in archived_images.data}
        print(f"🗄️ Found {len(archived_image_files)} already processed images in database")

        for image_path in image_files:
            processed_count += 1
            print(f"\n🖼️  Processing image {processed_count}/{total_files}")
            print(f"File: {image_path.name}")
            
            # Check if image is already processed
            if is_already_processed(image_path.name):
                print(f"⏭️  Skipping already processed image: {image_path.name}")
                skipped_count += 1
                continue
            
            # Skip DNG and CR2 files
            if image_path.suffix.lower() in ['.dng', '.cr2']:
                print(f"⏭️  Skipping RAW file: {image_path.name}")
                skipped_count += 1
                continue
                
            try:
                # Create network path
                relative_path = str(image_path.relative_to(Path(NETWORK_PATH)))
                network_path = f"{NETWORK_PATH}\\{relative_path}"
                formatted_path = network_path.replace('\\', '/')
                print(f"📍 Path: {formatted_path}")
                
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
                
                # Generate new filename
                new_filename = generate_clean_filename(category, description if description else "", xmp_data, archived_image_files, image_path.suffix, str(image_path.parent))
                print(f"📝 New filename: {new_filename}")
                
                # Rename the physical file
                new_file_path = image_path.parent / new_filename
                try:
                    image_path.rename(new_file_path)
                    print(f"✅ Renamed file to: {new_filename}")
                    # Update the network path to reflect the new filename
                    relative_path = str(new_file_path.relative_to(Path(NETWORK_PATH)))
                    formatted_path = f"{NETWORK_PATH}/{relative_path}".replace('\\', '/')
                except Exception as e:
                    print(f"⚠️ Could not rename file: {str(e)}")
                    formatted_path = network_path.replace('\\', '/')
                
                # Add to archived files set to prevent duplicates within this session
                archived_image_files.add(new_filename)
                
                # Get current timestamp
                created_at = datetime.datetime.now().isoformat()
                
                # Prepare image data
                image_data = {
                    'image_file': new_filename,
                    'image_path': formatted_path,
                    'description': description if description else f"Image from {category} category",
                    'category': category,
                    'created_at': created_at,
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

                # Upload to Supabase
                print("☁️  Uploading to Supabase...")
                result = supabase.table('images').insert(image_data).execute()
                
                if result.data:
                    image_data['id'] = result.data[0].get('id')
                    results.append(image_data)
                    print("✅ Successfully processed and uploaded")
                else:
                    print("❌ Failed to upload to Supabase")
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
            output_file = folder / 'processed_images.json'
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
        print("🚀 Starting image processing system...")
        
        # Check Ollama first
        if not test_ollama_connection():
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
        print("\n✨ Processing completed!")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        logging.error(traceback.format_exc())