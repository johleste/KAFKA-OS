# kos_status.py
# Handles system status commands for KafkaOS

import time # Need monotonic here specifically
import kos_config
import kos_utility
import kos_bureaucracy

def handle_status(os_state, args_dict, positional_args, get_input_func):
    """Handles the kstatus command."""
    log = kos_bureaucracy.log_system_message
    verify = kos_bureaucracy.verify_action_intent
    check_time = os_state['utils']['check_time_limit']

    if not os_state.get('is_authenticated'):
        log("Operation requires authentication. Use 'klogin'.", level="ERROR")
        return

    check_time(os_state['session_start_time'], "System Status Query")

    # Arbitrary operational check
    if not kos_bureaucracy.check_operational_mandate(os_state, required_clearance="SYSTEM_INFO"):
        log("System status query blocked by current operational mandate.", level="WARN")
        return

    # Mandatory flags and purpose code
    compliance_flag = args_dict.get('compliance-check') or args_dict.get('c')
    purpose_code = args_dict.get('p') or args_dict.get('purpose')

    if not compliance_flag:
        log("Procedural error: 'kstatus' requires '--compliance-check' or '-c' flag.", level="ERROR")
        return
    if purpose_code != kos_config.STATUS_PURPOSE_CODE:
         log(f"Procedural error: Requires '-p {kos_config.STATUS_PURPOSE_CODE}' or '--purpose={kos_config.STATUS_PURPOSE_CODE}'. Found: '{purpose_code}'.", level="ERROR")
         return

    # Verification Step (now needs purpose)
    if not verify(os_state, "kstatus -c", get_input_func,
                  requires_purpose=True, purpose_code_expected=kos_config.STATUS_PURPOSE_CODE, requires_reauth=False):
         log("Command aborted due to failed intent verification.", level="WARN")
         return

    log("Initiating System Status Verification Protocol...")
    success, check_code = kos_bureaucracy.perform_simulated_check("Core System Module Health & Compliance Scan", kos_config.BASE_CHECK_DELAY_MEDIUM_MS)

    if success:
         # Apply friction before displaying potentially sensitive (?) status
         kos_bureaucracy.apply_procedural_friction(os_state, reason="Status Report Generation")

         print("\n--- KafkaOS System Status Report ---")
         print(f"  Node ID          : {kos_config.NODE_ID}")
         print(f"  Location         : {kos_config.CURRENT_LOCATION}")
         print(f"  Version          : {kos_config.OS_VERSION}")
         print(f"  Kernel Status    : Nominal")
         print(f"  Auth Status      : {'ACTIVE' if os_state.get('is_authenticated') else 'INACTIVE'} (User: {os_state.get('user_id', 'N/A')})")
         print(f"  Audit Backlog    : {os_state.get('pending_reviews', 0)} items")
         elapsed = time.monotonic() - os_state.get('session_start_time', 0) if os_state.get('session_start_time', 0) else 0
         print(f"  Session Uptime   : {elapsed:.1f}s / {kos_config.TIME_LIMIT_SECONDS}s (Mandate: {kos_config.TIME_LIMIT_MANDATE})")
         print(f"  Compliance Check : Passed (Ref: {check_code})")
         print("----------------------------------\n")
         log("System Status Report generated successfully.")
         kos_bureaucracy.simulate_forwarding(os_state, 'STATUS_QUERY', check_code, detail="System Status Query (-c)")
    else:
         log("System Status check failed during compliance scan.", level="ERROR")

