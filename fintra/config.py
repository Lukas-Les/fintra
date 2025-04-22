import os
from dotenv import load_dotenv

env = os.getenv("ENV", "dev")
if env == "dev":
    load_dotenv()
elif env == "test":
    load_dotenv(dotenv_path="./.env.test")
