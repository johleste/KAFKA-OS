# kos_core.py
# Core OS state management, command loop, parsing, time checks

import time
import sys

# Import other OS modules
import kos_config
import kos_utility
import kos_bureaucracy
import kos_auth
import kos_fs
import kos_proc
import kos_status
import kos_shutdown

# --- Core OS State ---
os_state = {
    'user_id': None,
    'is_authenticated': False,
    'session_start_time': 0,
    'pending_reviews': 0,
    'current_directory': "/home/user",
    'last_command_ref': None,
    # Pass utility functions needed by other modules if not importing directly
    'utils': {
        'check_time_limit': None # Will be assigned later
    }
}

# --- Core Functions ---

def log_system_message(message, level="INFO"):
    """Wrapper to call bureaucracy logging."""
    kos_bureaucracy.log_system_message(message, level)

def check_time_limit(step_name="Operational Phase"):
    """Checks the global time limit using the stored start time."""
    if os_state['session_start_time'] == 0: return # Timer not started
    elapsed_time = time.monotonic() - os_state['session_start_time']
    remaining_time = kos_config.TIME_LIMIT_SECONDS - elapsed_time
    # Log more subtly now
    if elapsed_time > kos_config.TIME_LIMIT_SECONDS * 0.8: # Warn when close
         log_system_message(f"Temporal constraint check ({step_name}). Remaining: {remaining_time:.1f}s.", level="WARN")
    else:
         log_system_message(f"Temporal constraint check ({step_name}). Elapsed: {elapsed_time:.1f}s.", level="DEBUG")

    if elapsed_time > kos_config.TIME_LIMIT_SECONDS:
        log_system_message(f"FATAL ERROR: Session quantum ({kos_config.TIME_LIMIT_SECONDS}s) depleted ({elapsed_time:.2f}s elapsed).", level="FATAL")
        log_system_message(f"Violation logged against {kos_config.TIME_LIMIT_MANDATE}. Session terminated.", level="FATAL")
        print(f"\n*** KAFKAOS SESSION TIMEOUT ({kos_config.TIME_LIMIT_MANDATE}) - CONNECTION TERMINATED ***")
        sys.exit(2)

# Assign the function to the state dict for bureaucracy module to use
os_state['utils']['check_time_limit'] = check_time_limit

def get_user_input(prompt_override=None):
    """Gets input, using a Linux-style prompt constructed from os_state."""
    if prompt_override:
        prompt = f" > {prompt_override}: "
    else:
        user_part = f"{os_state['user_id'] or 'unauthenticated'}@{kos_config.NODE_ID.split('-')[2].lower()}"
        cwd_part = os_state['current_directory']
        pending_part = f"{{REV:{os_state['pending_reviews']}}}" if os_state['pending_reviews'] > 0 else ""
        prompt = f"[{user_part} {cwd_part}{pending_part}]$ "

    try:
        user_input = input(prompt)
        log_system_message(f"Input detected: '{user_input[:40]}{'...' if len(user_input)>40 else ''}'. Parsing...", level="DEBUG")
        kos_utility.sleep_random(kos_config.BASE_INPUT_PROC_DELAY_MS)
        return user_input.strip()
    except EOFError:
        log_system_message("EOF detected. Initiating emergency halt.", level="FATAL")
        kos_shutdown.handle_shutdown(os_state, {}, [], forced=True) # Call shutdown handler
    except KeyboardInterrupt:
        print() # Print newline after ^C
        log_system_message("Keyboard interrupt (SIGINT) received. Use 'khalt' or 'exit'.", level="WARN")
        return ""

