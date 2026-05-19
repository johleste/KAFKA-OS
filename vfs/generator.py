import random
import time
import datetime
from vfs.tree import VFS

# ---------------------------------------------------------------------------
# Plausible file content generators
# ---------------------------------------------------------------------------

def _bash_history(username, extra_cmds=None):
    base = [
        "ls -la", "cd /var/log", "tail -f syslog", "ps aux | grep python",
        "df -h", "free -m", "uptime", "who", "last | head -20",
        "sudo systemctl status sshd", "ip addr", "netstat -tlnp",
        "cat /etc/passwd", "find /home -name '*.log'",
        "grep -r 'password' /etc/*.conf 2>/dev/null",
        "history", "exit",
    ]
    if extra_cmds:
        base = extra_cmds + base
    random.shuffle(base)
    return "\n".join(base[:random.randint(30, 60)]) + "\n"


def _ssh_authorized_keys(username):
    key_types = ["ssh-rsa", "ecdsa-sha2-nistp256", "ssh-ed25519"]
    keys = []
    for _ in range(random.randint(1, 3)):
        kt = random.choice(key_types)
        fake_key = "A" * random.randint(200, 400)
        comment = f"{username}@corp-laptop"
        keys.append(f"{kt} {fake_key} {comment}")
    return "\n".join(keys) + "\n"


def _etc_passwd(users):
    lines = [
        "root:x:0:0:root:/root:/bin/bash",
        "daemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin",
        "bin:x:2:2:bin:/bin:/usr/sbin/nologin",
        "sys:x:3:3:sys:/dev:/usr/sbin/nologin",
        "www-data:x:33:33:www-data:/var/www:/usr/sbin/nologin",
        "syslog:x:104:110::/home/syslog:/usr/sbin/nologin",
    ]
    for u in users:
        if u["username"] not in ("root", "www-data"):
            lines.append(
                f"{u['username']}:x:{u['uid']}:{u['gid']}:"
                f"{u['fullname']}:{u['home']}:{u['shell']}"
            )
    return "\n".join(lines) + "\n"


def _etc_shadow(users):
    lines = []
    for u in users:
        lines.append(f"{u['username']}:{u.get('password_hash', '!')}:19000:0:99999:7:::")
    return "\n".join(lines) + "\n"


def _crontab():
    return (
        "# /etc/crontab: system-wide crontab\n"
        "SHELL=/bin/sh\n"
        "PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin\n\n"
        "17 *    * * *   root    cd / && run-parts --report /etc/cron.hourly\n"
        "25 6    * * *   root    test -x /usr/sbin/anacron || ( cd / && run-parts --report /etc/cron.daily )\n"
        "47 6    * * 7   root    test -x /usr/sbin/anacron || ( cd / && run-parts --report /etc/cron.weekly )\n"
        "52 6    1 * *   root    test -x /usr/sbin/anacron || ( cd / && run-parts --report /etc/cron.monthly )\n"
    )


def _auth_log(hostname, users):
    lines = []
    now = datetime.datetime.now()
    ips = ["185.234.218.98", "45.33.32.156", "192.168.1.105", "10.10.14.5"]
    for i in range(random.randint(40, 80)):
        ts = now - datetime.timedelta(minutes=random.randint(1, 1440))
        ts_str = ts.strftime("%b %d %H:%M:%S")
        u = random.choice(users)
        ip = random.choice(ips)
        if random.random() < 0.3:
            lines.append(f"{ts_str} {hostname} sshd[{random.randint(1000,9999)}]: "
                         f"Failed password for {u['username']} from {ip} port {random.randint(1024,65535)} ssh2")
        else:
            lines.append(f"{ts_str} {hostname} sshd[{random.randint(1000,9999)}]: "
                         f"Accepted publickey for {u['username']} from {ip} port {random.randint(1024,65535)} ssh2")
    lines.sort()
    return "\n".join(lines) + "\n"


def _env_file(profile_name):
    if profile_name == "webserver":
        return (
            "APP_ENV=production\n"
            "DB_HOST=10.20.1.20\n"
            "DB_PORT=5432\n"
            "DB_NAME=webapp_prod\n"
            "DB_USER=webapp\n"
            "DB_PASS=Tr0ub4dor&3\n"
            "SECRET_KEY=django-insecure-placeholder-key-do-not-use\n"
            "REDIS_URL=redis://10.20.1.30:6379/0\n"
            "ALLOWED_HOSTS=web-prod-03.corp.internal\n"
        )
    return (
        "DEBUG=false\n"
        "DATABASE_URL=postgresql://user:hunter2@localhost:5432/appdb\n"
        "SECRET_KEY=supersecretkey1234567890\n"
        "API_KEY=sk-prod-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx\n"
        "REDIS_URL=redis://localhost:6379\n"
    )


