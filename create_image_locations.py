import json
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

def get_location_info():
    """Get location information from user input"""
    print("\nEnter location information for all images:")
    city = input("City: ").strip()
    state = input("State (e.g., CA): ").strip()
    zipcode = input("Zipcode: ").strip()
    street_address = input("Street Address (e.g., '1234 Main St'): ").strip()
    
    return {
        "city": city,
        "state": state,
        "zipcode": zipcode,
        "Street": street_address,
        "location_name": f"{city}, {state}"
    }

def check_existing_location(image_name):
    """Check if image already has location data in EXIF"""
    # Get the file extension from the image name
    file_extension = Path(image_name).suffix
    exif_file = Path(f'images/exif_data/{image_name.replace(file_extension, "_exif.json")}')
    if exif_file.exists():
        try:
            with open(exif_file, 'r') as f:
                data = json.load(f)
                print(f"\nChecking EXIF data for {image_name}:")
                
                # Check for location data in XMP
                if 'XMP' in data:
                    xmp = data['XMP']
                    print("Found XMP section with fields:", list(xmp.keys()))
                    
                    # Check if all required location fields exist
                    if all(key in xmp for key in ['City', 'State', 'Location', 'Street']):
                        print("Found complete location data:")
                        print(f"City: {xmp['City']}")
                        print(f"State: {xmp['State']}")
                        print(f"Street: {xmp['Street']}")
                        print(f"Location: {xmp['Location']}")
                        return True
                    else:
                        missing = [key for key in ['City', 'State', 'Location', 'Street'] if key not in xmp]
                        print(f"Missing location fields: {missing}")
                else:
                    print("No XMP section found in EXIF data")
                        
        except Exception as e:
            print(f"Error reading EXIF data for {image_name}: {e}")
    else:
        print(f"No EXIF file found for {image_name}")
    return False

def create_image_locations():
    """Create image locations JSON file"""
    image_data = {}
    
    # Get network path from environment variable
    network_path = os.getenv("NETWORK_PATH")
    if not network_path:
        print("❌ NETWORK_PATH environment variable not set. Please set it in your .env file or environment.")
        return
    
    images_dir = Path(network_path)
    
    if not images_dir.exists():
        print(f"❌ Network path not found: {network_path}")
        print("Please check your NETWORK_PATH setting in the .env file")
        return
    
    print(f"📂 Using network path: {network_path}")
    
    # Get all image files with various extensions
    image_files = []
    extensions = ['*.jpg', '*.JPG', '*copy.jpg', '*.png']
    for ext in extensions:
        image_files.extend(images_dir.glob(ext))
    
    # Remove duplicates by converting to set and back to list
    image_files = list(set(image_files))
    
    if not image_files:
        print("No images found in the network directory")
        return
    
    print(f"\nFound {len(image_files)} unique images:")
    for img in sorted(image_files):
        print(f"- {img.name}")
    
    print("\nYou will be prompted to enter location information once.")
    print("This information will be applied to all images in the folder.")
    
    # Get location info once
    location_info = get_location_info()
    
    # Apply location info to all images
    print("\nAdding location data to images:")
    for image_file in sorted(image_files):
        # Skip DNG and CR2 files
        if image_file.suffix.lower() in ['.dng', '.cr2']:
            print(f"⏭️  Skipping RAW file: {image_file.name}")
            continue
            
        print(f"Processing: {image_file.name}")
        image_data[image_file.name] = location_info
    
    # Save the data to JSON file
    output_file = 'image_locations.json'
    with open(output_file, 'w') as f:
        json.dump(image_data, f, indent=4)
    
    print(f"\nImage location data saved to {output_file}")
    print(f"Added location data to {len(image_data)} images")
    
    # List all files in the network directory for verification
    print("\nAll files in network directory:")
    for file in sorted(images_dir.iterdir()):
        print(f"- {file.name}")

def main():
    # Create locations file
    create_image_locations()
    
    # After creating locations file, run add_location_exiftool.py
    print("\nRunning add_location_exiftool.py to add location data to images...")
    try:
        from add_location_exiftool import process_images
        process_images('image_locations.json')
        print("✅ Successfully added location data to images")
    except Exception as e:
        print(f"❌ Error adding location data to images: {str(e)}")

if __name__ == "__main__":
    main() 

    