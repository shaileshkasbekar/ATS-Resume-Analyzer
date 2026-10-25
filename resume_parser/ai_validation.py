"""
Helpers to validate AI output before it is shown or stored.

The AI's answer is treated like user input: wrong types are
dropped, numbers are clamped, text is length-limited, and any
"evidence" the AI quotes must really exist in the resume.
"""

import re


def clean_text(value, max_len=500):
    """
    A single string, trimmed and length-limited. Non-strings -> "".
    """

    if not isinstance(value, (str, int, float)) or isinstance(value, bool):
        return ""

    text = re.sub(r"\s+", " ", str(value)).strip()

    return text[:max_len]


def clean_text_list(value, max_items=10, max_len=300):
    """
    A list of unique non-empty strings.
    """

    if not isinstance(value, list):
        return []

    result = []
    seen = set()

    for item in value:

        text = clean_text(item, max_len)

        if text and text.lower() not in seen:
            seen.add(text.lower())
            result.append(text)

        if len(result) >= max_items:
            break

    return result


def clean_score(value):
    """
    A 0-100 number, or None if the value is missing or not a number.
    """

    if isinstance(value, bool) or value is None:
        return None

    try:
        score = float(str(value).replace("%", "").strip())
    except ValueError:
        return None

    return round(min(max(score, 0), 100), 2)


def clean_dict_list(value, max_items=10):
    """
    Only the dict items of a list.
    """

    if not isinstance(value, list):
        return []

    return [item for item in value if isinstance(item, dict)][:max_items]


def _normalize(text):

    text = (text or "").lower()

    # Treat bullets, dashes and quotes as spaces

    text = re.sub(r"[^a-z0-9+#.%/]+", " ", text)

    return re.sub(r"\s+", " ", text).strip()


def quote_in_text(quote, text, min_len=8):
    """
    True if the quote really appears in the text (ignoring case,
    spacing, bullets and punctuation). Quotes the AI shortened with
    "..." are accepted when every part appears.
    """

    if not isinstance(quote, str):
        return False

    normalized_text = _normalize(text)

    parts = [
        _normalize(part)
        for part in re.split(r"\.\.\.|…", quote)
    ]

    parts = [part for part in parts if part]

    if not parts or sum(len(part) for part in parts) < min_len:
        return False

    return all(part in normalized_text for part in parts)
