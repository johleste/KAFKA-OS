# kos_shutdown.py
# Handles system shutdown commands for KafkaOS

import datetime
import sys
import kos_config
import kos_utility
import kos_bureaucracy

def handle_shutdown(os_state, args_dict, positional_args, get_input_func=None, forced=False): # Add get_input_func
    """Handles khalt, shutdown, exit commands."""
    log = kos_bureaucracy.log_system_message
    verify = kos_bureaucracy.verify_action_intent # Needed if not forced
    check_time = os_state['utils']['check_time_limit'] # Needed if not forced

    log("System Halt Sequence Initiated.", level="WARN")

    is_forced = forced or args_dict.get('force') or args_dict.get('f')

    if not os_state.get('is_authenticated') and not is_forced:
         log("Shutdown requires authentication ('klogin') or '--force' / '-f' flag.", level="ERROR")
         return

    if not is_forced:
        # Check time BEFORE verification
        check_time(os_state['session_start_time'], "System Shutdown Sequence")

        # Require time-based code via --auth-code=...
        now = datetime.datetime.now()
        code_suffix = f"{now.minute:02d}{now.second % 10}"
        expected_code = kos_config.SHUTDOWN_AUTH_CODE_BASE + code_suffix
        provided_code = args_dict.get('auth-code')

        # Verification requires re-auth
        if not verify(os_state, "khalt (authenticated)", get_input_func,
                      requires_purpose=False, requires_reauth=True):
             log("Shutdown aborted due to failed intent verification.", level="WARN")
             return

        if provided_code != expected_code:
             log(f"Shutdown authorization failed: Incorrect or missing '--auth-code'. Expected '{expected_code}'.", level="ERROR")
             return
        log("Shutdown authorization code validated.")

    log("Performing final compliance checks before system halt...")
    kos_bureaucracy.perform_simulated_check("Pre-Shutdown Compliance Verification", kos_config.BASE_CHECK_DELAY_MEDIUM_MS)
    log("Flushing critical audit logs to secure persistent storage...")
    kos_bureaucracy.perform_simulated_check("Audit Log Synchronization", kos_config.BASE_CHECK_DELAY_LONG_MS)

    kos_bureaucracy.simulate_forwarding(os_state, 'SHUTDOWN', f"Forced={is_forced}", detail="System Halt Event")
    log(f"KafkaOS is halting NOW. Reason: {'Forced Override' if is_forced else 'Authorized Operator Command'}.", level="WARN")
    print(f"\n*** KAFKAOS SYSTEM HALT INITIATED ({kos_utility.get_current_timestamp()}) ***")
    os_state['is_authenticated'] = False # Log out state before exit
    sys.exit(0)
