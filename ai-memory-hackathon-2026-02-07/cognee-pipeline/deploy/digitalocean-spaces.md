# Host Vector Snapshots on DigitalOcean Spaces

Store pre-built vector snapshots for users to download.

## Create Space

```bash
# Create Space
doctl compute cdn create \
  --origin cognee-data.nyc3.digitaloceanspaces.com \
  --ttl 3600

# Or via console: https://cloud.digitalocean.com/spaces
```

## Upload Snapshots

```bash
# Export from Qdrant Cloud
python export_qdrant_snapshots.py

# Upload to Spaces
python upload_to_spaces.py cognee-vectors-snapshot.tar.gz
```

## Configure Public Access

In DO Console:
1. Go to Spaces > cognee-data
2. Settings > File Listing: Enable
3. Or set individual file permissions to public

## Download URL

Users download from:
```
https://cognee-data.nyc3.digitaloceanspaces.com/cognee-vectors-snapshot.tar.gz
```

## CDN (Optional)

Enable CDN for faster downloads:
```bash
doctl compute cdn create \
  --origin cognee-data.nyc3.digitaloceanspaces.com \
  --ttl 86400
```

CDN URL becomes:
```
https://cognee-data.nyc3.cdn.digitaloceanspaces.com/cognee-vectors-snapshot.tar.gz
```
