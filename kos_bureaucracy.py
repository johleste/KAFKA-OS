# kos_bureaucracy.py
# Core Kafkaesque functions: logging, checks, forwarding, arbitrary rules

import datetime
import random
import sys # For potential exit in verify_action_intent

# Import shared utilities and config
import kos_config
import kos_utility

# --- Bureaucratic Entities ---
# Moved the actual dictionary here
REVIEW_ENTITIES = {
    'BOOT': "System Initialization Audit Log (SIAL)",
    'AUTH': "Pluggable Authentication Module Verifier (PAMV)",
    'CMD_INTENT': "Command Intent Review Unit (CIRU)",
    'CMD_EXEC': "Execution Result Log Monitor (ERLM)",
    'FS_ACCESS': "Filesystem Access Control Monitor (FACM)",
    'PROC_LAUNCH': "Process Execution Authorization Daemon (PEAD)",
    'STATUS_QUERY': "System Health Monitoring Log (SHML)",
    'SHUTDOWN': "System Termination Oversight Protocol (STOP)",
    'COMPLIANCE': "Regulatory Compliance Check Subsystem (RCCS)",
    'ARBITRARY_LOCKOUT': "Operational Mandate Enforcement Unit (OMEU)", # New
    'RE_AUTH': "Secondary Authentication Verification Log (SAVL)",    # New
    'PURPOSE_VALIDATION': "Justification Code Audit Service (JCAS)"  # New
}

# --- Core Bureaucratic Functions ---

def log_system_message(message, level="INFO"):
    """Logs a message with KafkaOS formatting."""
    timestamp = kos_utility.get_current_timestamp(include_tz=False)
    print(f"{timestamp} {kos_config.NODE_ID} kernel: [{level}] {message}")
    kos_utility.sleep_random(kos_config.BASE_MSG_DELAY_MS)

def perform_simulated_check(check_name, base_duration_ms):
    """Simulates a time-consuming check."""
    log_system_message(f"Subsystem Check: Initiating {check_name}...")
    kos_utility.sleep_random(base_duration_ms)
    verification_code = f"{check_name[:3].upper()}-{kos_utility.pseudo_uuid()[:6]}"
    log_system_message(f"Subsystem Check: {check_name} completed. Status: OK. Ref: {verification_code}")
    return True, verification_code

def simulate_forwarding(os_state, entity_key, context_ref, detail="Operational Context"):
    """Simulates forwarding context for review and updates pending count."""
    reviewer = REVIEW_ENTITIES.get(entity_key, "Default Audit Sink")
    forward_id = f"KOS-FWD-{entity_key}-{kos_utility.pseudo_uuid()[:8]}"
    log_system_message(f"AUDIT: Forwarding {detail} (Ref: {context_ref}) to '{reviewer}'. ID: {forward_id}")
    os_state['pending_reviews'] = os_state.get('pending_reviews', 0) + 1
    kos_utility.sleep_random(kos_config.BASE_FORWARDING_DELAY_MS)
    log_system_message(f"AUDIT: Ack received from '{reviewer}'. Pending Reviews: {os_state['pending_reviews']}")

def apply_procedural_friction(os_state, reason="Standard Operational Delay"):
    """Adds extra arbitrary delay based on state."""
    if os_state.get('pending_reviews', 0) > kos_config.HIGH_FRICTION_REVIEW_THRESHOLD:
        delay_ms = kos_config.BASE_CHECK_DELAY_SHORT_MS
        log_system_message(f"Applying procedural friction due to high audit backlog ({os_state['pending_reviews']}). Reason: {reason}.", level="WARN")
        kos_utility.sleep_random(delay_ms)

# --- Arbitrary Lockout Logic ---

def check_operational_mandate(os_state, required_clearance="STANDARD"):
    """Checks if an operation is allowed based on arbitrary rules."""
    now = datetime.datetime.now() # Use current time for checks
    minute = now.minute
    day_of_week = now.weekday() # 0=Mon, 1=Tue
    pending = os_state.get('pending_reviews', 0)
    user = os_state.get('user_id', 'UNKNOWN')

    log_system_message(f"Mandate Check: Verifying operational allowances for clearance '{required_clearance}'...", level="DEBUG")
    apply_procedural_friction(os_state, reason="Mandate Compliance Check") # Add friction here too

    # Rule 1: Filesystem on prime minute Tuesdays
    if required_clearance == "FILESYSTEM" and day_of_week == kos_config.LOCKOUT_PRIME_MINUTE_FILESYSTEM_DAY:
        is_prime = True
        if minute < 2: is_prime = False
        else:
            for i in range(2, int(minute**0.5) + 1):
                if minute % i == 0:
                    is_prime = False
                    break
        if is_prime:
            msg = f"Operation Denied: Filesystem access temporarily restricted during prime minute ({minute}) on specified day ({day_of_week}). Directive FS-TUE-PRIME."
            log_system_message(msg, level="ERROR")
            simulate_forwarding(os_state, 'ARBITRARY_LOCKOUT', f"FS-PRIME-{minute}", detail="Operational Denial Event")
            return False

    # Rule 2: High review backlog lockout (e.g., > 10)
    if pending > 10 and random.random() < 0.2: # 20% chance if backlog > 10
        msg = f"Operation Denied: System temporarily locked for critical operations due to excessive audit backlog ({pending}). Mandate AUDIT-BACKLOG-LOCK."
        log_system_message(msg, level="ERROR")
        simulate_forwarding(os_state, 'ARBITRARY_LOCKOUT', f"BACKLOG-{pending}", detail="Operational Denial Event")
        return False

    # Rule 3: Random compliance spot-check failure
    if random.random() < kos_config.LOCKOUT_RANDOM_FAILURE_CHANCE:
         msg = f"Operation Denied: Random compliance spot-check failed (Ref: SPOT-{kos_utility.pseudo_uuid()[:4]}). Please retry command."
         log_system_message(msg, level="ERROR")
         simulate_forwarding(os_state, 'ARBITRARY_LOCKOUT', f"SPOTCHECK-FAIL", detail="Operational Denial Event")
         return False

    log_system_message(f"Operational mandate check passed for clearance '{required_clearance}'.", level="DEBUG")
    return True


