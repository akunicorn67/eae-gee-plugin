import os
import boto3, requests
from dotenv import load_dotenv
from io import BytesIO
from datetime import datetime

# Load the variables from the .env file
load_dotenv()

S3_BUCKET = os.getenv("S3_BUCKET")

def upload_gee_to_s3(image, region, folder, prefix):
    s3 = boto3.client('s3')
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{prefix}_{timestamp}.tif"
    s3_key = f"{folder}/{filename}"

    url = image.getDownloadURL({
        'name': filename.replace('.tif', ''),
        'scale': 1000,
        'crs': 'EPSG:4326',
        'format': 'GEO_TIFF',
        'region': region.getInfo()['coordinates']
    })
    
    print("☁️ Streaming image from GEE to S3...")

    resp = requests.get(url)
    if resp.status_code == 200:
        s3.put_object(
            Bucket=S3_BUCKET,
            Key=s3_key,
            Body=BytesIO(resp.content),
            ContentType='image/tiff')
        return (f"https://{S3_BUCKET}.s3.amazonaws.com/{s3_key}").replace(' ','%20')
    
    return None
