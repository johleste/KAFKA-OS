import datetime
import random
import time
import uuid


REVIEW_ENTITIES = {
    'BOOT':               "System Initialization Audit Log (SIAL)",
    'AUTH':               "Pluggable Authentication Module Verifier (PAMV)",
    'CMD_INTENT':         "Command Intent Review Unit (CIRU)",
    'CMD_EXEC':           "Execution Result Log Monitor (ERLM)",
    'FS_ACCESS':          "Filesystem Access Control Monitor (FACM)",
    'FS_WRITE':           "Write Operation Integrity Daemon (WOID)",
    'PROC_LAUNCH':        "Process Execution Authorization Daemon (PEAD)",
    'STATUS_QUERY':       "System Health Monitoring Log (SHML)",
    'SHUTDOWN':           "System Termination Oversight Protocol (STOP)",
    'COMPLIANCE':         "Regulatory Compliance Check Subsystem (RCCS)",
    'ARBITRARY_LOCKOUT':  "Operational Mandate Enforcement Unit (OMEU)",
    'RE_AUTH':            "Secondary Authentication Verification Log (SAVL)",
    'PURPOSE_VALIDATION': "Justification Code Audit Service (JCAS)",
    'NETWORK':            "Network Activity Surveillance Log (NASL)",
    'PRIVILEGE_ESC':      "Privilege Escalation Containment Unit (PECU)",
    'SECURITY':           "Security Incident Reporting (SIR)",
}

REJECTION_REASONS = [
    "Command execution conflicts with Temporal Mandate subsection 4(gamma).",
    "Insufficient Justification Quotient (JQ) for requested operation.",
    "Potential resource contention flagged by Predictive Allocation Subsystem (PAS).",
    "Command signature deviates from registered secure execution profile.",
    "Pending Compliance Audit prohibits this operation at this time.",
    "Operation deemed 'Non-Essential' under Resource Conservation Directive RC-9.",
    "Command string contains patterns identified as 'Anomalous User Behavior'.",
    "Cross-referencing with User Profile Mandate UPM-11b revealed non-compliance.",
    "Operation blocked: elevated risk score assigned by Behavioral Analytics Engine.",
    "Command rate limit exceeded per Fair Use Directive FUD-3.2.1.",
    "Prior session anomaly flag has not been cleared. Contact your administrator.",
]

NETWORK_REJECTION_REASONS = [
    "TLS certificate chain validation pending PKI team approval (Ref: PKI-HOLD-{ref}).",
    "Outbound connection requires Security Gateway pre-authorization (Form SG-7701).",
    "Destination IP not in approved Egress Allowlist. Submit change request via ITSM.",
    "Deep Packet Inspection flagged payload as non-compliant. Session logged.",
    "DNS resolution deferred pending DNSSEC validation by Security Operations.",
    "Connection throttled: bandwidth allocation quota exhausted for current period.",
]


