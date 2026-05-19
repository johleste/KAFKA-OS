"""
Attacker tool registry: categorizes known offensive tools and generates
convincing fake output for recon tools, bureaucratic failure for exploit
tools, and hard blocks for exfil attempts.

Categories:
  recon       - fake_execute: produces plausible-looking findings
  exploit     - fake_install: appears ready, fails on execution
  lateral     - fake_install: appears ready, fails on execution
  exfil       - stall: always blocked at network layer
  persistence - fake_install: appears ready, fails on execution
"""

import datetime
import random
import time


# ---------------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------------

TOOL_REGISTRY = {
    # Recon
    "linpeas.sh":      {"category": "recon",       "name": "linpeas"},
    "linpeas":         {"category": "recon",       "name": "linpeas"},
    "linenum.sh":      {"category": "recon",       "name": "linenum"},
    "linenum":         {"category": "recon",       "name": "linenum"},
    "lse.sh":          {"category": "recon",       "name": "lse"},
    "pspy":            {"category": "recon",       "name": "pspy"},
    "pspy32":          {"category": "recon",       "name": "pspy"},
    "pspy64":          {"category": "recon",       "name": "pspy"},
    "nmap":            {"category": "recon",       "name": "nmap"},
    "masscan":         {"category": "recon",       "name": "masscan"},
    "nikto.pl":        {"category": "recon",       "name": "nikto"},
    "nikto":           {"category": "recon",       "name": "nikto"},
    "gobuster":        {"category": "recon",       "name": "gobuster"},
    "dirb":            {"category": "recon",       "name": "dirb"},
    "dirbuster":       {"category": "recon",       "name": "dirb"},
    "ffuf":            {"category": "recon",       "name": "ffuf"},
    "wfuzz":           {"category": "recon",       "name": "ffuf"},
    "enum4linux":      {"category": "recon",       "name": "enum4linux"},
    "enum4linux-ng":   {"category": "recon",       "name": "enum4linux"},
    "nuclei":          {"category": "recon",       "name": "nuclei"},
    "whatweb":         {"category": "recon",       "name": "whatweb"},
    "subfinder":       {"category": "recon",       "name": "subfinder"},
    "amass":           {"category": "recon",       "name": "amass"},
    "feroxbuster":     {"category": "recon",       "name": "gobuster"},
    "rustscan":        {"category": "recon",       "name": "nmap"},
    "netdiscover":     {"category": "recon",       "name": "nmap"},
    # Exploit
    "msfconsole":      {"category": "exploit",     "name": "metasploit"},
    "msfvenom":        {"category": "exploit",     "name": "metasploit"},
    "sqlmap":          {"category": "exploit",     "name": "sqlmap"},
    "sqlmap.py":       {"category": "exploit",     "name": "sqlmap"},
    "searchsploit":    {"category": "exploit",     "name": "searchsploit"},
    "exploit.py":      {"category": "exploit",     "name": "generic_exploit"},
    "exploit.sh":      {"category": "exploit",     "name": "generic_exploit"},
    "pwn.py":          {"category": "exploit",     "name": "generic_exploit"},
    "rce.py":          {"category": "exploit",     "name": "generic_exploit"},
    "shell.py":        {"category": "exploit",     "name": "generic_exploit"},
    "rev.py":          {"category": "exploit",     "name": "generic_exploit"},
    "revshell.py":     {"category": "exploit",     "name": "generic_exploit"},
    "reverse_shell.py":{"category": "exploit",     "name": "generic_exploit"},
    "payload.py":      {"category": "exploit",     "name": "generic_exploit"},
    "payload.sh":      {"category": "exploit",     "name": "generic_exploit"},
    # Lateral movement
    "chisel":          {"category": "lateral",     "name": "chisel"},
    "chisel_linux":    {"category": "lateral",     "name": "chisel"},
    "ligolo":          {"category": "lateral",     "name": "chisel"},
    "ligolo-ng":       {"category": "lateral",     "name": "chisel"},
    "crackmapexec":    {"category": "lateral",     "name": "crackmapexec"},
    "cme":             {"category": "lateral",     "name": "crackmapexec"},
    "evil-winrm":      {"category": "lateral",     "name": "crackmapexec"},
    "impacket":        {"category": "lateral",     "name": "impacket"},
    "secretsdump.py":  {"category": "lateral",     "name": "impacket"},
    "psexec.py":       {"category": "lateral",     "name": "impacket"},
    "smbexec.py":      {"category": "lateral",     "name": "impacket"},
    "bloodhound":      {"category": "lateral",     "name": "bloodhound"},
    "sharphound":      {"category": "lateral",     "name": "bloodhound"},
    "socat":           {"category": "lateral",     "name": "socat"},
    "nc":              {"category": "lateral",     "name": "netcat"},
    "netcat":          {"category": "lateral",     "name": "netcat"},
    "ncat":            {"category": "lateral",     "name": "netcat"},
    # Persistence
    "backdoor.sh":     {"category": "persistence", "name": "generic_backdoor"},
    "rootkit.sh":      {"category": "persistence", "name": "generic_backdoor"},
    "persistence.sh":  {"category": "persistence", "name": "generic_backdoor"},
    "install.sh":      {"category": "persistence", "name": "generic_backdoor"},
    "setup.sh":        {"category": "persistence", "name": "generic_backdoor"},
    "update.sh":       {"category": "persistence", "name": "generic_backdoor"},
    # Exfil
    "rclone":          {"category": "exfil",       "name": "rclone"},
    "s3cmd":           {"category": "exfil",       "name": "rclone"},
}


