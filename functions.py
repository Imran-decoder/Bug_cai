import re

def extract_route(text: str) -> str | None:
    """
    Extracts the route name from text.
    - Looks first for a line like: next:Researcher  (multiline, case-insensitive).
    - If not found, searches the text for known route keywords and returns the last occurrence.
    - Returns one of the allowed routes (title-cased) or "END" when no valid route is found.
    """
    if not isinstance(text, str):
        return "END"

    # 1) Try explicit next: route line (preferred)
    m = re.search(r'^\s*next\s*:\s*([A-Za-z]+)\s*$', text, re.MULTILINE | re.IGNORECASE)
    if m:
        route_raw = m.group(1).strip()
        route = route_raw.title()
        allowed = {"Research", "Researcher", "Static", "Dynamic", "End", "END"}
        if route in allowed or route.upper() == "END":
            return "END" if route.upper() == "END" else route
        # if explicit value is not allowed, fall through to fallback search

    # 2) Fallback: search for known keywords and return the last match (safe)
    # include possible variants (Researcher, Research)
    pattern = re.compile(r'\b(Researcher|Research|Static|Dynamic|END)\b', re.IGNORECASE)
    matches = pattern.findall(text or "")
    if matches:
        last = matches[-1].title()
        return "END" if last.upper() == "END" else last

    # 3) Nothing found
    return "END"