def parse_args(arg_list):
    """Basic parser for flags and positional args."""
    args = {}
    positional = []
    i = 0
    while i < len(arg_list):
        arg = arg_list[i]
        if arg.startswith('--'):
            if '=' in arg:
                key, value = arg.split('=', 1)
                args[key[2:]] = value
            else:
                key = arg[2:]
                if i + 1 < len(arg_list) and not arg_list[i+1].startswith('-'):
                    args[key] = arg_list[i+1]
                    i += 1
                else:
                    args[key] = True
        elif arg.startswith('-'):
            # Treat -abc as -a -b -c for simplicity
            for char in arg[1:]:
                 args[char] = True
        else:
            positional.append(arg)
        i += 1
    return args, positional


def print_help():
     # Defined here as it uses config constants
     print("\n--- KafkaOS Simulated Command Help ---")
     print("  klogin                  - Initiate user authentication sequence.")
     print("  klogout                 - Terminate current user session.")
     print("  kls | ls [path] --view-mode=<mode> -p <purpose_code>")
     print("                          - List directory contents. Mode ('standard'/'audit') depends on current minute.")
     print(f"                            Requires purpose code: {kos_config.STANDARD_PURPOSE_CODE_FS}")
     print("  kexec | ./<prog> [args...] -p <purpose_code> [--packet-id=<id>]")
     print("                          - Execute a program simulation.")
     print(f"                            Requires standard purpose: {kos_config.STANDARD_PURPOSE_CODE_PROC}")
     print(f"                            Secure client purpose: {kos_config.SECURE_COMM_PURPOSE_CODE} (requires --packet-id)")
     print(f"  kstatus -c | --compliance-check -p {kos_config.STATUS_PURPOSE_CODE}")
     print(f"                          - Display system status (mandatory flags/purpose).")
     print("  khalt | shutdown [--force | -f] [--auth-code=<CODE>]")
     print("                          - Initiate system halt (requires time-sensitive auth code unless forced).")
     print("  exit                    - Alias for shutdown.")
     print("  help                    - Display this message.")
     print("--------------------------------------\n")

# --- Command Mapping (Uses functions from imported modules) ---
COMMANDS = {
    "klogin": kos_auth.handle_login,
    "klogout": kos_auth.handle_logout,
    "kls": kos_fs.handle_ls,
    "ls": kos_fs.handle_ls, # Alias
    "kexec": kos_proc.handle_exec,
    "./": kos_proc.handle_exec, # Basic simulation
    "kstatus": kos_status.handle_status,
    "khalt": kos_shutdown.handle_shutdown,
    "shutdown": kos_shutdown.handle_shutdown, # Alias
    "exit": kos_shutdown.handle_shutdown, # Alias
    "help": lambda state, ad, pa: print_help(), # Lambda needs state now? No, help is stateless.
}

# --- Command Loop ---
def command_loop():
    global os_state # Allow modification
    while True:
        check_time_limit("Idle State") # Check time limit periodically
        full_command_line = get_user_input()
        if not full_command_line:
            continue

        parts = full_command_line.split()
        command_name_raw = parts[0]
        command_args_raw = parts[1:]

        command_handler = None
        args_dict = {}
        positional_args = []

        # Handle ./program syntax before lowercasing command
        if command_name_raw.startswith("./"):
             command_handler = COMMANDS.get("./")
             # Pass all parts for ./ handler to parse program name + args
             args_dict, positional_args = parse_args(parts) # Positional will include ./program
        else:
             command_name = command_name_raw.lower()
             command_handler = COMMANDS.get(command_name)
             args_dict, positional_args = parse_args(command_args_raw)


        os_state['last_command_ref'] = f"CMD-{kos_utility.pseudo_uuid()[:6]}"
        log_system_message(f"Processing command: '{command_name_raw}', Args: {args_dict}, Positional: {positional_args}, Ref: {os_state['last_command_ref']}", level="CMD")

        # Pre-command arbitrary check
        if command_handler and command_name_raw not in ['klogin', 'help', 'exit', 'shutdown', 'khalt']: # Don't lock out login/help/shutdown
            if not kos_bureaucracy.check_operational_mandate(os_state, required_clearance="STANDARD"):
                 log_system_message(f"Command '{command_name_raw}' blocked by operational mandate.", level="WARN")
                 continue # Skip command execution

        if command_handler:
             try:
                 # Pass necessary state and input function to handlers
                 command_handler(os_state, args_dict, positional_args, get_input_func=get_user_input)
                 log_system_message(f"Command '{command_name_raw}' processing complete (Ref: {os_state['last_command_ref']}).", level="CMD")
             except Exception as e:
                 log_system_message(f"Runtime error during execution of '{command_name_raw}': {e}", level="ERROR")
                 print(f"*** Error executing command '{command_name_raw}'. Consult system logs. ***")
        elif command_name_raw not in ['help']: # Don't log error for implicit help call
             log_system_message(f"Unknown command: '{command_name_raw}'. Command ignored. Type 'help'.", level="ERROR")


