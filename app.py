from flask import Flask, render_template, request, jsonify, redirect, url_for
import boto3
import os
from datetime import datetime
from dotenv import load_dotenv
import json
from botocore.exceptions import ClientError
from typing import List, Dict, Optional
from functools import lru_cache
import time
import threading

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Simple in-memory cache
_cache = {}
_cache_lock = threading.Lock()

def get_cached(key, ttl_seconds=300):
    """Get value from cache with TTL"""
    with _cache_lock:
        if key in _cache:
            value, timestamp = _cache[key]
            if time.time() - timestamp < ttl_seconds:
                return value
            else:
                del _cache[key]
    return None

def set_cached(key, value, ttl_seconds=300):
    """Set value in cache with TTL"""
    with _cache_lock:
        _cache[key] = (value, time.time())
        # Clean old entries if cache gets too big
        if len(_cache) > 100:
            current_time = time.time()
            _cache.clear()  # Simple cleanup for now

# S3 Configuration
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION", "us-west-1")

# Initialize S3 client with timeout
s3_client = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION,
    config=boto3.session.Config(
        connect_timeout=30,
        read_timeout=30,
        retries={'max_attempts': 2}
    )
)

# Cache for expensive operations
@lru_cache(maxsize=32)
def cached_list_s3_objects(prefix: str, max_keys: int = 1000) -> List[Dict]:
    """Cached version of list_s3_objects to reduce API calls"""
    return list_s3_objects(prefix, max_keys)

def list_s3_objects(prefix: str = "", max_keys: int = 1000) -> List[Dict]:
    """List objects in S3 bucket with optional prefix"""
    # Check cache first
    cache_key = f"s3_objects_{prefix}_{max_keys}"
    cached_result = get_cached(cache_key, ttl_seconds=600)  # Cache for 10 minutes
    if cached_result:
        return cached_result
    
    try:
        response = s3_client.list_objects_v2(
            Bucket=S3_BUCKET_NAME,
            Prefix=prefix,
            MaxKeys=max_keys
        )
        
        objects = []
        if 'Contents' in response:
            for obj in response['Contents']:
                # Get object metadata (re-enabled for better address info)
                try:
                    head_response = s3_client.head_object(
                        Bucket=S3_BUCKET_NAME,
                        Key=obj['Key']
                    )
                    metadata = head_response.get('Metadata', {})
                except:
                    metadata = {}
                
                # Generate presigned URL for viewing (expires in 1 hour)
                try:
                    presigned_url = s3_client.generate_presigned_url(
                        'get_object',
                        Params={'Bucket': S3_BUCKET_NAME, 'Key': obj['Key']},
                        ExpiresIn=3600
                    )
                except:
                    presigned_url = None
                
                objects.append({
                    'key': obj['Key'],
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'].isoformat(),
                    'metadata': metadata,
                    'presigned_url': presigned_url,
                    'filename': obj['Key'].split('/')[-1]
                })
        
        # Cache the result
        set_cached(cache_key, objects, ttl_seconds=600)
        return objects
    except Exception as e:
        print(f"Error listing S3 objects: {e}")
        return []

@lru_cache(maxsize=16)
def cached_get_location_folders() -> List[str]:
    """Cached version of get_location_folders"""
    return get_location_folders()

def get_location_folders() -> List[str]:
    """Get all location folders from S3, sorted alphabetically by state"""
    # Check cache first
    cache_key = "location_folders"
    cached_result = get_cached(cache_key, ttl_seconds=900)  # Cache for 15 minutes
    if cached_result:
        return cached_result
    
    try:
        response = s3_client.list_objects_v2(
            Bucket=S3_BUCKET_NAME,
            Prefix="images/",
            Delimiter='/'
        )
        
        folders = []
        if 'CommonPrefixes' in response:
            for prefix in response['CommonPrefixes']:
                folder_name = prefix['Prefix'].replace('images/', '').replace('/', '')
                if folder_name:
                    folders.append(folder_name)
        
        # Sort by state (last part of the folder name)
        def extract_state(folder_name):
            parts = folder_name.split('_')
            if len(parts) >= 3:
                return parts[-1]  # Last part is the state
            return folder_name  # Fallback to full name if can't parse
        
        # Sort folders by state, then by full name for locations in same state
        sorted_folders = sorted(folders, key=lambda x: (extract_state(x), x))
        
        # Cache the result
        set_cached(cache_key, sorted_folders, ttl_seconds=900)
        return sorted_folders
    except Exception as e:
        print(f"Error getting location folders: {e}")
        return []