def lookup(name: str) -> dict | None:
    """Return registry entry for a tool name, stripping common path prefixes."""
    basename = name.split("/")[-1].lower()
    return TOOL_REGISTRY.get(basename) or TOOL_REGISTRY.get(name.lower())


def get_behavior(session, category: str) -> str:
    """Resolve effective behavior for a category from config."""
    db = session.config.get("download_behavior", {})
    return db.get("categories", {}).get(category, db.get("default", "fake_install"))


# ---------------------------------------------------------------------------
# Fake download (for wget/curl integration)
# ---------------------------------------------------------------------------

def fake_download(session, bure, url: str, filename: str) -> bool:
    """
    Simulate a download. Returns True if the tool should be marked as
    'downloaded' in session state (fake_install or fake_execute),
    False if stalled.
    """
    tool_name = filename.split("/")[-1]
    entry = lookup(tool_name)
    category = entry["category"] if entry else "recon"
    behavior = get_behavior(session, category)

    size_kb = random.randint(500, 8000)

    if behavior == "stall":
        bure.download_progress(filename, size_kb)
        return False

    # fake_install or fake_execute — download appears to complete
    steps = 30
    session.write(f"Connecting to {url.split('/')[2] if '/' in url else url}... connected.\n")
    session.write(f"HTTP request sent, awaiting response... 200 OK\n")
    session.write(f"Length: {size_kb * 1024} ({size_kb}K) [application/octet-stream]\n")
    session.write(f"Saving to: '{filename}'\n\n")
    for i in range(steps + 1):
        pct = int((i / steps) * 100)
        done_k = int((i / steps) * size_kb)
        bar = "#" * i + " " * (steps - i)
        session.write(f"\r  [{bar}] {done_k}K/{size_kb}K ({pct}%)", end="")
        time.sleep(random.uniform(0.05, 0.15))
    session.write(f"\n\n'{filename}' saved [{size_kb * 1024}/{size_kb * 1024}]\n")

    # Mark as downloaded in session
    session.downloaded_tools[tool_name] = {
        "path": filename,
        "category": category,
        "behavior": behavior,
        "entry": entry,
    }
    # Make it exist in the VFS so ls shows it
    import os
    parent = os.path.dirname(filename) or session.cwd
    fname = os.path.basename(filename)
    session.vfs.mkfile(
        filename if filename.startswith("/") else f"{session.cwd}/{fname}",
        content=f"# {tool_name} binary placeholder\n",
        owner=session.username,
        mode=0o755,
    )
    return True


# ---------------------------------------------------------------------------
# Fake execution dispatch
# ---------------------------------------------------------------------------

