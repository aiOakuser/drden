from storages.backends.s3boto3 import S3Boto3Storage

class StaticStorage(S3Boto3Storage):
    location = "static"
    default_acl = "public-read"

class MediaStorage(S3Boto3Storage):
    location = "media"
    file_overwrite = False  # keep filenames; good for user uploads


# 
# 2. CORS JSON (already in your comments)

# For AWS S3 bucket CORS:

# [
#   {
#     "AllowedHeaders": ["*"],
#     "AllowedMethods": ["GET","HEAD"],
#     "AllowedOrigins": [
#       "https://designrden.com",
#       "https://www.designrden.com",
#     ],
#     "ExposeHeaders": ["ETag"],
#     "MaxAgeSeconds": 3000
#   }
# ]


# Whome:

# AWS Console → S3 → your bucket → Permissions → CORS configuration → Paste + Save

# ⚡ For production security, swap * in "AllowedOrigins" for:

# ["https://designrden.com","https://www.designrden.com"]