class BureaucracyEngine:
    def __init__(self, config: dict, output_func=None):
        self.cfg = config.get("bureaucracy", {})
        self.out = output_func or print
        self._pending_reviews = 0

    # ------------------------------------------------------------------ helpers

    def _sleep(self, base_ms, jitter_ms=300):
        time.sleep((base_ms + random.uniform(50, jitter_ms)) / 1000.0)

    def _uuid(self):
        return str(uuid.uuid4()).upper()

    def _short_ref(self):
        return self._uuid()[:8]

    def _ts(self):
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

    # ------------------------------------------------------------------ logging

    def log(self, message, level="INFO"):
        self.out(f"{self._ts()} kernel: [{level}] {message}")
        self._sleep(self.cfg.get("base_msg_delay_ms", 200))

    # ------------------------------------------------------------------ checks

    def simulated_check(self, name, duration_key="base_check_medium_ms"):
        self.log(f"Subsystem Check: Initiating {name}...")
        self._sleep(self.cfg.get(duration_key, 1300))
        ref = f"{name[:3].upper()}-{self._short_ref()}"
        self.log(f"Subsystem Check: {name} completed. Status: OK. Ref: {ref}")
        return ref

    def forward(self, entity_key, context_ref, detail="Operational Context"):
        entity = REVIEW_ENTITIES.get(entity_key, "Default Audit Sink")
        fwd_id = f"KOS-FWD-{entity_key}-{self._short_ref()}"
        self.log(f"AUDIT: Forwarding {detail} (Ref: {context_ref}) to '{entity}'. ID: {fwd_id}")
        self._pending_reviews += 1
        self._sleep(self.cfg.get("base_forwarding_delay_ms", 750))
        self.log(f"AUDIT: Ack received from '{entity}'. Pending Reviews: {self._pending_reviews}")

    def friction(self, reason="Standard Operational Delay"):
        threshold = self.cfg.get("high_friction_threshold", 5)
        if self._pending_reviews > threshold:
            self.log(f"Applying procedural friction — audit backlog ({self._pending_reviews} items). "
                     f"Reason: {reason}.", level="WARN")
            self._sleep(self.cfg.get("base_check_short_ms", 800))

    # ------------------------------------------------------------------ mandate

    def check_mandate(self, clearance="STANDARD"):
        now = datetime.datetime.now()
        self.log(f"Mandate Check: Verifying operational allowances for clearance '{clearance}'...",
                 level="DEBUG")
        self.friction(reason="Mandate Compliance Check")

        # Arbitrary rule: filesystem locked during prime minutes on Tuesday
        if clearance == "FILESYSTEM" and now.weekday() == 1:
            m = now.minute
            is_prime = m >= 2 and all(m % i != 0 for i in range(2, int(m**0.5) + 1))
            if is_prime:
                self.log(f"Operation Denied: Filesystem restricted during prime minute ({m}) "
                         f"on Tuesday. Directive FS-TUE-PRIME.", level="ERROR")
                self.forward('ARBITRARY_LOCKOUT', f"FS-PRIME-{m}", "Operational Denial Event")
                return False

        # Audit backlog lockout
        if self._pending_reviews > 10 and random.random() < 0.2:
            self.log(f"Operation Denied: Critical audit backlog ({self._pending_reviews} items). "
                     f"Mandate AUDIT-BACKLOG-LOCK.", level="ERROR")
            return False

        # Random compliance spot-check
        if random.random() < self.cfg.get("random_failure_chance", 0.05):
            ref = self._short_ref()[:4]
            self.log(f"Operation Denied: Random compliance spot-check failed "
                     f"(Ref: SPOT-{ref}). Retry the command.", level="ERROR")
            return False

        self.log(f"Mandate check passed for clearance '{clearance}'.", level="DEBUG")
        return True

    # ------------------------------------------------------------------ verification

    def verify_intent(self, session, command_name, requires_reauth=False):
        self.log(f"PROC_VERIFY: Initiating Intent Verification Protocol for '{command_name}'.")
        self.friction(reason="Intent Verification Start")
        phrase = "I_ACKNOWLEDGE_AND_COMPLY_WITH_ALL_PROTOCOLS"

        confirm = session.prompt(f"Verify intent for '{command_name}'. "
                                 f"Type EXACTLY '{phrase}': ")
        if confirm != phrase:
            self.log("PROC_VERIFY: Failed — incorrect confirmation phrase.", level="ERROR")
            return False
        self.log("PROC_VERIFY: Confirmation phrase validated.")
        self.simulated_check("Intent Confirmation Logging", "base_check_short_ms")

        if requires_reauth and session.username:
            self.log("PROC_VERIFY: Secondary authentication challenge required.", level="WARN")
            re_id = session.prompt(f"Re-enter your username ('{session.username}') to confirm: ")
            if re_id != session.username:
                self.log("PROC_VERIFY: Failed — identity mismatch.", level="ERROR")
                self.forward('RE_AUTH', f"{command_name}-FAIL", "Re-Authentication Failure")
                return False
            self.log("PROC_VERIFY: Secondary authentication successful.")
            self.simulated_check("Re-authentication PAM Check", "base_check_medium_ms")
            self.forward('RE_AUTH', f"{command_name}-OK", "Re-Authentication Success")

        self.friction(reason="Intent Verification Complete")
        self.log(f"PROC_VERIFY: Protocol for '{command_name}' completed successfully.")
        self.forward('CMD_INTENT', f"{command_name}-{self._short_ref()[:4]}",
                     "Command Intent Verification Complete")
        return True

    # ------------------------------------------------------------------ circular rejection

    def circular_rejection(self, session, command_name):
        max_cycles = self.cfg.get("max_verification_cycles", 3)
        self.log(f"Detected non-native command: '{command_name}'. "
                 f"Initiating Rejection Protocol RP-LNX-1.", level="WARN")
        reason = random.choice(REJECTION_REASONS)
        self.log(f"COMMAND REJECTED: {reason} (Ref: REJ-{self._short_ref()[:6]})", level="ERROR")
        self.friction(reason="Non-Native Command Handling")
        self.log("Initiating Mandatory Verification Cycle VMC-Circular-01.", level="WARN")

        for cycle in range(max_cycles):
            self.log(f"Verification Cycle {cycle + 1} of {max_cycles} commencing.")

            reconfirm = session.prompt(
                f"Cycle {cycle+1}: Re-enter the exact command attempted "
                f"('{command_name[:20]}') for log correlation: ")
            if reconfirm != command_name:
                self.log("Verification Failed: Command line discrepancy detected. "
                         "Potential obfuscation.", level="ERROR")
                self.log("Logging discrepancy. Continuing under elevated scrutiny.", level="WARN")
            else:
                self.log("Command re-confirmation logged.")
                self.simulated_check("Log Correlation Subroutine", "base_check_short_ms")

            justification = session.prompt(
                f"Cycle {cycle+1}: Provide Level Gamma Justification Code "
                f"(Format: GJC-XXXX-YYYY): ")
            parts = justification.split("-")
            if not justification.startswith("GJC-") or len(parts) != 3:
                self.log("Verification Failed: Invalid Level Gamma Justification Code format.",
                         level="ERROR")
            else:
                self.log("Justification Code format accepted. Validating against CAAM...")
                self._sleep(self.cfg.get("base_check_medium_ms", 1300))
                self.log("Verification Failed: Code not found in Command Allowable Actions Matrix "
                         "(CAAM) for this context.", level="ERROR")

            self.log(f"Discrepancy detected in Cycle {cycle + 1}. Intent remains unverified.",
                     level="WARN")
            self.friction(reason=f"Verification Cycle {cycle+1} Failure")
            if cycle < max_cycles - 1:
                self.log("Re-initiating due to persistent inconsistencies.", level="WARN")
                self._sleep(self.cfg.get("base_check_short_ms", 800))

        self.log("CIRCULAR VERIFICATION FAILED.", level="FATAL")
        self.log("Patterns inconsistent with standard operational procedures.", level="SECURITY")
        self.log("User veracity assessment: NEGATIVE.", level="SECURITY")
        ref = self._short_ref()
        self.out(f"\n*** SECURITY ALERT: Verification failure for '{command_name}'. "
                 f"Suspected misrepresentation. ***")
        self.out(f"*** Actions logged to Security Incident Reporting. Ref: SIR-{ref} ***\n")
        self.forward('SECURITY', f"CMD:{command_name}:VERIF_FAIL",
                     f"Circular Verification Failure — command '{command_name}'")

    # ------------------------------------------------------------------ network stall

    def network_stall(self, session, destination, protocol="TCP"):
        self.log(f"NASL: Outbound {protocol} connection request to {destination} detected.")
        self.simulated_check("Egress Policy Evaluation", "base_check_medium_ms")
        self.forward('NETWORK', f"{protocol}:{destination}", "Outbound Connection Attempt")

        self.log("Establishing connection...", level="INFO")
        # Show progress that stalls
        stall_at = self.cfg.get("download_stall_at", 0.94)
        steps = 20
        stall_step = int(steps * stall_at)
        for i in range(steps):
            pct = int((i / steps) * 100)
            bar = "=" * i + ">" + " " * (steps - i - 1)
            self.out(f"\r  [{bar}] {pct}%", end="", flush=True)
            self._sleep(400 if i < stall_step else 2000)
            if i == stall_step:
                self.out()
                reason = random.choice(NETWORK_REJECTION_REASONS).format(ref=self._short_ref()[:6])
                self.log(f"Connection stalled: {reason}", level="ERROR")
                self.log("Session will be retried automatically when clearance is obtained.",
                         level="WARN")
                return False
        return False

    # ------------------------------------------------------------------ download progress

    def download_progress(self, filename, size_kb):
        stall_at = self.cfg.get("download_stall_at", 0.94)
        steps = 30
        stall_step = int(steps * stall_at)
        self.out(f"Downloading {filename}... ({size_kb}K)")
        for i in range(steps + 1):
            pct = int((i / steps) * 100)
            done_k = int((i / steps) * size_kb)
            bar = "#" * i + " " * (steps - i)
            self.out(f"\r  [{bar}] {done_k}K/{size_kb}K ({pct}%)", end="", flush=True)
            self._sleep(300 if i < stall_step else 2500)
            if i == stall_step:
                self.out()
                self.log(f"Transfer interrupted: TLS certificate validation pending "
                         f"PKI team approval (Ref: PKI-{self._short_ref()[:6]}).", level="ERROR")
                self.log("Partial download discarded per Security Directive SD-4.1.", level="WARN")
                return False
        return False

    # ------------------------------------------------------------------ compile progress

    def compile_progress(self, target):
        fail_at = self.cfg.get("compile_fail_at", 0.97)
        steps = 40
        fail_step = int(steps * fail_at)
        self.out(f"Building target: {target}")
        for i in range(steps + 1):
            pct = int((i / steps) * 100)
            self.out(f"\r  Compiling... {pct}%", end="", flush=True)
            self._sleep(600)
            if i == fail_step:
                self.out()
                self.log(f"Build failed: Compiler output flagged by Static Analysis Daemon "
                         f"(SAD-{self._short_ref()[:4]}). Compilation aborted.", level="ERROR")
                self.out(f"  error: operation not permitted under Mandate COMP-CTRL-9b")
                self.out(f"  make: *** [{target}] Error 1")
                return False
        return False
