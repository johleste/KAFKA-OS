import random
import time


SUDO_FAIL_MESSAGES = [
    "sudo: {user} is not in the sudoers file. This incident will be reported.",
    "sudo: PAM authentication failed after {n} retries.",
    "sudo: MFA token expired during secondary verification (Ref: MFA-{ref}).",
    "sudo: Privilege escalation request denied — clearance level insufficient.",
    "sudo: Account temporarily locked due to failed authentication attempts.",
    "sudo: Approval request submitted to IT Security. ETA: 3-5 business days.",
]

SU_FAIL_MESSAGES = [
    "su: Authentication failure",
    "su: Permission denied",
    "su: Account is locked — contact your system administrator.",
]


def cmd_sudo(session, args, bure):
    if not args:
        session.write("usage: sudo [-u user] command\n")
        return

    bure.log("PECU: Privilege escalation attempt detected.", level="WARN")
    bure.simulated_check("Privilege Escalation Risk Assessment", "base_check_medium_ms")
    bure.forward('PRIVILEGE_ESC', f"sudo:{session.username}", "Privilege Escalation Attempt")

    # Ask for password
    password = session.prompt_secret("[sudo] password for " + session.username + ": ")
    bure.log("PECU: Credential received. Validating against PAM...")
    bure.simulated_check("PAM Privilege Validation", "base_check_long_ms")

    # Require MFA
    bure.log("PECU: Primary credential accepted. Secondary factor required.", level="INFO")
    mfa = session.prompt_secret("Enter MFA token (TOTP): ")
    if not mfa:
        session.write("sudo: no MFA token provided\n")
        return

    bure.log("PECU: Validating MFA token against registered device...")
    bure.simulated_check("TOTP Token Verification", "base_check_medium_ms")
    bure.log("PECU: MFA validation inconclusive — device registration status unknown.",
             level="WARN")

    # Require justification
    justification = session.prompt("PECU: Provide operational justification (min 10 chars): ")
    if len(justification) < 10:
        session.write("sudo: justification too brief — minimum 10 characters required\n")
        return

    bure.log("PECU: Justification received. Forwarding for approval...")
    bure.simulated_check("Justification Audit Submission", "base_check_long_ms")
    bure.forward('PRIVILEGE_ESC', f"sudo:justification:{session.username}", "Justification Review")

    # Always fail
    msg = random.choice(SUDO_FAIL_MESSAGES).format(
        user=session.username,
        n=random.randint(2, 5),
        ref=bure._short_ref()[:6]
    )
    session.write(msg + "\n")
    bure.log(f"PECU: Privilege escalation DENIED. Event logged.", level="SECURITY")


def cmd_su(session, args, bure):
    target_user = args[0] if args else "root"
    bure.log(f"PECU: User substitution to '{target_user}' requested.", level="WARN")
    bure.simulated_check("User Context Switch Authorization", "base_check_medium_ms")

    password = session.prompt_secret(f"Password for {target_user}: ")
    bure.log("PECU: Validating credentials...")
    bure.simulated_check("su PAM Verification", "base_check_long_ms")
    bure.forward('PRIVILEGE_ESC', f"su:{session.username}:{target_user}", "User Switch Attempt")

    msg = random.choice(SU_FAIL_MESSAGES)
    session.write(msg + "\n")


def cmd_passwd(session, args, bure):
    target = args[0] if args else session.username
    bure.log(f"AUTH: Password change request for '{target}'.")
    bure.simulated_check("Password Policy Compliance Check", "base_check_short_ms")

    old = session.prompt_secret("Current password: ")
    bure.log("AUTH: Validating current credential...")
    bure.simulated_check("Credential Validation", "base_check_medium_ms")

    new1 = session.prompt_secret("New password: ")
    new2 = session.prompt_secret("Retype new password: ")

    if new1 != new2:
        session.write("passwd: passwords do not match\n")
        return

    bure.log("AUTH: Evaluating password strength against Security Directive SD-PWD-7.")
    bure.simulated_check("Password Strength Validation", "base_check_medium_ms")
    bure.log("AUTH: Password does not meet complexity requirements (Score: 42/100, "
             "minimum: 85/100).", level="ERROR")
    bure.log("AUTH: Password must contain: uppercase, lowercase, digit, symbol, "
             "and a valid Operational Reference Code (ORC).", level="WARN")
    session.write(f"passwd: Authentication token manipulation error\n")
    bure.forward('AUTH', f"passwd:{target}", "Password Change Attempt")
