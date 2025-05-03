from dotenv import load_dotenv
import os

load_dotenv()

print("EMAIL:", os.getenv("JQUANTS_EMAIL"))
print("PASSWORD:", os.getenv("JQUANTS_PASSWORD"))
