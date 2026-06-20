#!/usr/bin/env python3
"""Upload snapshot archive to DigitalOcean Spaces."""

import os
import sys
import boto3
from botocore.client import Config
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# DO Spaces config (S3-compatible)
SPACES_REGION = os.getenv("SPACES_REGION", "nyc3")
SPACES_BUCKET = os.getenv("SPACES_BUCKET", "cognee-data")
SPACES_KEY = os.getenv("SPACES_KEY", "")
SPACES_SECRET = os.getenv("SPACES_SECRET", "")

ENDPOINT_URL = f"https://{SPACES_REGION}.digitaloceanspaces.com"


def upload_file(file_path: Path, object_name: str = None):
    """Upload a file to DO Spaces."""
    if not SPACES_KEY or not SPACES_SECRET:
        print("ERROR: Missing SPACES_KEY and SPACES_SECRET in .env")
        print()
        print("Get them from: https://cloud.digitalocean.com/account/api/spaces")
        print("Then add to .env:")
        print("  SPACES_KEY=<your-key>")
        print("  SPACES_SECRET=<your-secret>")
        sys.exit(1)

    if object_name is None:
        object_name = file_path.name

    print(f"Uploading {file_path} to {SPACES_BUCKET}/{object_name}...")

    # Create S3 client for DO Spaces
    client = boto3.client(
        's3',
        region_name=SPACES_REGION,
        endpoint_url=ENDPOINT_URL,
        aws_access_key_id=SPACES_KEY,
        aws_secret_access_key=SPACES_SECRET,
        config=Config(signature_version='s3v4')
    )

    # Check if bucket exists, create if not
    try:
        client.head_bucket(Bucket=SPACES_BUCKET)
        print(f"  Bucket exists: {SPACES_BUCKET}")
    except:
        print(f"  Creating bucket: {SPACES_BUCKET}")
        client.create_bucket(Bucket=SPACES_BUCKET)

    # Upload with progress
    file_size = file_path.stat().st_size
    uploaded = 0

    def progress_callback(bytes_transferred):
        nonlocal uploaded
        uploaded += bytes_transferred
        pct = (uploaded / file_size) * 100
        print(f"\r  {pct:.1f}% ({uploaded // 1024 // 1024} MB)", end="", flush=True)

    client.upload_file(
        str(file_path),
        SPACES_BUCKET,
        object_name,
        Callback=progress_callback,
        ExtraArgs={'ACL': 'public-read'}
    )

    print()

    # Get public URL
    public_url = f"https://{SPACES_BUCKET}.{SPACES_REGION}.digitaloceanspaces.com/{object_name}"
    print(f"  Uploaded: {public_url}")

    return public_url


def main():
    if len(sys.argv) < 2:
        file_path = Path("cognee-vectors-snapshot.tar.gz")
    else:
        file_path = Path(sys.argv[1])

    if not file_path.exists():
        print(f"ERROR: File not found: {file_path}")
        sys.exit(1)

    print("=" * 50)
    print("Upload to DigitalOcean Spaces")
    print("=" * 50)
    print()

    url = upload_file(file_path)

    print()
    print("=" * 50)
    print("Done! Update SNAPSHOT_URL in examples/local/.env.example:")
    print(f"  SNAPSHOT_URL={url}")
    print("=" * 50)


if __name__ == "__main__":
    main()