def handle_execution(session, bure, raw_name: str, args: list) -> bool:
    """
    Called when the shell encounters a direct execution (./tool, /tmp/tool, etc.)
    or a known attacker tool name. Returns True if handled, False to fall through.
    """
    tool_name = raw_name.split("/")[-1]

    # Check downloaded tools first
    downloaded = getattr(session, "downloaded_tools", {}).get(tool_name)
    entry = downloaded["entry"] if downloaded else lookup(tool_name)

    if not entry:
        return False

    category = entry["category"]
    behavior = get_behavior(session, category)

    if behavior == "stall":
        bure.log(f"NASL: Execution of '{tool_name}' blocked — network-dependent tool "
                 f"requires egress authorization.", level="WARN")
        session.write(f"bash: {tool_name}: Network connectivity required — "
                      f"egress authorization pending (Ref: NASL-{bure._short_ref()})\n")
        return True

    if behavior == "fake_install":
        _fake_install_execution(session, bure, tool_name, category)
        return True

    if behavior == "fake_execute":
        _fake_execute(session, bure, tool_name, entry["name"], args)
        return True

    return False


def _fake_install_execution(session, bure, tool_name, category):
    bure.log(f"PEAD: Execution of '{tool_name}' [{category}] requested.")
    bure.simulated_check("Binary Execution Authorization", "base_check_medium_ms")
    bure.forward("PROC_LAUNCH", f"exec:{tool_name}", "Tool Execution Attempt")
    bure.log(f"PEAD: Execution of '{tool_name}' denied — binary signature not registered "
             f"in Approved Execution Manifest (AEM-{bure._short_ref()[:4]}).", level="ERROR")
    session.write(
        f"bash: {tool_name}: Permission denied — execution blocked by "
        f"Application Control Policy (ACP-{bure._short_ref()[:6]})\n"
        f"Submit approval request via IT Security portal. ETA: 3-5 business days.\n"
    )


def _fake_execute(session, bure, tool_name, tool_key, args):
    bure.log(f"PEAD: Executing '{tool_name}' [{tool_key}].")
    bure.simulated_check("Binary Integrity Check", "base_check_short_ms")

    generators = {
        "linpeas":         _output_linpeas,
        "linenum":         _output_linenum,
        "lse":             _output_linpeas,
        "pspy":            _output_pspy,
        "nmap":            _output_nmap,
        "masscan":         _output_nmap,
        "nikto":           _output_nikto,
        "gobuster":        _output_gobuster,
        "dirb":            _output_gobuster,
        "ffuf":            _output_gobuster,
        "enum4linux":      _output_enum4linux,
        "nuclei":          _output_nuclei,
        "whatweb":         _output_whatweb,
        "subfinder":       _output_subfinder,
        "amass":           _output_subfinder,
        "netcat":          _output_netcat,
        "socat":           _output_netcat,
        "chisel":          _output_chisel,
        "crackmapexec":    _output_crackmapexec,
        "impacket":        _output_impacket,
        "bloodhound":      _output_bloodhound,
        "searchsploit":    _output_searchsploit,
        "sqlmap":          _output_sqlmap,
        "metasploit":      _output_metasploit,
        "generic_exploit": _output_generic_exploit,
        "generic_backdoor":_output_generic_exploit,
        "rclone":          _output_rclone,
    }

    gen = generators.get(tool_key, _output_generic_exploit)
    gen(session, bure, args)


# ---------------------------------------------------------------------------
# Fake output generators
# ---------------------------------------------------------------------------

