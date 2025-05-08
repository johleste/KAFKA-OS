# kos_auth.py
# Handles authentication commands for KafkaOS

import kos_config
import kos_utility
import kos_bureaucracy

def handle_login(os_state, args_dict, positional_args, get_input_func):
    """Handles the klogin command."""
    log = kos_bureaucracy.log_system_message # Alias for brevity
    check_time = os_state['utils']['check_time_limit']

    log("Authentication sequence initiated via klogin.")
    if os_state.get('is_authenticated'):
        log("User already authenticated. Use 'klogout' first.", level="WARN")
        return

    check_time(os_state['session_start_time'], "Authentication")
    temp_user_id = get_input_func("Username: ")
    if not temp_user_id:
        log("Authentication failed: Null username provided.", level="ERROR")
        return

    get_input_func(f"Password for {temp_user_id}: ") # Simulate password
    log("Performing credential validation via PAMV...")
    success, check_code = kos_bureaucracy.perform_simulated_check("PAM Credential Check", kos_config.BASE_CHECK_DELAY_LONG_MS)

    if success:
         check_time(os_state['session_start_time'], "Authentication - MFA Check")
         mfa_code = get_input_func(f"Enter 6-digit MFA Token (Ref: Directive MFA-KOS-2A): ")
         if not mfa_code.isdigit() or len(mfa_code) != 6:
             log("Authentication failed: Invalid MFA token format.", level="ERROR")
             return # Changed from return False to just return

         log("MFA token format validated. Verifying...")
         mfa_success, mfa_check_code = kos_bureaucracy.perform_simulated_check("MFA Token Verification", kos_config.BASE_CHECK_DELAY_MEDIUM_MS)

         if mfa_success:
             os_state['user_id'] = temp_user_id
             os_state['is_authenticated'] = True
             os_state['session_start_time'] = kos_utility.time.monotonic() # Start timer on successful auth
             log(f"User '{os_state['user_id']}' authenticated successfully via klogin. Session timer initiated ({kos_config.TIME_LIMIT_SECONDS}s limit).", level="SECURITY")
             kos_bureaucracy.simulate_forwarding(os_state, 'AUTH', os_state['user_id'], detail="Successful Authentication Event (klogin)")
         else:
              log(f"Authentication failed: MFA Token validation failure (Ref: {mfa_check_code}).", level="ERROR")

    else:
        log(f"Authentication failed: Primary credential validation failed (PAM Ref: {check_code}).", level="ERROR")


def handle_logout(os_state, args_dict, positional_args, get_input_func):
     """Handles the klogout command."""
     log = kos_bureaucracy.log_system_message
     if not os_state.get('is_authenticated'):
         log("No active session found to terminate.", level="WARN")
         return

     user = os_state['user_id']
     log(f"Initiating logout sequence for user '{user}'.")
     # Maybe add a pointless confirmation?
     confirm = get_input_func("Confirm logout? Type 'TERMINATE_SESSION': ")
     if confirm != 'TERMINATE_SESSION':
         log("Logout aborted by user.", level="WARN")
         return

     kos_bureaucracy.perform_simulated_check("Session Teardown and Credential Purge", kos_config.BASE_CHECK_DELAY_SHORT_MS)
     kos_bureaucracy.simulate_forwarding(os_state, 'AUTH', user, detail="User Logout Event (klogout)")
     log(f"User '{user}' session terminated.")
     os_state['user_id'] = None
     os_state['is_authenticated'] = False
     os_state['session_start_time'] = 0 # Reset timer

