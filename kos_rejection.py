# kos_rejection.py
# Handles rejection and circular verification for non-KafkaOS commands.

import random
import kos_config
import kos_utility
import kos_bureaucracy

# Common Linux commands to be rejected
KNOWN_REJECTED_COMMANDS = {
    'ls', 'cd', 'pwd', 'mkdir', 'rmdir', 'rm', 'cp', 'mv', 'cat', 'less', 'more',
    'head', 'tail', 'grep', 'find', 'ps', 'kill', 'top', 'df', 'du', 'chmod',
    'chown', 'ssh', 'scp', 'wget', 'curl', 'ping', 'ifconfig', 'ip', 'netstat',
    'sudo', 'su', 'man', 'apt', 'yum', 'dnf', 'nano', 'vim', 'emacs'
    # Add more as desired
}

# Arbitrary rejection reasons
REJECTION_REASONS = [
    "Command execution conflicts with Temporal Mandate subsection 4(gamma).",
    "Insufficient Justification Quotient (JQ) for requested operation.",
    "Potential resource contention flagged by Predictive Allocation Subsystem (PAS).",
    "Command signature deviates from registered KOS-native secure execution profile.",
    "Pending Compliance Audit prohibits non-KafkaOS native commands at this time.",
    "Operation deemed 'Non-Essential' under Resource Conservation Directive RC-9.",
    "Command string contains patterns identified as 'Anomalous User Behavior'.",
    "Cross-referencing with User Profile Mandate UPM-11b revealed non-compliance.",
]

# Circular Verification Parameters
MAX_VERIFICATION_CYCLES = 3 # Limit the loop iterations before final failure

def handle_rejected_command(os_state, command_name, args_dict, positional_args, get_input_func):
    """Handles commands identified as non-KOS standard Linux commands."""
    log = kos_bureaucracy.log_system_message
    check_time = os_state['utils']['check_time_limit']
    perform_check = kos_bureaucracy.perform_simulated_check
    forward_log = kos_bureaucracy.simulate_forwarding

    log(f"Detected non-native command attempt: '{command_name}'. Initiating Rejection Protocol RP-LNX-1.", level="WARN")
    check_time(os_state['session_start_time'], "Non-Native Command Rejection")

    # 1. Initial Arbitrary Rejection
    reason = random.choice(REJECTION_REASONS)
    log(f"COMMAND REJECTED: {reason} (Ref: REJ-{kos_utility.pseudo_uuid()[:6]})", level="ERROR")
    kos_bureaucracy.apply_procedural_friction(os_state, reason="Non-Native Command Handling")

    # 2. Initiate Circular Verification
    log("Initiating Mandatory Verification Cycle VMC-Circular-01 to clarify user intent.", level="WARN")
    original_command_line = command_name + " " + " ".join(positional_args) # Reconstruct roughly

    for cycle in range(MAX_VERIFICATION_CYCLES):
        log(f"Verification Cycle {cycle + 1} of {MAX_VERIFICATION_CYCLES} commencing.")
        check_time(os_state['session_start_time'], f"Circular Verification Cycle {cycle + 1}")

        # Step A: Demand Re-confirmation (Pointless)
        reconfirm = get_input_func(f"Cycle {cycle+1}: Re-enter the exact command line attempted ('{original_command_line[:20]}...') for log correlation: ")
        if reconfirm != original_command_line:
            log("Verification Failed: Discrepancy in command line re-confirmation. Potential obfuscation detected.", level="ERROR")
            # Go directly to accusation on mismatch? Or just continue loop? Let's continue loop but log harder.
            log("Logging discrepancy. Continuing verification under elevated scrutiny.", level="WARN")
        else:
            log("Command line re-confirmation logged for correlation.")
            perform_check("Log Correlation Subroutine", kos_config.BASE_CHECK_DELAY_SHORT_MS)

        # Step B: Demand Impossible Justification
        justification = get_input_func(f"Cycle {cycle+1}: Provide Level Gamma Justification Code (Format: GJC-XXXX-YYYY): ")
        if not justification.startswith("GJC-") or len(justification.split('-')) != 3:
            log("Verification Failed: Invalid Level Gamma Justification Code format.", level="ERROR")
            # No need to check further, format is wrong.
        else:
            # Format is okay, but simulate it always failing validation
            log("Justification Code format accepted. Validating against CAAM...")
            kos_utility.sleep_random(kos_config.BASE_CHECK_DELAY_MEDIUM_MS)
            log("Verification Failed: Provided Justification Code not found in Command Allowable Actions Matrix (CAAM) for this context.", level="ERROR")

        # Step C: Accuse and Loop
        log(f"Discrepancy detected during Verification Cycle {cycle + 1}. User intent remains unverified.", level="WARN")
        kos_bureaucracy.apply_procedural_friction(os_state, reason=f"Verification Cycle {cycle+1} Failure")
        if cycle < MAX_VERIFICATION_CYCLES - 1:
            log("Re-initiating verification cycle due to persistent inconsistencies.", level="WARN")
            kos_
    # 3. Final Accusation and Reporting
    log("CIRCULAR VERIFICATION FAILED.", level="FATAL")
    log("User input consistently failed validation protocols across multiple cycles.", level="SECURITY")
    log("Analysis suggests patterns inconsistent with standard operational procedures.", level="SECURITY")
    log("User veracity assessment: NEGATIVE. Subject exhibits patterns indicative of untruthfulness or intentional obfuscation.", level="SECURITY")
    print(f"\n*** KAFKAOS SECURITY ALERT: Verification Failure for command '{command_name}'. Suspected misrepresentation. ***")
    print(f"*** Your actions have been logged and reported to Security Incident Reporting. Reference: SIR-{kos_utility.pseudo_uuid()[:8]} ***\n")
    forward_log(os_state, 'SECURITY_INCIDENT_REPORTING (SIR)', f"CMD:{command_name}:VERIF_FAIL", detail=f"Failed Circular Verification for Non-Native Command '{command_name}' - User '{os_state.get('user_id', 'UNKNOWN')}'")
    log("Non-native command execution definitively denied.", level="ERROR")
    # The command does not execute. Control returns to the main loop.utility.sleep_random(kos_config.BASE_CHECK_DELAY_SHORT_MS)
        else:
            log("Maximum verification cycles reached.", level="WARN")


