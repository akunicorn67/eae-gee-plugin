# This scrip calculates the average land surface temperature for the region for the previous month

import ee
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

# load the variable from th .env file
load_dotenv()

#EE_PROJECT = 'braided-course-483916-s9'
EE_PROJECT = os.getenv("EE_PROJECT")

def get_gee_data():
    # Initialize Earth Engine
    ee.Initialize(project=EE_PROJECT)

    """Define the GEE logic and metadata here."""
    # 1. Geometry (Bounding Box) and time variables
    region = ee.Geometry.Rectangle([89.6, 24.1, 96.2, 28.1]) # Assam

    today = datetime.now()
    first_day_this_month = today.replace(day=1)
    last_month_end = first_day_this_month - timedelta(days=1)
    last_month_start = last_month_end.replace(day=1)
    prev_month = last_month_end.strftime("%B %Y")
    
    # 2. GEE Logic
    collection = ee.ImageCollection("MODIS/061/MOD11A1") \
                   .filterDate(last_month_start.strftime('%Y-%m-%d'), 
                               last_month_end.strftime('%Y-%m-%d')) \
                   .select('LST_Day_1km')
    # Calculate Mean and convert Kelvin to Celsius: (Raw * 0.02) - 273.15
    mean_lst = collection.mean().multiply(0.02).subtract(273.15).clip(region)

    image = mean_lst

    # 3. Metadata for S3 and EAE
    config = {
        "long_name": f"Land Surface Temperature ({prev_month})",
        "metadata": f"This layer provides the mean land surface temperature values for the previous month for Assam.\n\nAt present it is providinoviding the mean LST values of Assam for the month of {prev_month}.",
        "s3_folder": "EnergyAccess/IND/assam/Climate",
        "file_prefix": f"Assam_average_LST_{prev_month}",
        "eae_dataset_url": "https://admin.energyaccessexplorer.org/admin/?model=datasets&geography_id=bb80d8a8-f478-409a-94f3-e7ac8d6c85bc&edit_model=3b67dcff-a124-46e5-9510-c515a20a7671"
    }
    
    return image, region, config