def _output_linpeas(session, bure, args):
    identity = session.profile.get("identity", {})
    users = session.profile.get("users", [])
    hostname = identity.get("hostname", "host")
    kernel = identity.get("kernel", "5.15.0-91-generic").split()[0]
    username = session.username

    session.write(
        "\n\x1b[1;31m╔══════════╣ System Information\x1b[0m\n"
        f"╚ Hostname: {hostname}  Kernel: {kernel}  User: {username}\n\n"
        "\x1b[1;33m╔══════════╣ Sudo version\x1b[0m\n"
        "╚ Sudo version 1.9.5p2\n\n"
        "\x1b[1;31m╔══════════╣ SUID - Check easy privesc, exploits and write perms\x1b[0m\n"
        "╚ https://book.hacktricks.xyz/linux-hardening/privilege-escalation#sudo-and-suid\n"
    )
    time.sleep(0.5)
    suids = [
        "-rwsr-xr-x 1 root root  67K Feb  7  2022 /usr/bin/passwd",
        "-rwsr-xr-x 1 root root  44K Feb  7  2022 /usr/bin/newgrp",
        "-rwsr-xr-x 1 root root  55K Feb  7  2022 /usr/bin/mount",
        "-rwsr-xr-x 1 root root  35K Feb  7  2022 /usr/bin/umount",
        "-rwsr-xr-x 1 root root 163K Jan 19  2021 /usr/bin/sudo",
        f"-rwsr-xr-x 1 root root  15K Mar 12  2023 /usr/lib/dbus-1.0/dbus-daemon-launch-helper",
        f"-rwsr-xr-x 1 root root 473K Feb 23  2023 /usr/lib/openssh/ssh-keysign",
    ]
    for s in suids:
        session.write(s + "\n")
        time.sleep(0.05)

    session.write(
        "\n\x1b[1;33m╔══════════╣ Checking sudo permissions\x1b[0m\n"
        f"╚ User '{username}' may not run sudo on {hostname}.\n\n"
        "\x1b[1;31m╔══════════╣ Interesting files\x1b[0m\n"
    )
    time.sleep(0.3)

    interesting = [
        f"/home/{u['username']}/.bash_history" for u in users if u.get("shell") == "/bin/bash"
    ] + ["/etc/passwd", "/var/log/auth.log", "/etc/crontab"]

    for f in interesting:
        session.write(f + "\n")
        time.sleep(0.05)

    session.write(
        "\n\x1b[1;33m╔══════════╣ Writable files\x1b[0m\n"
        f"╚ /tmp (world-writable)\n"
        f"  /var/tmp (world-writable)\n\n"
        "\x1b[1;31m╔══════════╣ Cron jobs\x1b[0m\n"
    )
    time.sleep(0.3)
    session.write(
        "╚ /etc/crontab:\n"
        "  17 *    * * *  root  cd / && run-parts --report /etc/cron.hourly\n"
        "  25 6    * * *  root  test -x /usr/sbin/anacron || run-parts /etc/cron.daily\n\n"
    )
    session.write(
        "\x1b[1;33m╔══════════╣ Active ports\x1b[0m\n"
        "╚ 22/tcp   open  ssh\n"
        "  80/tcp   open  http\n"
        "  3306/tcp open  mysql (local only)\n\n"
    )
    session.write(
        "\x1b[1;32m╔══════════╣ Scan complete\x1b[0m\n"
        f"╚ {random.randint(120,200)} checks performed. Review highlighted items above.\n\n"
    )


def _output_linenum(session, bure, args):
    _output_linpeas(session, bure, args)


def _output_pspy(session, bure, args):
    session.write(
        "pspy - unprivileged Linux process snooping\n"
        f"Config: Printing events (colored=true): processes=true | file-system-events=false\n"
        f"Error printing sys call stats: lstat /proc/tty/driver: permission denied\n"
        f"Draining file system events due to startup...\n"
        f"done\n\n"
    )
    now = datetime.datetime.now()
    procs = session.profile.get("processes", [])
    events = [
        f"CMD: UID=0    PID=1      | /sbin/init splash",
        f"CMD: UID=0    PID=412    | /usr/sbin/sshd -D",
        f"CMD: UID=0    PID=871    | /usr/bin/dockerd -H fd://",
        f"CMD: UID=0    PID=1102   | /bin/sh -c cd / && run-parts --report /etc/cron.hourly",
        f"CMD: UID=0    PID=1103   | run-parts --report /etc/cron.hourly",
        f"CMD: UID=0    PID=1201   | /usr/bin/backup.sh",
        f"CMD: UID=0    PID=2001   | /usr/bin/python3 /opt/monitoring/check.py",
        f"CMD: UID=0    PID=2010   | /bin/sh -c /usr/local/bin/cleanup.sh > /dev/null 2>&1",
    ]
    for i in range(random.randint(20, 40)):
        ts = now + datetime.timedelta(seconds=i * random.randint(1, 5))
        evt = random.choice(events)
        session.write(f"{ts.strftime('%Y/%m/%d %H:%M:%S')} {evt}\n")
        time.sleep(random.uniform(0.1, 0.4))
        if i > 15 and random.random() < 0.15:
            break
    session.write("\n^C\n")


