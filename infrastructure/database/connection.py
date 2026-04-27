import os
import pandas as pd
from pyathena import connect
from dotenv import load_dotenv


load_dotenv()

conn = connect(
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_DEFAULT_REGION"),
    s3_staging_dir=os.getenv("S3_STAGING_DIR")
)