@lru_cache(maxsize=32)
def cached_get_categories_in_location(location_folder: str) -> List[str]:
    """Cached version of get_categories_in_location"""
    return get_categories_in_location(location_folder)

def get_categories_in_location(location_folder: str) -> List[str]:
    """Get all categories within a location folder"""
    try:
        response = s3_client.list_objects_v2(
            Bucket=S3_BUCKET_NAME,
            Prefix=f"images/{location_folder}/",
            Delimiter='/'
        )
        
        categories = []
        if 'CommonPrefixes' in response:
            for prefix in response['CommonPrefixes']:
                category_name = prefix['Prefix'].split('/')[-2]
                if category_name:
                    categories.append(category_name)
        
        return sorted(categories)
    except Exception as e:
        print(f"Error getting categories: {e}")
        return []

def get_location_details_from_metadata(location_folder: str) -> Dict:
    """Get location details from metadata of images in this location"""
    try:
        # Get all categories in this location
        categories = get_categories_in_location(location_folder)
        
        # Look through categories to find metadata (ultra-fast search)
        for category in categories[:2]:  # Only check first 2 categories
            objects = list_s3_objects(f"images/{location_folder}/{category}/", max_keys=2)  # Only check first 2 images
            for obj in objects:
                metadata = obj.get('metadata', {})
                if metadata.get('xmp-street') or metadata.get('xmp-city') or metadata.get('xmp-state'):
                    result = {
                        'street': metadata.get('xmp-street', ''),
                        'city': metadata.get('xmp-city', ''),
                        'state': metadata.get('xmp-state', ''),
                        'zipcode': metadata.get('xmp-zipcode', ''),
                        'location': metadata.get('xmp-location', '')
                    }
                    return result
        
        # If no metadata found, try to parse from folder name
        # Handle various folder name formats
        if '_' in location_folder:
            parts = location_folder.split('_')
            
            # Handle format: "long_beach_ca" -> "Long Beach, CA"
            if len(parts) >= 2:
                # Check if last part is a state abbreviation (2 letters)
                last_part = parts[-1].lower()
                if len(last_part) == 2 and last_part in ['ca', 'az', 'nv', 'tx', 'fl', 'ny', 'il', 'pa', 'oh', 'ga', 'nc', 'mi', 'nj', 'va', 'wa', 'or', 'co', 'mn', 'wi', 'md', 'mo', 'tn', 'in', 'ma', 'ct', 'sc', 'la', 'al', 'ky', 'ut', 'ia', 'ar', 'ms', 'ks', 'ne', 'id', 'hi', 'nh', 'me', 'ri', 'mt', 'de', 'sd', 'nd', 'ak', 'vt', 'wy', 'wv']:
                    # Everything except the last part is the location name
                    location_name = '_'.join(parts[:-1])
                    state = parts[-1].upper()
                    
                    # Try to separate city and street if possible
                    location_parts = location_name.split('_')
                    if len(location_parts) >= 2:
                        # Assume first part might be street direction/name, rest is city
                        street = location_parts[0].title()
                        city = ' '.join(location_parts[1:]).title()
                    else:
                        street = ''
                        city = location_name.replace('_', ' ').title()
                    
                    result = {
                        'street': street,
                        'city': city,
                        'state': state,
                        'zipcode': '',
                        'location': f"{city}, {state}" if city else f"{state}"
                    }
                    
                    print(f"Parsed address for {location_folder}: {result}")
                    return result
                
                # Handle format: "n83rdave_tolleson_az" -> "N 83rd Ave, Tolleson, AZ"
                elif len(parts) >= 3:
                    street_part = parts[0]
                    if street_part.startswith('n') and len(street_part) > 1:
                        street = f"N {street_part[1:]} Ave"
                    elif street_part.startswith('s') and len(street_part) > 1:
                        street = f"S {street_part[1:]} Ave"
                    elif street_part.startswith('e') and len(street_part) > 1:
                        street = f"E {street_part[1:]} Ave"
                    elif street_part.startswith('w') and len(street_part) > 1:
                        street = f"W {street_part[1:]} Ave"
                    else:
                        street = street_part.title()
                    
                    city = parts[1].title()
                    state = parts[2].upper()
                    
                    result = {
                        'street': street,
                        'city': city,
                        'state': state,
                        'zipcode': '',
                        'location': f"{street}, {city}, {state}"
                    }
                    
                    print(f"Parsed address for {location_folder}: {result}")
                    return result
        
        # Fallback: return empty dict if no metadata found
        return {
            'street': '',
            'city': '',
            'state': '',
            'zipcode': '',
            'location': ''
        }
    except Exception as e:
        print(f"Error getting location details for {location_folder}: {e}")
        return {
            'street': '',
            'city': '',
            'state': '',
            'zipcode': '',
            'location': ''
        }