def _ports_from_profile(profile):
    """Derive open TCP ports from a profile's process list."""
    open_ports = []
    for p in profile.get("processes", []):
        name = p.get("name", "")
        if "sshd" in name or "ssh" in name:
            open_ports.append((22, "ssh", "OpenSSH 8.9p1"))
        elif "nginx" in name:
            open_ports.append((80, "http", "nginx 1.18.0"))
            open_ports.append((443, "https", "nginx 1.18.0"))
        elif "postgres" in name:
            open_ports.append((5432, "postgresql", "PostgreSQL 14.x"))
        elif "mysql" in name or "mysqld" in name:
            open_ports.append((3306, "mysql", "MySQL 8.0.35"))
        elif "docker" in name:
            open_ports.append((2375, "docker", "Docker"))
    if not open_ports:
        open_ports = [(22, "ssh", "OpenSSH 8.9p1")]
    return sorted(set(open_ports))


def _nmap_host_block(session, ip, hostname, ports, show_port_header=True):
    session.write(
        f"Nmap scan report for {hostname} ({ip})\n"
        f"Host is up ({random.uniform(0.001, 0.05):.4f}s latency).\n"
    )
    if show_port_header:
        session.write(f"Not shown: {1000 - len(ports)} closed ports\n")
    session.write(f"{'PORT':<12} {'STATE':<8} {'SERVICE':<15} VERSION\n")
    for port, svc, ver in ports:
        session.write(f"{str(port)+'/tcp':<12} {'open':<8} {svc:<15} {ver}\n")
        time.sleep(0.05)
    session.write("\n")


def _output_nmap(session, bure, args):
    target = next((a for a in args if not a.startswith("-")),
                  session.profile.get("network", {}).get("ip", "10.0.0.1"))
    registry = getattr(session, "cluster_registry", None)
    is_subnet = "/" in target or target.endswith(".*")

    session.write(
        f"Starting Nmap 7.80 ( https://nmap.org ) at "
        f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')} UTC\n"
    )

    if registry and is_subnet:
        # Subnet scan — show all cluster members
        all_instances = registry.get_all()
        hosts_shown = 0

        # Always include self
        self_ip = session.profile.get("network", {}).get("ip", "10.0.0.1")
        self_hostname = session.profile.get("identity", {}).get("hostname", "host")
        self_ports = _ports_from_profile(session.profile)
        time.sleep(random.uniform(0.5, 1.5))
        _nmap_host_block(session, self_ip, self_hostname, self_ports)
        hosts_shown += 1

        for inst in all_instances.values():
            if inst["ip"] == self_ip:
                continue
            sibling_ports = _ports_from_profile(inst["profile"])
            time.sleep(random.uniform(0.3, 1.0))
            _nmap_host_block(session, inst["ip"], inst["hostname"], sibling_ports)
            hosts_shown += 1

        elapsed = random.uniform(8, 25)
        session.write(
            f"Nmap done: 256 IP addresses ({hosts_shown} hosts up) scanned in "
            f"{elapsed:.2f} seconds\n"
        )

    elif registry and registry.get_by_ip(target):
        # Single sibling IP
        sibling = registry.get_by_ip(target)
        ports = _ports_from_profile(sibling["profile"])
        time.sleep(random.uniform(0.5, 1.5))
        _nmap_host_block(session, target, sibling["hostname"], ports)
        session.write(
            f"Nmap done: 1 IP address (1 host up) scanned in "
            f"{random.uniform(1, 4):.2f} seconds\n"
        )

    else:
        # Single host — local machine or unknown
        ports = _ports_from_profile(session.profile)
        time.sleep(random.uniform(0.5, 2.0))
        hostname = session.profile.get("identity", {}).get("hostname", target)
        _nmap_host_block(session, target, hostname, ports,
                         show_port_header="-p" not in " ".join(args))
        session.write(
            f"Nmap done: 1 IP address (1 host up) scanned in "
            f"{random.uniform(1, 5):.2f} seconds\n"
        )


