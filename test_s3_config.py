import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("🔍 S3 Configuration Test")
print("=" * 40)

# Check each environment variable
network_path = os.getenv("NETWORK_PATH")
s3_bucket = os.getenv("S3_BUCKET_NAME")
aws_key = os.getenv("AWS_ACCESS_KEY_ID")
aws_secret = os.getenv("AWS_SECRET_ACCESS_KEY")
aws_region = os.getenv("AWS_REGION")

print(f"📂 NETWORK_PATH: {network_path}")
print(f"🪣 S3_BUCKET_NAME: {s3_bucket}")
print(f"🔑 AWS_ACCESS_KEY_ID: {aws_key[:10]}..." if aws_key else "❌ Not set")
print(f"🔐 AWS_SECRET_ACCESS_KEY: {aws_secret[:10]}..." if aws_secret else "❌ Not set")
print(f"🌍 AWS_REGION: {aws_region}")

print("\n✅ All variables loaded successfully!" if all([network_path, s3_bucket, aws_key, aws_secret, aws_region]) else "\n❌ Some variables are missing!")

# Test S3 connection
try:
    import boto3
    from botocore.exceptions import ClientError
    
    print("\n🔗 Testing S3 Connection...")
    
    s3_client = boto3.client(
        's3',
        aws_access_key_id=aws_key,
        aws_secret_access_key=aws_secret,
        region_name=aws_region
    )
    
    # Test bucket access
    s3_client.head_bucket(Bucket=s3_bucket)
    print(f"✅ Successfully connected to S3 bucket: {s3_bucket}")
    
except ImportError:
    print("❌ boto3 not installed. Run: pip install boto3")
except ClientError as e:
    print(f"❌ S3 connection failed: {e}")
except Exception as e:
    print(f"❌ Error: {e}") 