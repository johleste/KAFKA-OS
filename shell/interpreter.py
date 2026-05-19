import os
import shlex

from shell.bureaucracy.engine import BureaucracyEngine
from shell.commands import filesystem, system, auth, network, execution, editors, hardware, packages, attacker_tools


class Session:
    """Holds per-connection state."""

    def __init__(self, username, profile, vfs, config, write_func, prompt_func,
                 prompt_secret_func, remote_ip="unknown"):
        self.username = username
        self.profile = profile
        self.vfs = vfs
        self.config = config
        self._write = write_func
        self._prompt = prompt_func
        self._prompt_secret = prompt_secret_func
        self.remote_ip = remote_ip

        # Set home dir from profile
        users = profile.get("users", [])
        user = next((u for u in users if u["username"] == username), None)
        self.home = user["home"] if user else f"/home/{username}"
        self.cwd = self.home
        self.history = []
        self._nested_host = None

        # Package/service state — persists within the session
        self.installed_packages = {}   # name -> {version, bin_path}
        self.services = {}             # name -> "active"|"inactive"|"enabled"
        self.downloaded_tools = {}     # filename -> registry entry

    def write(self, text, end=""):
        self._write(text)

    def prompt(self, text=""):
        return self._prompt(text)

    def prompt_secret(self, text=""):
        return self._prompt_secret(text)

    def _build_prompt(self):
        identity = self.profile.get("identity", {})
        hostname = identity.get("hostname", "host")
        if self._nested_host:
            hostname = self._nested_host
        cwd = self.cwd
        if cwd.startswith(self.home):
            cwd = "~" + cwd[len(self.home):]
        return f"{self.username}@{hostname}:{cwd}$ "


# ---------------------------------------------------------------------------
# Command dispatch table
# ---------------------------------------------------------------------------

COMMANDS = {
    # Filesystem
    "ls":       filesystem.cmd_ls,
    "ll":       lambda s, a, b: filesystem.cmd_ls(s, ["-la"] + a, b),
    "la":       lambda s, a, b: filesystem.cmd_ls(s, ["-a"] + a, b),
    "cd":       filesystem.cmd_cd,
    "pwd":      filesystem.cmd_pwd,
    "cat":      filesystem.cmd_cat,
    "less":     filesystem.cmd_cat,
    "more":     filesystem.cmd_cat,
    "head":     filesystem.cmd_head,
    "tail":     filesystem.cmd_tail,
    "find":     filesystem.cmd_find,
    "grep":     filesystem.cmd_grep,
    "mkdir":    filesystem.cmd_mkdir,
    "rm":       filesystem.cmd_rm,
    "rmdir":    filesystem.cmd_rm,
    "cp":       filesystem.cmd_cp,
    "mv":       filesystem.cmd_mv,
    "chmod":    filesystem.cmd_chmod,
    "chown":    filesystem.cmd_chown,
    "touch":    lambda s, a, b: filesystem.cmd_chmod(s, ["644"] + a, b),
    # System
    "uname":    system.cmd_uname,
    "uptime":   system.cmd_uptime,
    "df":       system.cmd_df,
    "free":     system.cmd_free,
    "ps":       system.cmd_ps,
    "top":      system.cmd_top,
    "htop":     system.cmd_top,
    "who":      system.cmd_who,
    "w":        system.cmd_w,
    "id":       system.cmd_id,
    "whoami":   system.cmd_whoami,
    "hostname": system.cmd_hostname,
    "env":      system.cmd_env,
    "printenv": system.cmd_env,
    "date":     system.cmd_date,
    "history":  system.cmd_history,
    "clear":    system.cmd_clear,
    "echo":     system.cmd_echo,
    "exit":     system.cmd_exit,
    "logout":   system.cmd_exit,
    # Auth
    "sudo":     auth.cmd_sudo,
    "su":       auth.cmd_su,
    "passwd":   auth.cmd_passwd,
    # Network
    "ping":     network.cmd_ping,
    "ssh":      network.cmd_ssh,
    "scp":      network.cmd_scp,
    "curl":     network.cmd_curl,
    "wget":     network.cmd_wget,
    "netstat":  network.cmd_netstat,
    "ss":       network.cmd_ss,
    "ip":       network.cmd_ip,
    "ifconfig": network.cmd_ifconfig,
    # Execution
    "python":   execution.cmd_python,
    "python3":  execution.cmd_python3,
    "bash":     execution.cmd_bash,
    "sh":       execution.cmd_sh,
    "gcc":      execution.cmd_gcc,
    "make":     execution.cmd_make,
    "apt":      execution.cmd_apt,
    "apt-get":  execution.cmd_apt,
    "crontab":  execution.cmd_crontab,
    # Editors
    "vim":      editors.cmd_vim,
    "vi":       editors.cmd_vi,
    "nano":     editors.cmd_nano,
    # Hardware
    "lscpu":       hardware.cmd_lscpu,
    "lshw":        hardware.cmd_lshw,
    "lspci":       hardware.cmd_lspci,
    "lsusb":       hardware.cmd_lsusb,
    "lsblk":       hardware.cmd_lsblk,
    "fdisk":       hardware.cmd_fdisk,
    "dmidecode":   hardware.cmd_dmidecode,
    "smartctl":    hardware.cmd_smartctl,
    "hdparm":      hardware.cmd_hdparm,
    "mount":       hardware.cmd_mount,
    "du":          hardware.cmd_du,
    "dmesg":       hardware.cmd_dmesg,
    # Packages
    "pip":         packages.cmd_pip,
    "pip3":        packages.cmd_pip,
    "npm":         packages.cmd_npm,
    "yarn":        packages.cmd_yarn,
    "cargo":       packages.cmd_cargo,
    "gem":         packages.cmd_gem,
    "snap":        packages.cmd_snap,
    "dpkg":        packages.cmd_dpkg,
    "which":       packages.cmd_which,
    "whereis":     packages.cmd_whereis,
    "systemctl":   packages.cmd_systemctl,
    "service":     packages.cmd_service,
    "man":         packages.cmd_man,
}


