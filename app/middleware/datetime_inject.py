from datetime import datetime
import pytz
from app.models import CrossroadsRequest

async def inject_datetime(request: CrossroadsRequest, config: dict) -> CrossroadsRequest:
    tz_name = config.get("datetime", {}).get("timezone", "America/New_York")
    tz = pytz.timezone(tz_name)
    now = datetime.now(tz)
    formatted = now.strftime("%A, %B %-d, %Y, %-I:%M %p %Z")
    request.enriched_system += f"\nCurrent date and time: {formatted}\n"
    return request