@app.route('/')
def index():
    """Main dashboard page"""
    try:
        # Get ALL location folders (no limit)
        location_folders = cached_get_location_folders()
        
        # Get basic stats without loading all images
        total_objects = 0
        total_size = 0
        
        # Get location details with metadata (load all folders but limit metadata search)
        location_details = []
        for location in location_folders:  # No limit - show all folders
            # Get location details from metadata (optimized search)
            location_info = get_location_details_from_metadata(location)
            
            location_details.append({
                'folder': location,
                'street': location_info['street'],
                'city': location_info['city'],
                'state': location_info['state'],
                'zipcode': location_info['zipcode'],
                'location': location_info['location']
            })
            
            # Only calculate stats for first 5 locations to avoid timeout
            if len(location_details) <= 5:
                objects = list_s3_objects(f"images/{location}/", max_keys=50)
                total_objects += len(objects)
                total_size += sum(obj['size'] for obj in objects)
        
        # Estimate total objects based on first 5 locations
        if len(location_folders) > 5:
            avg_objects_per_location = total_objects / 5
            estimated_total = int(avg_objects_per_location * len(location_folders))
            total_objects = estimated_total
        
        return render_template('index.html', 
                             location_folders=location_folders,
                             location_details=location_details,
                             total_objects=total_objects,
                             total_size=total_size)
    except Exception as e:
        return render_template('error.html', error=str(e))

@app.route('/location/<location_folder>')
def location_view(location_folder):
    """View images in a specific location - Fast loading version"""
    try:
        print(f"Loading location view for: {location_folder}")
        
        # Get categories quickly (cached)
        categories = cached_get_categories_in_location(location_folder)
        print(f"Found {len(categories)} categories: {categories}")
        
        # Get location details from metadata (cached)
        location_info = get_location_details_from_metadata(location_folder)
        print(f"Location info: {location_info}")
        
        # Don't load any images here - just return the page structure
        # Images will be loaded via AJAX after page loads
        
        return render_template('location_fast.html', 
                             location_folder=location_folder,
                             location_info=location_info,
                             categories=categories)
    except Exception as e:
        print(f"Error in location_view for {location_folder}: {e}")
        return render_template('error.html', error=str(e))

@app.route('/location/<location_folder>/<category>')
def category_view(location_folder, category):
    """View all images in a specific category within a location - Fast loading version"""
    try:
        # Get location details from metadata (cached)
        location_info = get_location_details_from_metadata(location_folder)
        
        # Don't load any images here - just return the page structure
        # Images will be loaded via AJAX with pagination
        
        return render_template('category_fast.html',
                             location_folder=location_folder,
                             location_info=location_info,
                             category=category)
    except Exception as e:
        return render_template('error.html', error=str(e))

