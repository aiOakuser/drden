from django import template
import os, re
from urllib.parse import unquote

register = template.Library()

@register.filter
def prettify(value: str) -> str:
    """
    Clean up filenames/slugs for display:
    - URL decode (%20 -> space)
    - Strip extension & directory
    - Remove year prefixes like '2024-'
    - Replace dashes/underscores with spaces
    - Apply natural capitalization rules
    """
    if not value:
        return ""

    # Decode URL-encoded characters
    value = unquote(value)

    # Keep only the base name without extension
    name = os.path.basename(value)
    name = os.path.splitext(name)[0]

    # Remove leading year prefix (e.g., "2024-thom-browne" -> "thom-browne")
    name = re.sub(r"^\d{4}-", "", name)

    # Normalize separators
    name = name.replace("-", " ").replace("_", " ")

    # Words to lowercase unless first word
    lowercase_words = {
        "a", "an", "and", "as", "at", "but", "by", "for",
        "from", "in", "nor", "of", "on", "or", "so",
        "the", "to", "with"
    }

    words = name.split()
    prettified = []
    for i, w in enumerate(words):
        if w.isupper():  # acronyms (e.g., FSF) stay uppercase
            prettified.append(w)
        elif i == 0 or w.lower() not in lowercase_words:
            prettified.append(w.capitalize())
        else:
            prettified.append(w.lower())

    return " ".join(prettified)
