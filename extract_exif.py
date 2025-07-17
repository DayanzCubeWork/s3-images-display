import json
import os
import subprocess
from PIL import Image
from PIL.ExifTags import TAGS

EXIFTOOL_PATH = os.path.join(os.path.dirname(__file__), 'exiftool', 'exiftool.exe')

def extract_exif(image_path):
    exif_data = {}
    try:
        with Image.open(image_path) as img:
            info = img._getexif()
            if info:
                for tag, value in info.items():
                    tag_name = TAGS.get(tag, tag)
                    # Convert all values to string for JSON serialization
                    exif_data[tag_name] = str(value)
                print(f'✅ Found EXIF data in {image_path}')
            else:
                print(f'⚠️ No EXIF data found in {image_path}')
    except Exception as e:
        print(f'❌ Error reading EXIF data from {image_path}: {e}')
    
    return exif_data

def extract_xmp_fields(image_path):
    xmp_fields = ['XMP:City', 'XMP:State', 'XMP:Location', 'XMP:PostalCode', 'XMP:Zipcode', 'XMP-xmp:ZipCode']
    xmp_data = {}
    try:
        # Use exiftool to extract XMP fields
        cmd = [
            EXIFTOOL_PATH,
            '-j',  # JSON output
        ] + [f'-{field}' for field in xmp_fields] + [image_path]
        
        # Debug print
        print(f"Running command: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0 and result.stdout:
            # Debug print
            print(f"ExifTool output: {result.stdout}")
            
            json_data = json.loads(result.stdout)
            if json_data and isinstance(json_data, list):
                for field in xmp_fields:
                    # exiftool returns keys without the 'XMP:' prefix, but for XMP-xmp:ZipCode, the key is 'xmp:ZipCode'
                    if field == 'XMP-xmp:ZipCode':
                        key = 'xmp:ZipCode'
                    else:
                        key = field.split(':')[1]
                    value = json_data[0].get(key)
                    if value is not None:
                        xmp_data[key] = value
        else:
            print(f'⚠️ exiftool did not return XMP data for {image_path}')
            if result.stderr:
                print(f'Error: {result.stderr}')
    except Exception as e:
        print(f'❌ Error extracting XMP data from {image_path}: {e}')
    return xmp_data

def process_images_folder(folder_path='images'):
    # Create output directory if it doesn't exist
    output_dir = os.path.join(folder_path, 'exif_data')
    os.makedirs(output_dir, exist_ok=True)
    
    # Get all image files
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.dng'}
    processed_count = 0
    success_count = 0
    
    for filename in os.listdir(folder_path):
        if any(filename.lower().endswith(ext) for ext in image_extensions):
            image_path = os.path.join(folder_path, filename)
            exif_data = extract_exif(image_path)
            xmp_data = extract_xmp_fields(image_path)
            combined_data = exif_data.copy()
            if xmp_data:
                combined_data['XMP'] = xmp_data
            
            if combined_data:
                # Save EXIF data to JSON file
                output_filename = f"{os.path.splitext(filename)[0]}_exif.json"
                output_path = os.path.join(output_dir, output_filename)
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(combined_data, f, indent=2, ensure_ascii=False)
                print(f'💾 EXIF+XMP data saved to {output_path}')
                success_count += 1
            
            processed_count += 1
    
    print(f'\n📊 Summary:')
    print(f'Total images processed: {processed_count}')
    print(f'Successfully extracted EXIF+XMP data: {success_count}')
    print(f'Failed: {processed_count - success_count}')

if __name__ == "__main__":
    process_images_folder() 