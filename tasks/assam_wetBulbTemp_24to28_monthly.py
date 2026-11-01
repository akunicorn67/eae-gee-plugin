import ee
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

EE_PROJECT = os.getenv("EE_PROJECT")

# -----------------------------------------------------
# User Configuration
# -----------------------------------------------------

# Wet Bulb Temperature Thresholds (°C)
WET_BULB_MIN = 24
WET_BULB_MAX = 28

# Aggregation Period
AGGREGATION_PERIOD = "monthly"

# Other supported options:
# AGGREGATION_PERIOD = "annual"
# AGGREGATION_PERIOD = "decadal"


def get_gee_data():

    ee.Initialize(project=EE_PROJECT)

    # -----------------------------------------------------
    # 1. Geometry
    # -----------------------------------------------------
    region = ee.Geometry.Rectangle([89.6, 24.1, 96.2, 28.1])  # Assam

    # -----------------------------------------------------
    # 2. Time Period Selection
    # -----------------------------------------------------
    today = datetime.now()

    if AGGREGATION_PERIOD == "monthly":

        first_day_current = today.replace(day=1)
        end_date = first_day_current

        last_month_end = first_day_current - timedelta(days=1)
        start_date = last_month_end.replace(day=1)

        period_label = start_date.strftime("%B %Y")

    # Uncomment if annual calculations are needed

    # elif AGGREGATION_PERIOD == "annual":
    #
    #     year = today.year - 1
    #
    #     start_date = datetime(year, 1, 1)
    #     end_date = datetime(year + 1, 1, 1)
    #
    #     period_label = str(year)

    # Uncomment if decadal calculations are needed

    # elif AGGREGATION_PERIOD == "decadal":
    #
    #     current_year = today.year
    #
    #     decade_start_year = ((current_year - 1) // 10) * 10 - 9
    #     decade_end_year = decade_start_year + 9
    #
    #     start_date = datetime(decade_start_year, 1, 1)
    #     end_date = datetime(decade_end_year + 1, 1, 1)
    #
    #     period_label = f"{decade_start_year}-{decade_end_year}"

    else:
        raise ValueError(
            f"Unsupported AGGREGATION_PERIOD: {AGGREGATION_PERIOD}"
        )

    # -----------------------------------------------------
    # 3. ERA5-Land Daily Data
    # -----------------------------------------------------
    collection = (
        ee.ImageCollection("ECMWF/ERA5_LAND/DAILY_AGGR")
        .filterDate(
            start_date.strftime("%Y-%m-%d"),
            end_date.strftime("%Y-%m-%d")
        )
    )

    # -----------------------------------------------------
    # 4. Calculate Daily Wet Bulb Temperature
    # -----------------------------------------------------
    def calculate_wetbulb(img):

        # Kelvin -> Celsius
        T = img.select('temperature_2m').subtract(273.15)

        Td = img.select('dewpoint_temperature_2m').subtract(273.15)

        # Relative Humidity (%)
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

        return (
            Tw.gte(WET_BULB_MIN)
              .And(Tw.lte(WET_BULB_MAX))
              .rename('wetbulb_days')
              .copyProperties(img, ['system:time_start'])
        )

    # -----------------------------------------------------
    # 5. Count Days Meeting Threshold
    # -----------------------------------------------------
    qualifying_days = collection.map(calculate_wetbulb)

    image = (
        qualifying_days
        .sum()
        .rename('WetBulbDays')
        .clip(region)
    )

    # -----------------------------------------------------
    # 6. Metadata
    # -----------------------------------------------------
    config = {
        "long_name": (
            f"Days with Wet Bulb Temperature Between "
            f"{WET_BULB_MIN}°C and {WET_BULB_MAX}°C "
            f"({period_label})"
        ),
        "metadata": (
            f"This layer represents the number of days during "
            f"{period_label} when estimated wet bulb temperature "
            f"was between {WET_BULB_MIN}°C and {WET_BULB_MAX}°C "
            f"across Assam. Wet bulb temperature was computed from "
            f"ERA5-Land daily air temperature and dew point "
            f"temperature using the Stull approximation."
        ),
        "s3_folder": "EnergyAccess/IND/assam/Climate",
        "file_prefix": (
            f"Assam_WetBulb_Days_"
            f"{WET_BULB_MIN}_to_{WET_BULB_MAX}_"
            f"{period_label.replace(' ', '_')}"
        ),
        "eae_dataset_url": "https://admin.energyaccessexplorer.org/admin/?model=datasets&geography_id=bb80d8a8-f478-409a-94f3-e7ac8d6c85bc&edit_model=fe6908e7-f71d-4305-ac71-0f1c76c8a7c5#"
    }

    return image, region, config
