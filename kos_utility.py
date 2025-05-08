# kos_utility.py
# Basic utility functions for KafkaOS

import uuid
import random
import datetime
import time # Still need time for sleep

# Import config for delays - maybe pass delays instead? Let's import for now.
# NOTE: In larger projects, passing config/dependencies is better than direct imports between non-core modules.
import kos_config

def pseudo_uuid():
    """Generates a basic pseudo-UUID."""
    return str(uuid.uuid4()).upper()

def random_delay(base_delay_ms):
    """Adds a small random amount to a base delay and returns seconds."""
    return (base_delay_ms + random.uniform(50, 300)) / 1000.0

def get_current_timestamp(include_tz=True):
    """Gets the current timestamp, attempting to represent MST."""
    # Note: This relies on system time + offset, might not be true MST if DST changes etc.
    try:
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        now_mst = now_utc.astimezone(datetime.timezone(datetime.timedelta(hours=-7)))
        format_str = '%Y-%m-%d %H:%M:%S.%f'
        timestamp = now_mst.strftime(format_str)[:-3]
        if include_tz:
            timestamp += " MST"
        return timestamp
    except Exception: # Fallback if timezone math fails
        return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3] + " UTC*"

def sleep_random(base_delay_ms):
    """Sleeps for a base duration plus a random amount."""
    time.sleep(random_delay(base_delay_ms))
