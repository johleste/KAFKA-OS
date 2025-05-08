# main_kos.py
# Main entry point for the KafkaOS simulation

import sys
import kos_config
import kos_core
import kos_bureaucracy # Needed for initial logging/checks maybe?

# --- Main Execution ---
if __name__ == "__main__":
    # Perform initial boot sequence (simulates loading modules)
    try:
        kos_core.initialize_system()
    except Exception as e:
         # Use basic print here as logging might not be fully ready
         print(f"FATAL BOOT ERROR: {e}")
         sys.exit(10)

    # Enter the main command loop
    try:
        kos_core.command_loop()
    except SystemExit as e:
         # Graceful exit from shutdown or timeout
         kos_core.log_system_message(f"Session terminated with exit code {e.code}.", level="SYSTEM")
    except Exception as e:
        # Catch unexpected errors in the core loop
        kos_core.log_system_message(f"UNHANDLED SYSTEM EXCEPTION in command loop: {e}", level="FATAL")
        print(f"\n*** A CRITICAL SYSTEM ERROR OCCURRED: {e} ***")
        print(f"*** Please report Reference ID: KOS-ERR-CRIT-{kos_utility.pseudo_uuid()[:8]} ***")
        sys.exit(9)
    finally:
         # Ensure some final message if loop exits unexpectedly
         print("\nKafkaOS session ended.")
