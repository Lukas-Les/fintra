import os
from dotenv import load_dotenv

env = os.getenv("ENV", "dev")
if env == "dev":
    load_dotenv()
