import ee
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

EE_PROJECT = os.getenv("EE_PROJECT")

def get_gee_data():

    ee.Initialize(project=EE_PROJECT)

    # -----------------------------------------------------
    # 1. Geometry and Dates
    # -----------------------------------------------------
    region = ee.Geometry.Rectangle([89.6, 24.1, 96.2, 28.1])  # Assam

    today = datetime.now()
    first_day_this_month = today.replace(day=1)
    last_month_end = first_day_this_month - timedelta(days=1)
    last_month_start = last_month_end.replace(day=1)

    prev_month = last_month_end.strftime("%B %Y")

    # -----------------------------------------------------
    # 2. Daily ERA5-Land Data
    # -----------------------------------------------------
    collection = (
        ee.ImageCollection("ECMWF/ERA5_LAND/DAILY_AGGR")
        .filterDate(
            last_month_start.strftime('%Y-%m-%d'),
            first_day_this_month.strftime('%Y-%m-%d')
        )
    )

    # -----------------------------------------------------
    # Calculate Daily Wet Bulb Temperature
    # -----------------------------------------------------
    def calculate_wetbulb(img):

        # Kelvin -> Celsius
        T = img.select('temperature_2m').subtract(273.15)

        Td = img.select('dewpoint_temperature_2m').subtract(273.15)

        # Relative Humidity
        RH = ee.Image().expression(
            '''
            100 * (
                exp((17.625 * Td)/(243.04 + Td))
                /
                exp((17.625 * T)/(243.04 + T))
            )
            ''',
            {
                'Td': Td,
                'T': T
            }
        ).max(0).min(100)

        # Stull Wet Bulb Approximation
        Tw = ee.Image().expression(
            '''
            T * atan(0.151977 * sqrt(RH + 8.313659))
            + atan(T + RH)
            - atan(RH - 1.676331)
            + 0.00391838 * pow(RH, 1.5) * atan(0.023101 * RH)
            - 4.686035
            ''',
            {
                'T': T,
                'RH': RH
            }
        ).rename('wetbulb')

        # Days where Tw is between 25 and 30 C
        return (
            Tw.gte(25)
              .And(Tw.lte(30))
              .rename('wb_25_30')
        )

    # -----------------------------------------------------
    # Count Days Meeting Criteria
    # -----------------------------------------------------
    qualifying_days = collection.map(calculate_wetbulb)

    count_days = (
        qualifying_days
        .sum()
        .rename('WetBulbDays25to30')
        .clip(region)
    )

    image = count_days

    # -----------------------------------------------------
    # 3. Metadata
    # -----------------------------------------------------
    config = {
        "long_name": f"Days with Wet Bulb Temperature Between 25°C and 30°C ({prev_month})",
        "metadata": (
            f"This layer provides the number of days during {prev_month} "
            f"for which the estimated wet bulb temperature was between "
            f"25°C and 30°C across Assam. Wet bulb temperature was "
            f"calculated from ERA5-Land daily temperature and dew point "
            f"temperature datasets using the Stull approximation."
        ),
        "s3_folder": "EnergyAccess/IND/assam/Climate",
        "file_prefix": f"Assam_WetBulb_Days_25_to_30_{prev_month}",
        "eae_dataset_url": "https://admin.energyaccessexplorer.org/admin/?model=datasets&geography_id=bb80d8a8-f478-409a-94f3-e7ac8d6c85bc&edit_model=87f77a20-2ee8-4ae1-b04e-70d0aebd6773"
    }

    return image, region, config
