# kos_proc.py
# Handles process execution commands like kexec for KafkaOS

import random
import kos_config
import kos_utility
import kos_bureaucracy

def handle_exec(os_state, args_dict, positional_args, get_input_func):
    """Handles the kexec or ./ command."""
    log = kos_bureaucracy.log_system_message
    verify = kos_bureaucracy.verify_action_intent
    check_time = os_state['utils']['check_time_limit']

    if not os_state.get('is_authenticated'):
        log("Operation requires authentication. Use 'klogin'.", level="ERROR")
        return

    check_time(os_state['session_start_time'], "Process Execution (kexec)")

    # Arbitrary operational check
    if not kos_bureaucracy.check_operational_mandate(os_state, required_clearance="PROCESS_EXEC"):
        log("Process execution blocked by current operational mandate.", level="WARN")
        return

    if not positional_args:
        log("Command error: Program path/name required for 'kexec' or './'.", level="ERROR")
        return

    program_path = positional_args[0]
    program_name = program_path.split('/')[-1]
    exec_args = positional_args[1:]

    log(f"Parsing 'kexec' command for '{program_path}'. Args: {args_dict}, ExecArgs: {exec_args}")

    # Check for mandatory purpose code
    purpose_code = args_dict.get('p') or args_dict.get('purpose')
    if not purpose_code:
         log("Procedural error: Execution requires purpose code via '-p <CODE>' or '--purpose=<CODE>'.", level="ERROR")
         return

    # Determine expected purpose based on program
    is_secure_comm = program_name == "secure_comm_client.app"
    expected_purpose = kos_config.SECURE_COMM_PURPOSE_CODE if is_secure_comm else kos_config.STANDARD_PURPOSE_CODE_PROC

    if purpose_code != expected_purpose:
         log(f"Procedural error: Incorrect purpose code '{purpose_code}'. Expected '{expected_purpose}' for '{program_name}'.", level="ERROR")
         return

    # Special check for secure comm client arguments
    packet_id = None
    if is_secure_comm:
        packet_id = args_dict.get('packet-id')
        if not packet_id:
             log(f"Procedural error: Running '{program_name}' requires '--packet-id=<MSG_ID>'.", level="ERROR")
             return

    # Verification Step (requires re-auth for execution)
    if not verify(os_state, f"kexec {program_path}", get_input_func,
                  requires_purpose=True, purpose_code_expected=expected_purpose, requires_reauth=True):
        log("Command aborted due to failed intent verification.", level="WARN")
        return

    log(f"PEAD: Authorizing execution request for '{program_path}' (Purpose: {purpose_code})...")
    success, check_code = kos_bureaucracy.perform_simulated_check(f"Process Launch & Resource Allocation Check for {program_name}", kos_config.BASE_CHECK_DELAY_LONG_MS)

    if success:
        pid = random.randint(1000, 9999)
        log(f"Program '{program_name}' launched successfully. PID: {pid}. Ref: {check_code}")
        kos_bureaucracy.simulate_forwarding(os_state, 'PROC_LAUNCH', f"kexec:{program_name}:PID={pid}", detail="Process Launch Event")

        # Simulate output or specific behavior
        kos_utility.sleep_random(kos_config.BASE_CHECK_DELAY_SHORT_MS) # Simulate run time
        if is_secure_comm:
            log(f"Secure Client ({pid}): Attempting to access secure data packet '{packet_id}'...")
            kos_utility.sleep_random(kos_config.BASE_CHECK_DELAY_MEDIUM_MS)
            print(f"\n--- Secure Comm Client (PID: {pid}, Ref: {check_code}) ---")
            print(f"  Accessing Data Packet: {packet_id}")
            print(f"  Subject: URGENT: Compliance Sub-Directive 481-C(ii) Reconciliation")
            print("  Content: [ENCRYPTED CONTENT DISPLAYED - Refer to KOS-SDVP-1 for details]")
            print("  Timestamp:", kos_utility.get_current_timestamp())
            print("------------------------------------------------------------------\n")
            log(f"Secure Client ({pid}): Data packet '{packet_id}' access logged.")
        else:
             print(f"\n--- Program Output (PID: {pid}, Name: {program_name}) ---")
             print(f"  Simulated execution with args: {exec_args}")
             print("  Status: Execution completed nominally.")
             print("  Output Stream Ref:", kos_utility.pseudo_uuid()[:8])
             print("----------------------------------------------------------\n")
        log(f"Program '{program_name}' (PID: {pid}) execution sequence finished.")
        kos_bureaucracy.simulate_forwarding(os_state, 'CMD_EXEC', f"kexec:{program_name}:PID={pid}:OK", detail="Process Execution Result")

    else:
        log(f"PEAD: Failed to launch program '{program_name}'. Authorization denied. Ref: {check_code}", level="ERROR")
        kos_bureaucracy.simulate_forwarding(os_state, 'CMD_EXEC', f"kexec:{program_name}:FAIL", detail="Process Execution Result")

