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

# Load environment variables
load_dotenv()

app = Flask(__name__)

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
    try:
        response = s3_client.list_objects_v2(
            Bucket=S3_BUCKET_NAME,
            Prefix=prefix,
            MaxKeys=max_keys
        )
        
        objects = []
        if 'Contents' in response:
            for obj in response['Contents']:
                # Skip metadata fetching for performance
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
        
        return sorted_folders
    except Exception as e:
        print(f"Error getting location folders: {e}")
        return []

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
        
        # Look through categories to find metadata (limit to first 3 categories for performance)
        for category in categories[:3]:
            objects = list_s3_objects(f"images/{location_folder}/{category}/", max_keys=3)
            for obj in objects:
                metadata = obj.get('metadata', {})
                if metadata.get('xmp-street') or metadata.get('xmp-city') or metadata.get('xmp-state'):
                    return {
                        'street': metadata.get('xmp-street', ''),
                        'city': metadata.get('xmp-city', ''),
                        'state': metadata.get('xmp-state', ''),
                        'zipcode': metadata.get('xmp-zipcode', ''),
                        'location': metadata.get('xmp-location', '')
                    }
        
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
        # Get location folders (cached)
        location_folders = cached_get_location_folders()
        
        # Get some basic stats (limited for performance)
        total_objects = 0
        total_size = 0
        
        # Get location details with metadata (limit to first 10 for performance)
        location_details = []
        for location in location_folders[:10]:
            # Get location details from metadata
            location_info = get_location_details_from_metadata(location)
            
            location_details.append({
                'folder': location,
                'street': location_info['street'],
                'city': location_info['city'],
                'state': location_info['state'],
                'zipcode': location_info['zipcode'],
                'location': location_info['location']
            })
            
            # Get stats from first 3 locations only
            if len(location_details) <= 3:
                objects = list_s3_objects(f"images/{location}/", max_keys=50)
                total_objects += len(objects)
                total_size += sum(obj['size'] for obj in objects)
        
        return render_template('index.html', 
                             location_folders=location_folders,
                             location_details=location_details,
                             total_objects=total_objects,
                             total_size=total_size)
    except Exception as e:
        return render_template('error.html', error=str(e))

@app.route('/location/<location_folder>')
def location_view(location_folder):
    """View images in a specific location"""
    try:
        categories = get_categories_in_location(location_folder)
        
        # Get location details from metadata
        location_info = get_location_details_from_metadata(location_folder)
        
        # Get sample images from each category
        category_samples = {}
        for category in categories:
            objects = list_s3_objects(f"images/{location_folder}/{category}/", max_keys=5)
            category_samples[category] = objects
        
        return render_template('location.html', 
                             location_folder=location_folder,
                             location_info=location_info,
                             categories=categories,
                             category_samples=category_samples)
    except Exception as e:
        return render_template('error.html', error=str(e))

@app.route('/location/<location_folder>/<category>')
def category_view(location_folder, category):
    """View all images in a specific category within a location"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 20
        offset = (page - 1) * per_page
        
        # Get location details from metadata
        location_info = get_location_details_from_metadata(location_folder)
        
        # Get all objects in this category
        objects = list_s3_objects(f"images/{location_folder}/{category}/")
        
        # Paginate
        total_objects = len(objects)
        total_pages = (total_objects + per_page - 1) // per_page
        paginated_objects = objects[offset:offset + per_page]
        
        return render_template('category.html',
                             location_folder=location_folder,
                             location_info=location_info,
                             category=category,
                             objects=paginated_objects,
                             page=page,
                             total_pages=total_pages,
                             total_objects=total_objects)
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

if __name__ == '__main__':
    # For development only - Render will use gunicorn
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000))) 