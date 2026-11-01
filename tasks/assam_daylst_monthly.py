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
    # 3. VIIRS Day Land Surface Temperature
    # -----------------------------------------------------
    collection = (
        ee.ImageCollection("NASA/VIIRS/002/VNP21A1D")
        .filterDate(
            start_date.strftime("%Y-%m-%d"),
            end_date.strftime("%Y-%m-%d")
        )
    )

    # -----------------------------------------------------
    # 4. Quality Filter + Celsius Conversion
    # -----------------------------------------------------
    def process_lst(img):

        # Good-quality pixels only
        qc = img.select('QC')

        good_quality = (
            qc.bitwiseAnd(3).eq(0)  # Bits 0-1 = Good quality
        )

        lst_celsius = (
            img.select('LST_1KM')
            .subtract(273.15)
            .updateMask(good_quality)
            .rename('LST_C')
        )

        return lst_celsius.copyProperties(
            img,
            ['system:time_start']
        )

    lst_collection = collection.map(process_lst)

    # -----------------------------------------------------
    # 5. Previous Month Mean LST
    # -----------------------------------------------------
    image = (
        lst_collection
        .mean()
        .rename('Mean_Day_LST')
        .clip(region)
    )

    # -----------------------------------------------------
    # 6. Metadata
    # -----------------------------------------------------
    config = {
        "long_name": (
            f"Mean Day Land Surface Temperature ({period_label})"
        ),
        "metadata": (
            f"This layer represents the average daytime land "
            f"surface temperature across Assam during "
            f"{period_label}. Values are derived from the "
            f"NASA VIIRS VNP21A1D Daily Land Surface "
            f"Temperature product and expressed in degrees "
            f"Celsius."
        ),
        "s3_folder": "EnergyAccess/IND/assam/Climate",
        "file_prefix": (
            f"Assam_Mean_Day_LST_"
            f"{period_label.replace(' ', '_')}"
        ),
        "eae_dataset_url": "https://admin.energyaccessexplorer.org/admin/?model=datasets&geography_id=bb80d8a8-f478-409a-94f3-e7ac8d6c85bc&edit_model=903ab9e6-1835-4a83-8233-705cc2bc931d#"
    }

    return image, region, config
