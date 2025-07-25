# Local Vision Model Image Describer

A tool for processing images with location data and generating descriptions using LLaVA (Local Large Vision Assistant), with S3 storage and MySQL database integration.

## Features

- Add location metadata to images using ExifTool
- Process images with LLaVA for image description
- Upload images to AWS S3 with organized folder structure
- Store metadata in MySQL database
- Convert RAW files to JPEG format
- Intelligent categorization based on image content
- Skip already processed files to avoid duplicates

## Prerequisites

- Python 3.8 or higher
- Ollama with LLaVA model installed
- AWS S3 bucket and credentials
- MySQL database
- ImageMagick (for RAW file conversion)

## Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Install ImageMagick (for RAW file conversion):

For Windows:
- Visit https://imagemagick.org/script/download.php#windows
- Download the Windows installer (e.g., ImageMagick-7.1.1-Q16-HDRI-x64-dll.exe)
- Run the installer and follow the setup wizard
- Default installation path: `C:\Program Files\ImageMagick-7.1.1-Q16-HDRI\magick.exe`
- Note: The script is configured to use this default path

For Mac:
```bash
brew install imagemagick
```

For Linux (Ubuntu/Debian):
```bash
sudo apt-get update
sudo apt-get install imagemagick
```

3. Install Ollama and LLaVA:

For Windows:
- Visit https://ollama.ai/download
- Click "Download for Windows"
- Run the downloaded .exe installer
- Follow the installation wizard
- Open a new terminal and run:
```bash
ollama pull llava
```

For Mac/Linux:
```bash
# Install Ollama
curl https://ollama.ai/install.sh | sh

# Pull LLaVA model
ollama pull llava
```

4. Set up AWS S3:
   - Create an S3 bucket for storing images
   - Create an IAM user with S3 access
   - Get your AWS Access Key ID and Secret Access Key

5. Set up MySQL database:
   - Create a MySQL database
   - Create a table for storing image metadata:
   ```sql
   CREATE TABLE processed_images (
     id INT AUTO_INCREMENT PRIMARY KEY,
     s3_key VARCHAR(500),
     local_file VARCHAR(500),
     description TEXT,
     category VARCHAR(100),
     location_folder VARCHAR(200),
     uploaded_at DATETIME,
     metadata JSON
   );
   ```

6. Set up environment variables:
Create a `.env` file with your credentials:
```
NETWORK_PATH=Y:\Backup - .41\FinalPhotos
S3_BUCKET_NAME=your-s3-bucket-name
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_REGION=us-west-1
MYSQL_HOST=localhost
MYSQL_USER=your_mysql_user
MYSQL_PASSWORD=your_mysql_password
MYSQL_DATABASE=your_database_name
```

Note: ExifTool is already included in the `exiftool` directory of this project. No additional installation is needed. ImageMagick needs to be installed separately as described above.

## Usage

The tool consists of several components that can be run in sequence:

1. Add location metadata to images:
```bash
python add_location_exiftool.py
```
This will add location metadata to all images using ExifTool.

2. Convert RAW files to JPEG:
```bash
python magic_conversion.py
```
This will convert RAW files (CR2, DNG) to JPEG format for processing.

3. Create image location data:
```bash
python create_image_location.py
```
This will create a JSON file with location data for all images.

4. Process images with LLaVA and upload to S3:
```bash
python s3.py
```
This will process the images with LLaVA, generate descriptions, categorize them, and upload to S3 with organized folder structure.

## Project Structure

```
.
├── images/                  # Directory for input images
├── exiftool/               # ExifTool executable and files
├── add_location_exiftool.py # Add location metadata to images
├── magic_conversion.py     # Convert RAW files to JPEG
├── create_image_location.py # Create location data JSON
├── s3.py                   # Main processing script (LLaVA + S3 upload)
├── Image_server_llm_s3_location.py # Alternative processing script
└── requirements.txt        # Python dependencies
```

## Features

### Image Processing
- **LLaVA Integration**: Uses LLaVA model for AI-powered image description
- **RAW Conversion**: Converts CR2/DNG files to JPEG for processing
- **Location Metadata**: Extracts and adds location data using ExifTool
- **Intelligent Categorization**: Automatically categorizes images based on content

### S3 Storage
- **Organized Structure**: Images stored as `images/location/category/filename`
- **Metadata Storage**: Rich metadata including descriptions and location data
- **Duplicate Prevention**: Skips already processed files
- **Unique Naming**: Generates unique filenames to prevent conflicts

### Database Integration
- **MySQL Storage**: Stores processing metadata and results
- **Query Support**: Easy to query processed images and metadata
- **Audit Trail**: Tracks when images were processed and uploaded

## Dependencies

- Core:
  - requests==2.31.0
  - python-dotenv==1.0.0
  - boto3==1.34.0
  - mysql-connector-python==8.2.0
  - pathlib==1.0.1

- Image Processing:
  - Pillow>=10.0.0
  - python-magic>=0.4.27
  - ollama>=0.1.6

## Categories

The system automatically categorizes images into the following categories:
- `exterior_warehouse`: Warehouse exteriors, parking lots, loading docks
- `interior_warehouse`: Warehouse interiors, storage areas, equipment
- `interior_office`: Office spaces, workspaces, furniture
- `conference_room`: Meeting rooms, presentation areas
- `parking_lot`: Parking areas, vehicles
- `breakroom`: Kitchens, refrigerators, dining areas
- `office_gym`: Fitness facilities, workout equipment
- `bathroom`: Restrooms, facilities
- `marketing`: Promotional materials, branded items
- `unis`: UNIS-related content
- And more...

## File Naming Convention

Processed images are renamed using the format:
`category_street_city_state_zipcode.ext`

Example: `interior_warehouse_2470airportblvd_aurora_co_80011.jpg`
#   s 3 - i m a g e s - d i s p l a y  
 # s3-images-display
