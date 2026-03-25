import re
from typing import Any, Dict, List, Optional

from scrapling import Fetcher


UPS_TRACK_URL = "https://www.ups.com/track?loc=en_US&tracknum={tracking_number}&requester=ST/trackdetails"


def clean_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    value = re.sub(r"\s+", " ", value).strip()
    return value or None


def parse_event_row(row) -> Optional[Dict[str, Any]]:
    cells = row.css("td")
    if len(cells) < 2:
        return None

    datetime_cell = cells[0]
    details_cell = cells[1]

    datetime_text = clean_text(datetime_cell.text())
    headline = clean_text(details_cell.css_first("strong").text() if details_cell.css_first("strong") else None)

    # Get all visible lines from the details cell
    detail_text = details_cell.text(separator="\n")
    lines = [clean_text(x) for x in detail_text.split("\n")]
    lines = [x for x in lines if x]

    # Typical shapes:
    # ["On the Way", "Arrived at Facility", "Watertown, MA, United States"]
    # ["Departed from Facility", "Shrewsbury, MA, United States"]
    # ["Label Created", "Shipper created a label, UPS has not received the package yet.", "United States"]
    description = None
    location = None

    if headline:
        lines_wo_headline = [x for x in lines if x != headline]
    else:
        lines_wo_headline = lines[:]

    if len(lines_wo_headline) >= 1:
        description = lines_wo_headline[0]
    if len(lines_wo_headline) >= 2:
        location = lines_wo_headline[-1]

    date_value = None
    time_value = None
    if datetime_text:
        parts = datetime_text.split(" ", 1)
        if len(parts) == 2 and "/" in parts[0]:
            date_value = parts[0]
            time_value = parts[1]
        else:
            date_value = datetime_text

    return {
        "date": date_value,
        "time": time_value,
        "headline": headline,
        "description": description,
        "location": location,
    }


def scrape_ups_tracking(tracking_number: str) -> Dict[str, Any]:
    url = UPS_TRACK_URL.format(tracking_number=tracking_number)

    fetcher = Fetcher(
        auto_match=False,
    )

    page = fetcher.get(url)

    # Try to find and click the "View All Shipping Details" button.
    # Selector may change, so we try a few variants.
    button = (
        page.css_first("#st_App_View_Details")
        or page.css_first("button[id*='View']")
        or page.css_first("button[aria-label*='Details']")
        or page.css_first("button:contains('View All Shipping Details')")
    )

    if button is not None:
        try:
            button.click()
            page.wait_for_timeout(2000)
        except Exception:
            pass

    # Rows from the expanded details table
    rows = page.css("tr[id^='stApp_activitydetails_row']")

    events: List[Dict[str, Any]] = []
    for row in rows:
        parsed = parse_event_row(row)
        if parsed:
            events.append(parsed)

    if not events:
        # Fallback for debugging
        html_preview = page.html[:3000] if hasattr(page, "html") else ""
        raise RuntimeError(
            "Could not extract UPS event rows. The page structure may have changed or additional anti-bot handling may be needed.\n"
            f"URL: {url}\n"
            f"HTML preview:\n{html_preview}"
        )

    latest_event = events[0]

    return {
        "tracking_number": tracking_number,
        "carrier": "UPS",
        "latest_event": latest_event,
        "events": events,
    }