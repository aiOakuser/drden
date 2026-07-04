import os

from storages.backends.s3boto3 import S3Boto3Storage


def _normalize_location(value: str | None, fallback: str) -> str:
    location = (value or fallback).strip().strip("/")
    return location or fallback.strip("/")


AWS_S3_STATIC_LOCATION = _normalize_location(
    os.getenv("AWS_S3_STATIC_LOCATION", "static"),
    "static",
)
AWS_S3_MEDIA_LOCATION = _normalize_location(
    os.getenv("AWS_S3_MEDIA_LOCATION", "media"),
    "media",
)


def _media_location(env_name: str, suffix: str) -> str:
    default_location = f"{AWS_S3_MEDIA_LOCATION}/{suffix}"
    return _normalize_location(os.getenv(env_name, default_location), default_location)


AWS_S3_DOMAIN_LOCATIONS = {
    "designers_accounts": _media_location(
        "AWS_S3_DESIGNERS_ACCOUNTS_LOCATION",
        "designers/accounts",
    ),
    "viewers_accounts": _media_location(
        "AWS_S3_VIEWERS_ACCOUNTS_LOCATION",
        "viewers/accounts",
    ),
    "techpacks": _media_location("AWS_S3_TECHPACKS_LOCATION", "techpacks"),
    "orders": _media_location("AWS_S3_ORDERS_LOCATION", "orders"),
    "events": _media_location("AWS_S3_EVENTS_LOCATION", "events"),
    "collections": _media_location("AWS_S3_COLLECTIONS_LOCATION", "collections"),
}


class StaticStorage(S3Boto3Storage):
    location = AWS_S3_STATIC_LOCATION
    default_acl = "public-read"


class MediaStorage(S3Boto3Storage):
    location = AWS_S3_MEDIA_LOCATION
    file_overwrite = False


class DesignersAccountsStorage(MediaStorage):
    location = AWS_S3_DOMAIN_LOCATIONS["designers_accounts"]


class ViewersAccountsStorage(MediaStorage):
    location = AWS_S3_DOMAIN_LOCATIONS["viewers_accounts"]


class TechpacksStorage(MediaStorage):
    location = AWS_S3_DOMAIN_LOCATIONS["techpacks"]


class OrdersStorage(MediaStorage):
    location = AWS_S3_DOMAIN_LOCATIONS["orders"]


class EventsStorage(MediaStorage):
    location = AWS_S3_DOMAIN_LOCATIONS["events"]


class CollectionsStorage(MediaStorage):
    location = AWS_S3_DOMAIN_LOCATIONS["collections"]