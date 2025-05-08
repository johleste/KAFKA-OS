# kos_fs.py
# Handles filesystem commands like kls for KafkaOS

import datetime
import kos_config
import kos_utility
import kos_bureaucracy

def handle_ls(os_state, args_dict, positional_args, get_input_func):
    """Handles the kls command."""
    log = kos_bureaucracy.log_system_message
    verify = kos_bureaucracy.verify_action_intent
    check_time = os_state['utils']['check_time_limit']

    if not os_state.get('is_authenticated'):
        log("Operation requires authentication. Use 'klogin'.", level="ERROR")
        return

    check_time(os_state['session_start_time'], "Filesystem Operation (kls)")

    # Arbitrary operational check
    if not kos_bureaucracy.check_operational_mandate(os_state, required_clearance="FILESYSTEM"):
        log("Filesystem operation blocked by current operational mandate.", level="WARN")
        return

    log(f"Parsing 'kls' command. Args: {args_dict}, Path: {positional_args}")
    target_dir = positional_args[0] if positional_args else os_state['current_directory']

    # Conditional argument requirement based on time
    now = datetime.datetime.now()
    expected_mode = "audit" if now.minute % 2 == 0 else "standard"
    provided_mode = args_dict.get('view-mode')

    if provided_mode != expected_mode:
        log(f"Procedural error: Required '--view-mode={expected_mode}' for current temporal context (Minute: {now.minute}). Found: '{provided_mode}'. Command rejected.", level="ERROR")
        return

    # Check for mandatory purpose code via -p or --purpose
    purpose_code = args_dict.get('p') or args_dict.get('purpose')
    if purpose_code != kos_config.STANDARD_PURPOSE_CODE_FS:
         log(f"Procedural error: Requires '-p {kos_config.STANDARD_PURPOSE_CODE_FS}' or '--purpose={kos_config.STANDARD_PURPOSE_CODE_FS}'. Found: '{purpose_code}'. Command rejected.", level="ERROR")
         return

    # Verification Step
    if not verify(os_state, f"kls {target_dir} --view-mode={expected_mode}", get_input_func,
                  requires_purpose=True, purpose_code_expected=kos_config.STANDARD_PURPOSE_CODE_FS, requires_reauth=False): # No reauth needed?
        log("Command aborted due to failed intent verification.", level="WARN")
        return

    log(f"Querying directory manifest for '{target_dir}' (Mode: {expected_mode})...")
    success, check_code = kos_bureaucracy.perform_simulated_check("Filesystem Index Scan & ACL Check", kos_config.BASE_CHECK_DELAY_MEDIUM_MS)

    if success:
        # Simulate ls -l output
        print(f"\nDirectory Listing: {target_dir} (Mode: {expected_mode}, Ref: {check_code})")
        print("Permissions  Owner       Group       Size      Modified           Name                     KafkaRef")
        print("-----------------------------------------------------------------------------------------------------")
        print("-rw-r--r--  SysAdmin    SysAuditor  10248   2025-04-10 11:30   report-Q1-final.doc      FS-DOC-001")
        print("-rw-------  SysAdmin    SysAuditor  512340  2025-04-15 09:15   compliance_audit.log     FS-LOG-44B")
        print("-rwxr-xr-x  SysAdmin    SysOperator 15360   2025-03-01 16:00   secure_comm_client.app   FS-APP-901")
        print("-r--------  SysAdmin    SecReviewer 8192    2025-04-14 18:05   data_packet_MSG-XYZ789   FS-DATA-XYZ")
        if expected_mode == "audit":
             print("-rw-------  SysAdmin    SysAuditor   980    " + kos_utility.get_current_timestamp(False) + "   .kls_audit_trail         FS-AUD-KLS") # Dynamic timestamp
        print("-----------------------------------------------------------------------------------------------------\n")
        log("Directory manifest query completed.")
        kos_bureaucracy.simulate_forwarding(os_state, 'FS_ACCESS', f"kls:{target_dir}:{expected_mode}", detail="Directory List Event")
    else:
        log(f"Directory manifest query failed for '{target_dir}'. Check permissions or path.", level="ERROR")
