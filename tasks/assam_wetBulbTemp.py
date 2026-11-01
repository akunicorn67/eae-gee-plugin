import ee
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

EE_PROJECT = os.getenv("EE_PROJECT")

def get_gee_data():
    # Initialize Earth Engine
    ee.Initialize(project=EE_PROJECT)

    # -----------------------------------------------------
    # 1. Geometry (Assam Bounding Box) and Date Variables
    # -----------------------------------------------------
    region = ee.Geometry.Rectangle([89.6, 24.1, 96.2, 28.1])

    today = datetime.now()
    first_day_this_month = today.replace(day=1)
    last_month_end = first_day_this_month - timedelta(days=1)
    last_month_start = last_month_end.replace(day=1)

    prev_month = last_month_end.strftime("%B %Y")

    # -----------------------------------------------------
    # 2. GEE Logic
    # ERA5-Land Monthly Temperature & Dew Point
    # -----------------------------------------------------
    collection = (
        ee.ImageCollection("ECMWF/ERA5_LAND/MONTHLY_AGGR")
        .filterDate(
            last_month_start.strftime('%Y-%m-%d'),
            first_day_this_month.strftime('%Y-%m-%d')
        )
    )

    # Monthly mean air temperature (K → °C)
    temp = (
        collection
        .select('temperature_2m')
        .mean()
        .subtract(273.15)
    )

    # Monthly mean dew point temperature (K → °C)
    dewpoint = (
        collection
        .select('dewpoint_temperature_2m')
        .mean()
        .subtract(273.15)
    )

    # -----------------------------------------------------
    # Relative Humidity Calculation
    # -----------------------------------------------------
    rh = (
        dewpoint.expression(
            '''
            100 * (
              exp((17.625 * Td) / (243.04 + Td))
              /
              exp((17.625 * T) / (243.04 + T))
            )
            ''',
            {
                'Td': dewpoint,
                'T': temp
            }
        )
        .max(0)
        .min(100)
    )

    # -----------------------------------------------------
    # Stull (2011) Wet Bulb Temperature Approximation
    # -----------------------------------------------------
    wetbulb = ee.Image().expression(
        '''
        T * atan(0.151977 * sqrt(RH + 8.313659))
        + atan(T + RH)
        - atan(RH - 1.676331)
        + 0.00391838 * pow(RH, 1.5) * atan(0.023101 * RH)
        - 4.686035
        ''',
        {
            'T': temp,
            'RH': rh
        }
    ).rename('WetBulbTemperature').clip(region)

    image = wetbulb

    # -----------------------------------------------------
    # 3. Metadata for S3 and EAE
    # -----------------------------------------------------
    config = {
        "long_name": f"Wet Bulb Temperature (Mean) ({prev_month})",
        "metadata": (
            f"This layer provides the mean wet bulb temperature "
            f"for Assam during {prev_month}. Wet bulb temperature "
            f"is derived from monthly mean air temperature and "
            f"dew point temperature obtained from ERA5-Land "
            f"reanalysis data. It combines the effects of heat "
            f"and humidity and is an important indicator of "
            f"thermal stress."
        ),
        "s3_folder": "EnergyAccess/IND/assam/Climate",
        "file_prefix": f"Assam_average_WetBulb_{prev_month}",
        "eae_dataset_url": "https://admin.energyaccessexplorer.org/admin/?model=datasets&geography_id=bb80d8a8-f478-409a-94f3-e7ac8d6c85bc&edit_model=662c5266-1497-4b5e-a9fe-86244b9aa1d5"
    }

    return image, region, config
