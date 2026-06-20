"""
Upload snapshots and models to DigitalOcean Spaces.
Requires boto3 and DO Spaces credentials in .env.

Usage:
    uv run python upload-to-spaces.py
"""

import os
import glob
import boto3
from dotenv import load_dotenv

load_dotenv()

SPACES_ENDPOINT = os.environ["SPACES_ENDPOINT"]
SPACES_BUCKET = os.environ["SPACES_BUCKET"]
SPACES_KEY = os.environ["SPACES_KEY"]
SPACES_SECRET = os.environ["SPACES_SECRET"]

session = boto3.session.Session()
client = session.client(
    "s3",
    region_name=SPACES_ENDPOINT.split("//")[1].split(".")[0],
    endpoint_url=SPACES_ENDPOINT,
    aws_access_key_id=SPACES_KEY,
    aws_secret_access_key=SPACES_SECRET,
)


def upload_file(local_path: str, remote_key: str):
    size_mb = os.path.getsize(local_path) / 1e6
    print(f"Uploading {local_path} ({size_mb:.1f}MB) -> {remote_key}")
    client.upload_file(
        local_path, SPACES_BUCKET, remote_key,
        ExtraArgs={"ACL": "public-read"},
    )
    print(f"  Done: {SPACES_ENDPOINT}/{SPACES_BUCKET}/{remote_key}")


def main():
    # Upload snapshots
    snapshots = sorted(glob.glob("snapshots/*.snapshot"))
    if snapshots:
        print(f"Uploading {len(snapshots)} snapshots...")
        for f in snapshots:
            upload_file(f, f)
    else:
        print("No snapshots found in snapshots/")

    # Upload models zip
    if os.path.exists("models.zip"):
        upload_file("models.zip", "models.zip")
    else:
        print("No models.zip found. Create it with: cd models && zip -r ../models.zip . && cd ..")

    print("\nDone. Files are publicly accessible at:")
    print(f"  {SPACES_ENDPOINT}/{SPACES_BUCKET}/snapshots/")
    print(f"  {SPACES_ENDPOINT}/{SPACES_BUCKET}/models.zip")


if __name__ == "__main__":
    main()