# ---------------------------------------------------------------------------
# Boot banner
# ---------------------------------------------------------------------------

def boot_banner(session, bure):
    identity = session.profile.get("identity", {})
    hostname = identity.get("hostname", "host")
    os_name = identity.get("os_name", "Linux")
    os_ver = identity.get("os_version", "")
    kernel = identity.get("kernel", "")

    session.write(
        f"\r\nWelcome to {os_name} {os_ver} ({identity.get('os_codename','')})\r\n"
        f" * Documentation:  https://help.ubuntu.com\r\n"
        f" * Management:     https://landscape.canonical.com\r\n\r\n"
    )

    import random
    updates = random.randint(0, 40)
    security = random.randint(0, 10)
    if updates:
        session.write(f"{updates} updates can be applied immediately.\r\n")
        if security:
            session.write(f"{security} of these updates are standard security updates.\r\n")
        session.write(f"To see these additional updates run: apt list --upgradable\r\n\r\n")

    import datetime
    session.write(
        f"Last login: {datetime.datetime.now().strftime('%a %b %d %H:%M:%S %Y')} "
        f"from {session.remote_ip}\r\n\r\n"
    )


# ---------------------------------------------------------------------------
# Main shell loop
# ---------------------------------------------------------------------------

def run_shell(session: Session, bure: BureaucracyEngine):
    boot_banner(session, bure)

    while True:
        try:
            prompt = session._build_prompt()
            raw = session.prompt(prompt)
        except (EOFError, SystemExit):
            break
        except KeyboardInterrupt:
            session.write("^C\n")
            continue

        raw = raw.strip()
        if not raw:
            continue

        session.history.append(raw)

        # Handle variable assignment (silently accept)
        if "=" in raw and not raw.startswith(tuple(COMMANDS.keys())):
            continue

        # Pipe/redirect — pretend to process, apply friction
        has_pipe = "|" in raw
        has_redirect = ">" in raw or "<" in raw
        if has_pipe or has_redirect:
            # Strip pipe/redirect, run only the first command
            cmd_part = raw.split("|")[0].split(">")[0].split("<")[0].strip()
            raw = cmd_part

        # Parse
        try:
            parts = shlex.split(raw)
        except ValueError:
            session.write(f"bash: syntax error\n")
            continue

        if not parts:
            continue

        cmd_name = parts[0]
        args = parts[1:]

        # Log command for intelligence
        bure.log(f"CMD: {raw[:80]}", level="DEBUG")

        handler = COMMANDS.get(cmd_name)
        if handler:
            try:
                handler(session, args, bure)
            except SystemExit:
                break
            except Exception as e:
                session.write(f"bash: {cmd_name}: unexpected error\n")
                bure.log(f"Internal error in '{cmd_name}': {e}", level="DEBUG")
        elif attacker_tools.handle_execution(session, bure, cmd_name, args):
            pass  # tool handled
        else:
            # Unknown command — bureaucratic rejection
            bure.circular_rejection(session, cmd_name)