def _aws_credentials():
    return (
        "[default]\n"
        f"aws_access_key_id = AKIA{''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=16))}\n"
        f"aws_secret_access_key = {''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789+/', k=40))}\n"
        "region = us-east-1\n"
    )


# ---------------------------------------------------------------------------
# Main generator
# ---------------------------------------------------------------------------

def build_vfs(profile: dict) -> VFS:
    vfs = VFS()
    identity = profile.get("identity", {})
    users = profile.get("users", [])
    hostname = identity.get("hostname", "localhost")
    profile_name = identity.get("hostname", "")

    # Standard Linux directory skeleton
    for d in ["/bin", "/sbin", "/usr/bin", "/usr/sbin", "/usr/local/bin",
              "/etc", "/etc/ssh", "/etc/apt", "/etc/cron.d",
              "/var", "/var/log", "/var/tmp",
              "/tmp", "/opt", "/proc", "/sys", "/dev", "/run"]:
        vfs.makedirs(d)

    # /etc basics
    vfs.mkfile("/etc/hostname", content=hostname + "\n")
    vfs.mkfile("/etc/hosts",
               content=f"127.0.0.1 localhost\n127.0.1.1 {hostname}\n"
                       f"::1 localhost ip6-localhost ip6-loopback\n",
               mode=0o644)
    vfs.mkfile("/etc/os-release",
               content=(f'NAME="{identity.get("os_name","Linux")}"\n'
                        f'VERSION="{identity.get("os_version","1.0")}"\n'
                        f'ID={identity.get("os_name","linux").lower()}\n'
                        f'VERSION_CODENAME={identity.get("os_codename","stable")}\n'
                        f'PRETTY_NAME="{identity.get("os_name","Linux")} {identity.get("os_version","1.0")} ({identity.get("os_codename","")})"\n'),
               mode=0o644)
    vfs.mkfile("/etc/passwd", content=_etc_passwd(users), mode=0o644)
    vfs.mkfile("/etc/shadow", content=_etc_shadow(users), owner="root", group="shadow", mode=0o640)
    vfs.mkfile("/etc/crontab", content=_crontab(), mode=0o644)
    vfs.mkfile("/etc/ssh/sshd_config",
               content="Port 22\nPermitRootLogin no\nPasswordAuthentication yes\n"
                       "PubkeyAuthentication yes\nX11Forwarding no\n",
               mode=0o644)

    # /proc virtual files
    _add_proc_files(vfs, profile)

    # /var/log
    vfs.mkfile("/var/log/auth.log", content=_auth_log(hostname, users),
               owner="root", group="adm", mode=0o640)
    vfs.mkfile("/var/log/syslog",
               content="-- Logs begin at " + datetime.datetime.now().strftime("%a %Y-%m-%d %H:%M:%S") + " --\n",
               owner="root", group="adm", mode=0o640)

    # Per-user home directories
    for u in users:
        home = u.get("home", f"/home/{u['username']}")
        uname = u["username"]
        vfs.makedirs(home, owner=uname, group=uname, mode=0o700)
        vfs.makedirs(f"{home}/.ssh", owner=uname, group=uname, mode=0o700)
        vfs.mkfile(f"{home}/.ssh/authorized_keys",
                   content=_ssh_authorized_keys(uname),
                   owner=uname, group=uname, mode=0o600)
        if u.get("shell") == "/bin/bash":
            vfs.mkfile(f"{home}/.bash_history",
                       content=_bash_history(uname),
                       owner=uname, group=uname, mode=0o600)
            vfs.mkfile(f"{home}/.bashrc",
                       content="# ~/.bashrc\nexport HISTSIZE=1000\nexport EDITOR=nano\nalias ll='ls -alF'\n",
                       owner=uname, group=uname, mode=0o644)

        # AWS creds for primary non-root user
        if u.get("uid", 0) == 1001:
            vfs.makedirs(f"{home}/.aws", owner=uname, group=uname, mode=0o700)
            vfs.mkfile(f"{home}/.aws/credentials",
                       content=_aws_credentials(),
                       owner=uname, group=uname, mode=0o600)

    # Profile-specific filesystem additions
    _add_profile_files(vfs, profile, users)

    return vfs


