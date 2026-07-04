import os
from django.templatetags.static import static
from django.conf import settings


import os
from django.templatetags.static import static
from django.conf import settings

def list_static_media(path: str):
    abs_path = os.path.join(settings.BASE_DIR, "designer_portfolio", "static", path)

    if not os.path.exists(abs_path):
        return []

    # 🔹 Always sort files alphabetically (ascending by filename)
    files = sorted(os.listdir(abs_path))

    results = []
    for f in files:
        if f.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".mp4")):
            file_type = "video" if f.lower().endswith(".mp4") else "image"
            results.append({
                "name": f,
                "url": static(f"{path}/{f}"),
                "type": file_type,
            })
    return results



def get_first_media(path: str):
    """Return the first media file (image/video) inside a folder, or None if empty."""
    files = list_static_media(path)
    return files[0] if files else None