# --- Core Verification Protocol ---

def verify_action_intent(os_state, command_name, get_input_func, # Pass input func
                         requires_purpose=False, purpose_code_expected=None, requires_reauth=False):
    """Kafkaesque multi-step verification before executing a command."""
    log_system_message(f"PROC_VERIFY: Initiating Intent Verification Protocol for '{command_name}'.")
    # Access core functions via passed os_state or import kos_core? Pass for now.
    check_time_limit = os_state['utils']['check_time_limit'] # Assume check_time_limit is passed in utils dict

    check_time_limit(os_state['session_start_time'], f"Intent Verification for {command_name}")
    apply_procedural_friction(os_state, reason="Intent Verification Start")

    # 1. Confirmation Phrase
    confirm = get_input_func(f"Verify intent for '{command_name}'. Type EXACTLY '{kos_config.CONFIRMATION_PHRASE}': ")
    if confirm != kos_config.CONFIRMATION_PHRASE:
        log_system_message("PROC_VERIFY: Failed - Incorrect or incomplete confirmation phrase.", level="ERROR")
        return False
    log_system_message("PROC_VERIFY: Confirmation phrase validated.")
    perform_simulated_check("Intent Confirmation Logging", kos_config.BASE_CHECK_DELAY_SHORT_MS)

    # 2. Purpose Code (If required)
    if requires_purpose:
        check_time_limit(os_state['session_start_time'], f"Purpose Code for {command_name}")
        # Purpose code should have been extracted from args by the caller
        # We just simulate the validation check here
        log_system_message(f"PROC_VERIFY: Validating provided Purpose Code '{purpose_code_expected or 'N/A'}' against JCAS.")
        success, check_code = perform_simulated_check("Purpose Code Validation Against Mandate Matrix", kos_config.BASE_CHECK_DELAY_MEDIUM_MS)
        if not success: # Can add simulated failure here if needed
             log_system_message("PROC_VERIFY: Failed - Purpose code validation failed.", level="ERROR")
             return False
        log_system_message(f"PROC_VERIFY: Purpose Code validation successful (Ref: {check_code}).")
        simulate_forwarding(os_state, 'PURPOSE_VALIDATION', f"{command_name}-{purpose_code_expected}", detail="Purpose Code Audit")


    # 3. Re-Authentication (If required)
    if requires_reauth and os_state.get('is_authenticated'):
         check_time_limit(os_state['session_start_time'], f"Re-authentication for {command_name}")
         log_system_message("PROC_VERIFY: Secondary authentication challenge required via PAMV.", level="WARN")
         re_auth_id = get_input_func(f"Re-enter primary User ID ('{os_state['user_id']}') to confirm identity: ")
         if re_auth_id != os_state['user_id']:
             log_system_message("PROC_VERIFY: Failed - Secondary authentication identity mismatch.", level="ERROR")
             # Don't forward failure? Or should we? Let's forward.
             simulate_forwarding(os_state, 'RE_AUTH', f"{command_name}-FAIL", detail="Re-Authentication Failure")
             return False
         log_system_message("PROC_VERIFY: Secondary authentication successful.")
         perform_simulated_check("Re-authentication PAM Credential Check", kos_config.BASE_CHECK_DELAY_MEDIUM_MS)
         simulate_forwarding(os_state, 'RE_AUTH', f"{command_name}-OK", detail="Re-Authentication Success")

    # 4. Final Friction Check
    apply_procedural_friction(os_state, reason="Intent Verification Complete")

    log_system_message(f"PROC_VERIFY: Intent Verification Protocol for '{command_name}' completed successfully.")
    simulate_forwarding(os_state, 'CMD_INTENT', f"{command_name}-{kos_utility.pseudo_uuid()[:4]}", detail="Command Intent Verification Complete")
    return True
