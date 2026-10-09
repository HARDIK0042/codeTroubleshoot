import re


def format_recognized_text(text):
    if text is None:
        return ""
    lines = [line.strip() for line in str(text).splitlines()]
    formatted = "\n".join(line for line in lines if line)
    return re.sub(r"\b(send)\s+yournote\b", r"\1 your note", formatted, flags=re.IGNORECASE)
