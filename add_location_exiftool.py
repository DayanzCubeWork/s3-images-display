import json
import subprocess
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

# Full path to ExifTool executable
EXIFTOOL_PATH = r"./exiftool/exiftool.exe"

def add_location_exiftool(image_path, city, state, zipcode, location_name, street_address):
    """
    Add location data to an image using ExifTool
    :param image_path: Path to the image
    :param city: City name
    :param state: State code
    :param zipcode: ZIP code
    :param location_name: Full location name
    :param street_address: Street address
    """
    try:
        # Create full location string that includes street address
        full_location = f"{street_address}, {city}, {state}, {zipcode}"
        
        # Construct the ExifTool command
        # -overwrite_original to modify the file in place
        # -XMP:Location for the full location name (including street address)
        # -XMP:City for the city
        # -XMP:State for the state
        # -XMP:Street for the street address
        # -XMP:PostalCode for the zipcode (standard XMP field)
        cmd = [
            EXIFTOOL_PATH,
            '-overwrite_original',
            f'-XMP:Location={full_location}',
            f'-XMP:City={city}',
            f'-XMP:State={state}',
            f'-XMP:Street={street_address}',
            f'-XMP:PostalCode={zipcode}',
            str(image_path)
        ]
        print(f"Running command: {' '.join(cmd)}")  # Debug print
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ Successfully added location data to {image_path}")
            print(f"   Street: {street_address}")
            print(f"   Full Location: {full_location}")
            return True
        else:
            print(f"❌ Error adding location data to {image_path}")
            print(f"Error: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def process_images(locations_file):
    """
    Process all images with location data from the JSON file
    :param locations_file: Path to the JSON file containing location data
    """
    # Load location data
    with open(locations_file, 'r') as f:
        locations = json.load(f)
    
    # Get network path from environment variable
    network_path = os.getenv("NETWORK_PATH")
    if not network_path:
        print("❌ NETWORK_PATH environment variable not set. Please set it in your .env file or environment.")
        return
    
    network_dir = Path(network_path)
    if not network_dir.exists():
        print(f"❌ Network path not found: {network_path}")
        return
    
    print(f"📂 Using network path for ExifTool: {network_path}")
    
    # Process each image
    for image_name, location_data in locations.items():
        # Try to find the file with different extensions
        image_path = None
        possible_extensions = ['.jpg', '.JPG', '.jpeg', '.JPEG', '.png', '.PNG']
        
        # First try the exact name from JSON
        exact_path = network_dir / image_name
        if exact_path.exists():
            image_path = exact_path
        else:
            # If exact name doesn't exist, try with different extensions
            base_name = Path(image_name).stem  # Remove extension
            for ext in possible_extensions:
                test_path = network_dir / f"{base_name}{ext}"
                if test_path.exists():
                    image_path = test_path
                    print(f"📝 Found file with different extension: {test_path.name} (instead of {image_name})")
                    break
            
        if image_path and image_path.exists():
            add_location_exiftool(
                image_path,
                location_data['city'],
                location_data['state'],
                location_data['zipcode'],
                location_data['location_name'],
                location_data['Street']
            )
        else:
            print(f"⚠️ Image not found: {image_name} (tried all extensions)")

if __name__ == "__main__":
    # Check if ExifTool is installed
    if not os.path.exists(EXIFTOOL_PATH):
        print(f"❌ ExifTool not found at: {EXIFTOOL_PATH}")
        print("Please make sure ExifTool is installed at the correct location")
        exit(1)
        
    # Process images using the locations file
    process_images('image_locations.json') 