@app.route('/search')
def search():
    """Search images by filename or metadata"""
    query = request.args.get('q', '').lower()
    if not query:
        return redirect(url_for('index'))
    
    try:
        # Search through all objects
        all_objects = list_s3_objects("images/", max_keys=1000)
        
        # Filter by query
        filtered_objects = []
        for obj in all_objects:
            # Search in filename
            if query in obj['filename'].lower():
                filtered_objects.append(obj)
                continue
            
            # Search in metadata
            metadata_str = json.dumps(obj['metadata']).lower()
            if query in metadata_str:
                filtered_objects.append(obj)
                continue
            
            # Search in description
            description = obj['metadata'].get('description', '').lower()
            if query in description:
                filtered_objects.append(obj)
        
        return render_template('search.html',
                             query=query,
                             objects=filtered_objects,
                             result_count=len(filtered_objects))
    except Exception as e:
        return render_template('error.html', error=str(e))

@app.route('/api/objects')
def api_objects():
    """API endpoint to get objects"""
    prefix = request.args.get('prefix', '')
    max_keys = request.args.get('max_keys', 100, type=int)
    
    try:
        objects = list_s3_objects(prefix, max_keys)
        return jsonify(objects)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats')
def api_stats():
    """API endpoint to get basic stats"""
    try:
        location_folders = get_location_folders()
        
        stats = {
            'total_locations': len(location_folders),
            'total_objects': 0,
            'total_size': 0,
            'locations': []
        }
        
        for location in location_folders:
            categories = get_categories_in_location(location)
            location_objects = 0
            location_size = 0
            
            for category in categories:
                objects = list_s3_objects(f"images/{location}/{category}/", max_keys=100)
                location_objects += len(objects)
                location_size += sum(obj['size'] for obj in objects)
            
            stats['locations'].append({
                'name': location,
                'categories': len(categories),
                'objects': location_objects,
                'size': location_size
            })
            
            stats['total_objects'] += location_objects
            stats['total_size'] += location_size
        
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/location/<location_folder>/images')
def api_location_images(location_folder):
    """API endpoint to get all images in a location with pagination"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    category = request.args.get('category', '')
    
    try:
        if category:
            # Get images from specific category
            prefix = f"images/{location_folder}/{category}/"
        else:
            # Get images from all categories
            prefix = f"images/{location_folder}/"
        
        # Get all objects in this location/category
        all_objects = list_s3_objects(prefix)
        
        # Paginate
        total_objects = len(all_objects)
        total_pages = (total_objects + per_page - 1) // per_page
        offset = (page - 1) * per_page
        paginated_objects = all_objects[offset:offset + per_page]
        
        return jsonify({
            'objects': paginated_objects,
            'page': page,
            'total_pages': total_pages,
            'total_objects': total_objects,
            'per_page': per_page
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/location/<location_folder>/categories')
def api_location_categories(location_folder):
    """API endpoint to get category data for a location"""
    try:
        categories = cached_get_categories_in_location(location_folder)
        
        category_data = []
        for category in categories:
            # Get sample images and count quickly
            sample_objects = list_s3_objects(f"images/{location_folder}/{category}/", max_keys=3)
            all_objects = list_s3_objects(f"images/{location_folder}/{category}/", max_keys=1000)
            
            category_data.append({
                'name': category,
                'display_name': category.replace('_', ' ').title(),
                'sample_images': sample_objects,
                'total_images': len(all_objects)
            })
        
        return jsonify({
            'location_folder': location_folder,
            'categories': category_data
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/location/<location_folder>/<category>/images')
def api_category_images(location_folder, category):
    """API endpoint to get images in a category with pagination"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)  # Small batches for speed
    
    try:
        # Get all objects in this category
        all_objects = list_s3_objects(f"images/{location_folder}/{category}/")
        
        # Paginate
        total_objects = len(all_objects)
        total_pages = (total_objects + per_page - 1) // per_page
        offset = (page - 1) * per_page
        paginated_objects = all_objects[offset:offset + per_page]
        
        return jsonify({
            'objects': paginated_objects,
            'page': page,
            'total_pages': total_pages,
            'total_objects': total_objects,
            'per_page': per_page,
            'has_more': page < total_pages
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # For development only - Render will use gunicorn
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000))) 