def initialize_system():
    """Performs the boot sequence simulation."""
    print("="*70)
    print(f"Booting {kos_config.OS_NAME}...")
    print(f"Node Identifier: {kos_config.NODE_ID}")
    print(f"Operational Sector: {kos_config.CURRENT_LOCATION}")
    print(f"System Timestamp: {kos_utility.get_current_timestamp()}")
    print(f"Kernel Build: {kos_config.OS_VERSION}")
    print("="*70)
    log_system_message("Boot sequence started.", level="SYSTEM")
    kos_bureaucracy.perform_simulated_check("Core Kernel Module Integrity Verification", kos_config.BASE_CHECK_DELAY_MEDIUM_MS)
    log_system_message("Loading Module: kos_auth (Authentication Services)...")
    kos_utility.sleep_random(kos_config.BASE_CHECK_DELAY_SHORT_MS)
    log_system_message("Loading Module: kos_fs (Filesystem Interface Layer)...")
    kos_utility.sleep_random(kos_config.BASE_CHECK_DELAY_SHORT_MS)
    log_system_message("Loading Module: kos_proc (Process Execution Subsystem)...")
    kos_utility.sleep_random(kos_config.BASE_CHECK_DELAY_SHORT_MS)
    log_system_message("Loading Module: kos_status (System Health Monitor)...")
    kos_utility.sleep_random(kos_config.BASE_CHECK_DELAY_SHORT_MS)
    log_system_message("Loading Module: kos_shutdown (Termination Control)...")
    kos_utility.sleep_random(kos_config.BASE_CHECK_DELAY_SHORT_MS)
    log_system_message("Loading Module: kos_bureaucracy (Compliance & Oversight Engine)...")
    kos_utility.sleep_random(kos_config.BASE_CHECK_DELAY_MEDIUM_MS)
    kos_bureaucracy.perform_simulated_check("Initializing Audit & Compliance Subsystems (RCCS)", kos_config.BASE_CHECK_DELAY_SHORT_MS)
    kos_bureaucracy.perform_simulated_check("Final Compliance Scan against Mandate Delta-Fragmented", kos_config.BASE_CHECK_DELAY_LONG_MS)
    log_system_message("Applying session temporal constraints via " + kos_config.TIME_LIMIT_MANDATE)
    kos_bureaucracy.simulate_forwarding(os_state, 'BOOT', kos_config.OS_VERSION, detail="System Boot Event")
    log_system_message("System boot sequence complete. Awaiting user authentication.", level="SYSTEM")
    print("="*70)
    print(f"Welcome to {kos_config.OS_NAME} on {kos_config.NODE_ID}.")
    print(f"System time: {kos_utility.get_current_timestamp()}. Location: {kos_config.CURRENT_LOCATION}.")
    print(f"NOTICE: Session duration limited to {kos_config.TIME_LIMIT_SECONDS}s ({kos_config.TIME_LIMIT_MANDATE}).")
    print("Type 'klogin' to authenticate or 'help' for commands.")
    print("="*70 + "\n")

