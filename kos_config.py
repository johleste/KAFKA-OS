# kos_config.py
# Stores constants for the KafkaOS simulation

import datetime

# --- Core OS ---
OS_NAME = "KafkaOS (Kernel v0.9m-Modular)"
OS_VERSION = "Build 20250415-MESA-RC4 (Compliance Level: Delta-Fragmented)"
NODE_ID = "KOS-NODE-AZMESA-MOD-01"
CURRENT_LOCATION = "Mesa, Arizona Operations Sector"
CURRENT_TIME_MST = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-7))) # For initial reference

# --- Time Limit ---
TIME_LIMIT_SECONDS = 180
TIME_LIMIT_MANDATE = "KOS Temporal Mandate TM-CORE-SESS-MOD-79C"

# --- Authentication & Commands ---
MINIMUM_ID_LENGTH = 5
CONFIRMATION_PHRASE = "I_ACKNOWLEDGE_AND_COMPLY_WITH_ALL_PROTOCOLS" # Even longer
STANDARD_PURPOSE_CODE_FS = "FS-QUERY-7701"
STANDARD_PURPOSE_CODE_PROC = "PROC-EXEC-8804"
SECURE_COMM_PURPOSE_CODE = "SEC-DATA-9901"
STATUS_PURPOSE_CODE = "SYS-HEALTH-0101" # Purpose needed for status now? Yes.
SHUTDOWN_AUTH_CODE_BASE = "HALT_SYS_MOD_"

# --- Base Delays (milliseconds) ---
BASE_MSG_DELAY_MS = 200
BASE_INPUT_PROC_DELAY_MS = 400
BASE_CHECK_DELAY_SHORT_MS = 800
BASE_CHECK_DELAY_MEDIUM_MS = 1300
BASE_CHECK_DELAY_LONG_MS = 2000
BASE_FORWARDING_DELAY_MS = 750

# --- Bureaucracy ---
# Keys for Review Entities (actual dict in kos_bureaucracy.py)
REVIEW_ENTITY_KEYS = [
    'BOOT', 'AUTH', 'CMD_INTENT', 'CMD_EXEC', 'FS_ACCESS', 'PROC_LAUNCH',
    'STATUS_QUERY', 'SHUTDOWN', 'COMPLIANCE', 'ARBITRARY_LOCKOUT',
    'RE_AUTH', 'PURPOSE_VALIDATION' # Added more specific keys
]
# Arbitrary Rule Parameters
LOCKOUT_PRIME_MINUTE_FILESYSTEM_DAY = 1 # 0=Mon, 1=Tue, etc.
LOCKOUT_RANDOM_FAILURE_CHANCE = 0.05 # 5%
HIGH_FRICTION_REVIEW_THRESHOLD = 5 # Add extra steps if pending reviews exceed this
