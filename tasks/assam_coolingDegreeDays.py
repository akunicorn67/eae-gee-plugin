import ee
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

EE_PROJECT = os.getenv("EE_PROJECT")

CDD_BASE = 24

def get_gee_data():

    ee.Initialize(project=EE_PROJECT)

    region = ee.Geometry.Rectangle([89.6, 24.1, 96.2, 28.1])

    today = datetime.now()

    first_day_this_month = today.replace(day=1)
    last_month_end = first_day_this_month - timedelta(days=1)
    last_month_start = last_month_end.replace(day=1)

    prev_month = last_month_end.strftime("%B %Y")

    coll = (
        ee.ImageCollection(
            "ECMWF/ERA5_LAND/DAILY_AGGR"
        )
        .filterDate(
            last_month_start.strftime("%Y-%m-%d"),
            first_day_this_month.strftime("%Y-%m-%d")
        )
        .select("temperature_2m")
    )

    def calc_cdd(img):

        temp_c = img.subtract(273.15)

        return (
            temp_c
            .subtract(CDD_BASE)
            .max(0)
        )

    image = (
        coll
        .map(calc_cdd)
        .sum()
        .rename("cooling_degree_days")
        .clip(region)
    )

    config = {
        "long_name": f"Cooling Degree Days ({prev_month})",
        "metadata": f"Monthly Cooling Degree Days using 24°C base temperature for Assam during {prev_month}.",
        "s3_folder": "EnergyAccess/IND/assam/Climate",
        "file_prefix": f"Assam_Cooling_Degree_Days_{prev_month}",
	"eae_dataset_url":"https://admin.energyaccessexplorer.org/admin/?model=datasets&geography_id=bb80d8a8-f478-409a-94f3-e7ac8d6c85bc&edit_model=75671b5f-e2ae-4373-bbee-bd497a1290cc"
    }

    return image, region, config
