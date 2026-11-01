import asyncio, sys, importlib
import time
import nest_asyncio
from common.s3_utils import upload_gee_to_s3
from common.eae_utils import run_eae_update
from common.email_notification import send_email

nest_asyncio.apply()


async def main(task_name):
    # 1. Dynamically import the task (e.g., tasks.assam_lst)
    task_module = importlib.import_module(f"tasks.{task_name}")
    image, region, config = task_module.get_gee_data()
    # print(config)
    print("✔️ Task created successfully!")

    # 2. Process to S3
    print(f"🚀 Starting {task_name}...")
    s3_url = upload_gee_to_s3(image=image,
                              region=region,
                              folder=config['s3_folder'],
                              prefix=config['file_prefix'])

    # 3. Update EAE
    if s3_url:
        print("✅ s3 URL generated successfully!")

        # 2. REPEAT Step 2 until success
        success = False
        attempts = 0
        max_attempts = 5 # Optional: safety limit to avoid infinite loops

        while not success and attempts < max_attempts:
            attempts += 1
            print(f"⏳ Attempt {attempts}: Updating EAE Backend...")
            try:
                # Run your Playwright function
                await run_eae_update(config['eae_dataset_url'], config['long_name'], config['metadata'], s3_url)
                success = True
                print(f"✅ {task_name} fully completed!")
            except Exception as e:
                print(f"❌ Attempt {attempts} failed: {e}")
                print("🔄 Retrying in 10 seconds...")
                time.sleep(10) # Wait before retrying
        
        # 3. Send Email (Success or Failure)
        if success:
            send_email(f"✅ SUCCESS: Processed {task_name}",
                       f"✅ SUCCESS: Processed {task_name}")
        else:
            send_email(f"❌ FAILED: EAE update of {task_name} failed after {max_attempts} attempts.",
                       f"❌ FAILED: EAE update of {task_name} failed after {max_attempts} attempts.")


if __name__ == "__main__":
    # Run via: python run_task.py assam_lst
    if len(sys.argv) > 1:
        asyncio.run(main(sys.argv[1]))