def _add_proc_files(vfs, profile):
    identity = profile.get("identity", {})
    hw = profile.get("hardware", {})
    net = profile.get("network", {})
    procs = profile.get("processes", [])

    cores = hw.get("cpu_cores", 4)
    threads = hw.get("cpu_threads", cores * 2)
    ram_kb = hw.get("ram_gb", 8) * 1024 * 1024
    free_kb = int(ram_kb * random.uniform(0.25, 0.55))

    # /proc/cpuinfo
    cpu_entries = []
    model = hw.get("cpu_model", "Intel(R) CPU")
    for i in range(threads):
        cpu_entries.append(
            f"processor\t: {i}\n"
            f"vendor_id\t: GenuineIntel\n"
            f"cpu family\t: 6\n"
            f"model\t\t: 165\n"
            f"model name\t: {model}\n"
            f"stepping\t: 5\n"
            f"cpu MHz\t\t: {random.uniform(800, 3500):.3f}\n"
            f"cache size\t: 16384 KB\n"
            f"physical id\t: 0\n"
            f"siblings\t: {threads}\n"
            f"core id\t\t: {i % cores}\n"
            f"cpu cores\t: {cores}\n"
            f"flags\t\t: fpu vme de pse tsc msr pae mce cx8 apic sep mtrr pge mca cmov\n"
            f"bogomips\t: {random.uniform(4000,8000):.2f}\n"
            f"clflush size\t: 64\n"
            f"cache_alignment\t: 64\n\n"
        )
    vfs.mkfile("/proc/cpuinfo", content="".join(cpu_entries), mode=0o444)

    # /proc/meminfo
    cached_kb = int(ram_kb * random.uniform(0.1, 0.25))
    buffers_kb = int(ram_kb * random.uniform(0.02, 0.08))
    swap_kb = (hw.get("ram_gb", 8) // 2) * 1024 * 1024
    vfs.mkfile("/proc/meminfo", content=(
        f"MemTotal:       {ram_kb:>10} kB\n"
        f"MemFree:        {free_kb:>10} kB\n"
        f"MemAvailable:   {free_kb + cached_kb:>10} kB\n"
        f"Buffers:        {buffers_kb:>10} kB\n"
        f"Cached:         {cached_kb:>10} kB\n"
        f"SwapCached:              0 kB\n"
        f"Active:         {int(ram_kb * 0.4):>10} kB\n"
        f"Inactive:       {int(ram_kb * 0.2):>10} kB\n"
        f"SwapTotal:      {swap_kb:>10} kB\n"
        f"SwapFree:       {swap_kb:>10} kB\n"
        f"Dirty:                  96 kB\n"
        f"Writeback:               0 kB\n"
        f"HugePages_Total:         0\n"
        f"HugePages_Free:          0\n"
        f"HugePages_Rsvd:          0\n"
        f"HugePages_Surp:          0\n"
    ), mode=0o444)

    # /proc/version
    kernel = identity.get("kernel", "5.15.0-91-generic")
    vfs.mkfile("/proc/version",
               content=f"Linux version {kernel.split()[0]} (buildd@ubuntu) "
                       f"(gcc version 11.4.0 (Ubuntu 11.4.0-1ubuntu1~22.04)) {kernel}\n",
               mode=0o444)

    # /proc/mounts
    vfs.mkfile("/proc/mounts", content=(
        "sysfs /sys sysfs rw,nosuid,nodev,noexec,relatime 0 0\n"
        "proc /proc proc rw,nosuid,nodev,noexec,relatime 0 0\n"
        "udev /dev devtmpfs rw,nosuid,relatime 0 0\n"
        "/dev/sda2 / ext4 rw,relatime 0 0\n"
        "/dev/sda1 /boot/efi vfat rw,relatime 0 0\n"
        "tmpfs /run/user/1000 tmpfs rw,nosuid,nodev,relatime 0 0\n"
    ), mode=0o444)

    # /proc/uptime
    uptime_range = identity.get("uptime_days_range", [1, 30])
    uptime_secs = random.randint(uptime_range[0], uptime_range[1]) * 86400 + random.randint(0, 86400)
    idle_secs = uptime_secs * threads * random.uniform(0.6, 0.95)
    vfs.mkfile("/proc/uptime", content=f"{uptime_secs}.{random.randint(0,99):02d} "
               f"{idle_secs:.2f}\n", mode=0o444)

    # /proc/<pid> stubs for each fake process
    vfs.makedirs("/proc", mode=0o555)
    for proc in procs:
        pid = proc.get("pid", 1)
        vfs.makedirs(f"/proc/{pid}", mode=0o555)
        vfs.mkfile(f"/proc/{pid}/cmdline",
                   content=proc.get("cmd", proc.get("name", "unknown")).replace(" ", "\x00") + "\x00",
                   mode=0o444)
        vfs.mkfile(f"/proc/{pid}/status",
                   content=f"Name:\t{proc.get('name','unknown')}\nPid:\t{pid}\n"
                           f"PPid:\t1\nUid:\t0\t0\t0\t0\nGid:\t0\t0\t0\t0\n",
                   mode=0o444)

    # /sys/class/net
    iface = net.get("primary_iface", "eth0")
    vfs.makedirs(f"/sys/class/net/{iface}", mode=0o555)
    vfs.mkfile(f"/sys/class/net/{iface}/address",
               content=net.get("mac", "00:00:00:00:00:00") + "\n", mode=0o444)
    vfs.mkfile(f"/sys/class/net/{iface}/operstate", content="up\n", mode=0o444)
    vfs.makedirs("/sys/class/net/lo", mode=0o555)
    vfs.mkfile("/sys/class/net/lo/address", content="00:00:00:00:00:00\n", mode=0o444)
    vfs.mkfile("/sys/class/net/lo/operstate", content="unknown\n", mode=0o444)


def _add_profile_files(vfs, profile, users):
    profile_name = profile.get("identity", {}).get("hostname", "")
    fs_cfg = profile.get("filesystem", {})

    primary_user = next((u for u in users if u.get("uid") == 1001), None)
    uname = primary_user["username"] if primary_user else "user"
    home = primary_user.get("home", f"/home/{uname}") if primary_user else f"/home/{uname}"

    if "web-prod" in profile_name or "nginx" in str(profile.get("processes", [])):
        # Web server layout
        vfs.makedirs("/var/www/html", owner="www-data", group="www-data")
        vfs.mkfile("/var/www/html/.env",
                   content=_env_file("webserver"),
                   owner="www-data", group="www-data", mode=0o640)
        vfs.mkfile("/var/www/html/wp-config.php",
                   content="<?php\ndefine('DB_NAME', 'wordpress');\ndefine('DB_USER', 'wpuser');\ndefine('DB_PASSWORD', 'Wp@ssw0rd!');\ndefine('DB_HOST', '10.20.1.20');\n",
                   owner="www-data", group="www-data", mode=0o640)
        vfs.makedirs("/var/log/nginx", owner="www-data", group="adm")
        vfs.mkfile("/var/log/nginx/access.log",
                   content="10.10.0.5 - - [01/Jan/2024:00:00:01 +0000] \"GET / HTTP/1.1\" 200 612\n",
                   owner="www-data", group="adm", mode=0o640)
        vfs.mkfile("/var/log/nginx/error.log", content="", owner="www-data", group="adm", mode=0o640)
        vfs.mkfile("/etc/nginx/nginx.conf",
                   content="worker_processes auto;\nevents { worker_connections 1024; }\nhttp { include /etc/nginx/sites-enabled/*; }\n",
                   mode=0o644)
    else:
        # Developer workstation layout
        vfs.makedirs(f"{home}/projects/api", owner=uname, group=uname)
        vfs.mkfile(f"{home}/projects/api/.env",
                   content=_env_file("workstation"),
                   owner=uname, group=uname, mode=0o600)
        vfs.mkfile(f"{home}/projects/api/server.py",
                   content="from flask import Flask\napp = Flask(__name__)\n\n@app.route('/')\ndef index():\n    return 'OK'\n",
                   owner=uname, group=uname, mode=0o644)
        vfs.mkfile(f"{home}/projects/api/config.py",
                   content="import os\nDB_URL = os.environ.get('DATABASE_URL')\nSECRET = os.environ.get('SECRET_KEY')\n",
                   owner=uname, group=uname, mode=0o644)
