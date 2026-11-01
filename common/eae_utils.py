import os
import asyncio
import re
from playwright.async_api import async_playwright
from dotenv import load_dotenv
# from playwright.sync_api import Page, expect

# load the variable from th .env file
load_dotenv()

# --- TEST CONFIGURATION ---
ADMIN_URL = "https://admin.energyaccessexplorer.org/"
# Use your actual credentials for the test
EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")

# List of flags to reduce RAM usage
chrome_args = [
    '--disable-dev-shm-usage', # Uses /tmp instead of shared memory (fixes most VM crashes)
    '--no-sandbox',            # Reduces process overhead (crucial for small VMs)
    '--disable-gpu',           # Disables hardware acceleration (saves RAM)
    '--disable-extensions',    # Stops background extensions from loading
    '--js-flags="--max-old-space-size=512"' # Limits JavaScript engine memory
]

async def run_eae_update(dataset_url, long_name, metadata, s3_url):
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True, 
            slow_mo=1000,
#            channel="chrome",
            args=chrome_args
        )

        context = await browser.new_context()
        page = await context.new_page()

        print(f"🚀 Navigating to {ADMIN_URL}...")
        await page.goto(ADMIN_URL)

        # 1: LOGIN ---
        # Note: If these selectors fail, use page.pause() below to find the correct ones
        try:
            await page.fill('input[name="email"]', EMAIL)
            await page.fill('input[name="pass"]', PASSWORD)
            await page.click('button[type="submit"]')
            #await page.wait_for_load_state("networkidle")
            await page.get_by_role("heading", name="Geographies").wait_for(state="visible")
            print("✅ Logged in successfully.")
        except Exception as e:
            print(f"❌ Login failed: {e}")

        # 2: Jump DIRECTLY to the dataset edit page
        print(f"🚀 Jumping directly to dataset URL")
        await page.goto(dataset_url)

        # 3: Update the required fields
        print("✍️ Updating the dataset fields...")

        #await page.locator("input[name=\"name_long\"]").fill(f"Land Surface Temperature ({temporal_value})")
        await page.locator("input[name=\"name_long\"]").fill(long_name)
        print("Long Name updated!")

        await page.get_by_text("metadataimport metadata").click()
        
        # # Pause here for inspection
        # await page.pause()
        
        #await page.locator("textarea[name=\"description\"]").fill(f"This layer provides the mean land surface temperature values for the previous month for Assam.\n\nAt present it is providing the mean LST values of Assam for the month of {temporal_value}.")
        await page.locator("textarea[name=\"description\"]").fill(metadata)
        print("Metadata updated!")

        # navigate to the region where the new url is to be updated
        await page.get_by_text("source_files+").click()
        await page.get_by_text("0−").first.click()

        # await page.pause() # Uncomment this once to confirm the 'name' or 'id'
        await page.fill('input[name=\"endpoint\"]', s3_url)
        print("s3 URL updated!")

        print("💾 Saving changes...")
        # save the dataset with new url
        await page.get_by_title("Save").click()

        # # run paver
        await page.get_by_title("Paver").click()
        await page.get_by_role("button", name="Pave it!").wait_for(state="visible")
        print("💎 Running Paver...")

        await page.get_by_role("button", name="Pave it!").click()
        await page.get_by_role("main").filter(has_text=re.compile(r"DONE")).locator("#infopre").wait_for(state="visible")
        await page.wait_for_timeout(5000)
        # await get_by_text("×").nth(5).click()

        # 4: DEBUG PAUSE ---
        # This will pause the script and open the Playwright Inspector.
        # Use the "Pick Locator" button in the inspector window to click on 
        # the 'Datasets' link or 'URL' field to see the exact code needed.
        # print("⏸️ Pausing for manual inspection. Find your selectors now!")
        # await page.pause()

        print("🏁File Updated. Closing browser...")
        await browser.close()

# if __name__ == "__main__":
#     dataset_url = "https://admin.energyaccessexplorer.org/?model=datasets&geography_id=bb80d8a8-f478-409a-94f3-e7ac8d6c85bc&edit_model=3b67dcff-a124-46e5-9510-c515a20a7671&filter=temp"
#     s3_url = "https://wri-public-data.s3.amazonaws.com/EnergyAccess/IND/assam/aa%20automation-test/Assam_LST_2026_02_20260314_231000.tif"
#     temporal_value = "February 2026"
#     asyncio.run(run_eae_update(dataset_url, s3_url, temporal_value))
