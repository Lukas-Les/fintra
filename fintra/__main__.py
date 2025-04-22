import os
import uvicorn

from fintra import config
from fintra.app import app

if __name__ == "__main__":
    uvicorn.run(app=app)
