import os
import smtplib
import ssl
from dotenv import load_dotenv
from email.message import EmailMessage

# Load the variables from the .env file
load_dotenv()

# --- CONFIGURATION ---
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587  # Using SSL for a secure connection
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
APP_PASSWORD = os.getenv("APP_PASSWORD")
RECEIVER_EMAIL = "abdul.khalid@wri.org"

def send_email(layer, message):
    msg = EmailMessage()
    msg.set_content(message)
    msg['Subject'] = f"Update on {layer}"
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECEIVER_EMAIL

    # Create a secure SSL context
    context = ssl.create_default_context()

    try:
        # Use SMTP (not SMTP_SSL) for Port 587
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls(context=context) # Upgrade to secure connection
        server.login(SENDER_EMAIL, APP_PASSWORD)
        server.send_message(msg)
        server.quit()
        print("✅ Email sent successfully!")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    send_email("email functionality", "The email functionality is working properly!")