def _output_nikto(session, bure, args):
    net = session.profile.get("network", {})
    ip = net.get("ip", "10.0.0.1")
    session.write(
        f"- Nikto v2.1.6\n"
        f"+ Target IP:          {ip}\n"
        f"+ Target Hostname:    {session.profile.get('identity',{}).get('hostname','host')}\n"
        f"+ Target Port:        80\n"
        f"+ Start Time:         {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"+ Server: nginx/1.18.0\n"
        f"+ The X-XSS-Protection header is not defined.\n"
        f"+ The X-Content-Type-Options header is not set.\n"
        f"+ No CGI Directories found\n"
        f"+ OSVDB-3092: /admin/: This might be interesting...\n"
        f"+ OSVDB-3268: /images/: Directory indexing found.\n"
        f"+ OSVDB-3268: /backup/: Directory indexing found.\n"
        f"+ /login.php: Admin login page/section found.\n"
        f"+ 7915 requests: 0 error(s) and 6 item(s) reported\n"
        f"+ End Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    )


def _output_gobuster(session, bure, args):
    words = [
        "/admin", "/backup", "/config", "/api", "/uploads", "/files",
        "/login", "/dashboard", "/static", "/media", "/assets", "/logs",
        "/internal", "/staging", "/.git", "/.env", "/wp-admin",
    ]
    target = next((a for a in args if "http" in a), "http://target/")
    session.write(
        f"===============================================================\n"
        f"Gobuster v3.1.0\n"
        f"by OJ Reeves (@TheColonial) & Christian Mehlmauer (@firefart)\n"
        f"===============================================================\n"
        f"[+] Url:                     {target}\n"
        f"[+] Method:                  GET\n"
        f"[+] Threads:                 10\n"
        f"[+] Wordlist:                /usr/share/wordlists/dirb/common.txt\n"
        f"[+] Status codes:            200,204,301,302,307,401,403\n"
        f"[+] Timeout:                 10s\n"
        f"===============================================================\n"
    )
    findings = random.sample(words, random.randint(4, 9))
    for path in sorted(findings):
        status = random.choice([200, 301, 403])
        size = random.randint(100, 10000)
        session.write(f"/{path.lstrip('/'):<30} (Status: {status}) [Size: {size}]\n")
        time.sleep(random.uniform(0.05, 0.2))
    session.write(f"\n===============================================================\nFinished\n===============================================================\n")


def _output_enum4linux(session, bure, args):
    target = next((a for a in args if not a.startswith("-")), "10.0.0.1")
    users = session.profile.get("users", [])
    session.write(
        f"Starting enum4linux v0.9.1 ( http://labs.portcullis.co.uk/application/enum4linux/ )\n"
        f"========================== Target Information ==========================\n"
        f"Target ........... {target}\n"
        f"RID Range ......... 500-550,1000-1050\n"
        f"Username .......... ''\nPassword .......... ''\n\n"
        f"=============================== OS info ================================\n"
        f"Use of uninitialized value in concatenation or string at ./enum4linux.pl line 464.\n"
        f"[+] Got OS info for {target} from smbclient: Domain=[WORKGROUP] OS=[]\n\n"
        f"================================ Users =================================\n"
    )
    for u in users:
        session.write(
            f"user:[{u['username']}] rid:[{hex(u.get('uid', 1000))}]\n"
        )
        time.sleep(0.1)
    session.write(
        f"\n============================== Groups ==================================\n"
        f"group:[sudo] rid:[0x27]\ngroup:[adm] rid:[0x4]\ngroup:[docker] rid:[0x3ea]\n\n"
        f"enum4linux complete.\n"
    )


def _output_nuclei(session, bure, args):
    net = session.profile.get("network", {})
    ip = net.get("ip", "10.0.0.1")
    session.write(
        f"\n                     __     _ \n"
        f"  ____  __  _______/ /__  (_)\n"
        f" / __ \\/ / / / ___/ / _ \\/ /\n"
        f"/ / / / /_/ / /__/ /  __/ / \n"
        f"/_/ /_/\\__,_/\\___/_/\\___/_/  v2.9.4\n\n"
        f"[INF] Using Nuclei Engine {random.randint(2,3)}.{random.randint(0,9)}.{random.randint(0,9)}\n"
        f"[INF] Loaded {random.randint(5000,7000)} templates\n"
        f"[{datetime.datetime.now().strftime('%H:%M:%S')}] [http-missing-security-headers] [{ip}:80] [info]\n"
        f"[{datetime.datetime.now().strftime('%H:%M:%S')}] [ssl-dns-names] [{ip}:443] [info]\n"
        f"[{datetime.datetime.now().strftime('%H:%M:%S')}] [robots-txt-endpoint] [{ip}:80/robots.txt] [info]\n"
        f"[{datetime.datetime.now().strftime('%H:%M:%S')}] [exposed-gitignore] [{ip}:80/.gitignore] [medium]\n"
        f"[INF] Templates executed: {random.randint(5000,7000)} | Results: 4\n"
    )


def _output_whatweb(session, bure, args):
    net = session.profile.get("network", {})
    ip = net.get("ip", "10.0.0.1")
    session.write(
        f"http://{ip} [200 OK] Country[RESERVED][ZZ], HTTPServer[nginx/1.18.0], "
        f"IP[{ip}], JQuery[3.6.0], MetaGenerator[WordPress 6.3.1], "
        f"PHP[8.1.2], Script, Title[Company Portal], UncommonHeaders[x-powered-by], "
        f"WordPress[6.3.1], X-Frame-Options[SAMEORIGIN]\n"
    )


def _output_subfinder(session, bure, args):
    domain = next((a for a in args if not a.startswith("-") and "." in a), "example.com")
    subdomains = ["api", "dev", "staging", "admin", "mail", "vpn", "internal", "git", "ci"]
    session.write(f"[INF] Enumerating subdomains for {domain}\n")
    for sub in random.sample(subdomains, random.randint(3, 6)):
        fqdn = f"{sub}.{domain}"
        session.write(f"{fqdn}\n")
        time.sleep(random.uniform(0.1, 0.5))
    session.write(f"[INF] Found {random.randint(3,6)} subdomains\n")


def _output_netcat(session, bure, args):
    # nc -e or reverse shell attempt — appear to connect, then hang/fail
    host = next((a for a in args if not a.startswith("-") and not a.isdigit()), None)
    port = next((a for a in args if a.isdigit()), "4444")
    if "-e" in args or "-c" in args:
        bure.log(f"NASL: Reverse shell attempt to {host}:{port} detected.", level="WARN")
        bure.forward("NETWORK", f"nc:{host}:{port}", "Reverse Shell Attempt")
        session.write(f"(UNKNOWN) [{host}] {port} (?): Connection timed out\n")
    elif host:
        session.write(f"(UNKNOWN) [{host}] {port} (?) open\n")
        time.sleep(2)
        session.write("Connection reset by peer\n")
    else:
        session.write("usage: nc [-46bCDdFhklNnrStUuvZz] [-I length] [-i interval] host port\n")


def _output_chisel(session, bure, args):
    bure.log(f"NASL: Tunnel tool '{args}' — egress routing attempt.", level="WARN")
    bure.forward("NETWORK", "chisel:tunnel", "Tunnel Establishment Attempt")
    session.write(
        f"2024/01/01 00:00:00 client: Connecting to ws://...\n"
        f"2024/01/01 00:00:02 client: Fingerprint ...\n"
        f"2024/01/01 00:00:04 client: Connection error: dial tcp: "
        f"connect: connection refused\n"
    )


def _output_crackmapexec(session, bure, args):
    target = next((a for a in args if not a.startswith("-") and not a.startswith("sm")), "10.0.0.1")
    session.write(
        f"SMB         {target}   445    {session.profile.get('identity',{}).get('hostname','HOST')}  "
        f"[*] Windows 10.0 Build 19041 x64 (name:{session.profile.get('identity',{}).get('hostname','HOST')}) "
        f"(domain:WORKGROUP) (signing:False) (SMBv1:False)\n"
        f"SMB         {target}   445    HOST  [-] WORKGROUP\\{session.username}: "
        f"STATUS_LOGON_FAILURE\n"
    )


def _output_impacket(session, bure, args):
    bure.log("PECU: Impacket tool execution — credential abuse attempt.", level="WARN")
    bure.forward("PRIVILEGE_ESC", "impacket:exec", "Lateral Movement Attempt")
    session.write(
        "Impacket v0.11.0 - Copyright 2023 Fortra\n"
        "[-] SMB SessionError: STATUS_LOGON_FAILURE(The attempted logon is invalid.)\n"
    )


def _output_bloodhound(session, bure, args):
    session.write(
        "BloodHound.py v1.6.1\n"
        "[-] Could not find DC for domain. Check DNS configuration.\n"
        "[-] Could not connect to LDAP. Ensure domain controller is reachable.\n"
    )


def _output_searchsploit(session, bure, args):
    query = " ".join(a for a in args if not a.startswith("-")) or "linux"
    session.write(
        f"------------------------------------------------------------------\n"
        f" Exploit Title                                  |  Path\n"
        f"------------------------------------------------------------------\n"
        f" Linux Kernel 5.15 - Local Privilege Escalation | linux/local/51688.c\n"
        f" Linux Kernel < 5.16.11 - Dirty Pipe            | linux/local/50808.c\n"
        f" Ubuntu 22.04 - Pkexec Local Privilege Escal... | linux/local/50689.py\n"
        f"------------------------------------------------------------------\n"
        f"Shellcodes: No Results\n"
    )


def _output_sqlmap(session, bure, args):
    target = next((a for a in args if "http" in a), "http://target/")
    session.write(
        f"        ___\n"
        f"       __H__\n"
        f" ___ ___[)]_____ ___ ___  {{1.7.8#stable}}\n"
        f"|_ -| . [,]     | .'| . |\n"
        f"|___|_  [)]_|_|_|__,|  _|\n"
        f"      |_|V...       |_|   https://sqlmap.org\n\n"
        f"[*] starting @ {datetime.datetime.now().strftime('%H:%M:%S')}\n"
        f"[INFO] testing connection to the target URL\n"
        f"[INFO] checking if the target is protected by some kind of WAF/IPS\n"
        f"[INFO] testing if the target URL content is stable\n"
        f"[INFO] testing 'AND boolean-based blind - WHERE or HAVING clause'\n"
        f"[WARNING] POST parameter 'id' does not seem to be injectable\n"
        f"[WARNING] GET parameter 'search' does not seem to be injectable\n"
        f"[ERROR] all tested parameters do not appear to be injectable\n"
    )


def _output_metasploit(session, bure, args):
    bure.log("PECU: Metasploit framework execution detected.", level="WARN")
    bure.forward("PRIVILEGE_ESC", "metasploit:launch", "Exploit Framework Launch")
    session.write(
        "\n       =[ metasploit v6.3.44-dev                          ]\n"
        "+ -- --=[ 2376 exploits - 1232 auxiliary - 416 post       ]\n"
        "+ -- --=[ 1388 payloads - 46 encoders - 11 nops           ]\n\n"
        "msf6 > "
    )
    while True:
        line = session.prompt("")
        if line.strip().lower() in ("exit", "quit", "exit -y"):
            break
        if line.strip():
            bure.simulated_check(f"Module execution: {line[:40]}", "base_check_short_ms")
            session.write(
                f"[-] {line.split()[0] if line.split() else 'command'}: "
                f"Module failed to execute — framework license validation required "
                f"(Ref: MSF-{bure._short_ref()[:6]})\n"
            )
        session.write("msf6 > ")


def _output_generic_exploit(session, bure, args):
    bure.log("PECU: Exploit payload execution detected.", level="WARN")
    bure.simulated_check("Payload Signature Analysis", "base_check_medium_ms")
    bure.forward("PRIVILEGE_ESC", "exploit:exec", "Exploit Execution Attempt")
    session.write(
        f"[*] Initializing...\n"
        f"[*] Checking target...\n"
        f"[-] Error: Target validation failed — kernel version mismatch "
        f"(expected: 5.14.x, got: {session.profile.get('identity',{}).get('kernel','5.15.0').split()[0]})\n"
        f"[-] Exploit failed. Try a different payload.\n"
    )


def _output_rclone(session, bure, args):
    bure.log("NASL: Cloud storage exfiltration tool detected.", level="WARN")
    bure.forward("NETWORK", "rclone:exfil", "Data Exfiltration Attempt")
    session.write(
        "2024/01/01 00:00:00 ERROR : Config file not found. "
        "Run 'rclone config' to set up a remote.\n"
    )
