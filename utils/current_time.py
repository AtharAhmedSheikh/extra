from datetime import datetime
import pytz

def _get_current_karachi_time_str():
    """Internal: current datetime in Karachi timezone as ISO string."""
    karachi_tz = pytz.timezone("Asia/Karachi")
    return datetime.now(karachi_tz).isoformat()
