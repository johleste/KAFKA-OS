import random
import time

# ---------------------------------------------------------------------------
# Known package metadata — bin paths and versions for common packages
# ---------------------------------------------------------------------------

KNOWN_PACKAGES = {
    "nginx":          {"bin": "/usr/sbin/nginx",       "version": "1.24.0"},
    "apache2":        {"bin": "/usr/sbin/apache2",     "version": "2.4.57"},
    "mysql-server":   {"bin": "/usr/sbin/mysqld",      "version": "8.0.35"},
    "postgresql":     {"bin": "/usr/bin/psql",         "version": "14.10"},
    "redis-server":   {"bin": "/usr/bin/redis-server", "version": "7.0.14"},
    "docker-ce":      {"bin": "/usr/bin/docker",       "version": "24.0.7"},
    "docker.io":      {"bin": "/usr/bin/docker",       "version": "24.0.5"},
    "python3":        {"bin": "/usr/bin/python3",      "version": "3.10.12"},
    "python3-pip":    {"bin": "/usr/bin/pip3",         "version": "22.0.2"},
    "nodejs":         {"bin": "/usr/bin/node",         "version": "18.19.0"},
    "npm":            {"bin": "/usr/bin/npm",          "version": "9.2.0"},
    "git":            {"bin": "/usr/bin/git",          "version": "2.34.1"},
    "curl":           {"bin": "/usr/bin/curl",         "version": "7.81.0"},
    "wget":           {"bin": "/usr/bin/wget",         "version": "1.21.2"},
    "vim":            {"bin": "/usr/bin/vim",          "version": "8.2.3995"},
    "nano":           {"bin": "/usr/bin/nano",         "version": "6.2"},
    "htop":           {"bin": "/usr/bin/htop",         "version": "3.2.1"},
    "nmap":           {"bin": "/usr/bin/nmap",         "version": "7.80"},
    "netcat-openbsd": {"bin": "/usr/bin/nc",           "version": "1.219"},
    "nc":             {"bin": "/usr/bin/nc",           "version": "1.219"},
    "tcpdump":        {"bin": "/usr/sbin/tcpdump",     "version": "4.99.1"},
    "wireshark":      {"bin": "/usr/bin/wireshark",    "version": "3.6.2"},
    "openssh-server": {"bin": "/usr/sbin/sshd",       "version": "8.9p1"},
    "openssh-client": {"bin": "/usr/bin/ssh",         "version": "8.9p1"},
    "fail2ban":       {"bin": "/usr/bin/fail2ban-client", "version": "0.11.2"},
    "ufw":            {"bin": "/usr/sbin/ufw",         "version": "0.36.1"},
    "rsync":          {"bin": "/usr/bin/rsync",        "version": "3.2.3"},
    "tmux":           {"bin": "/usr/bin/tmux",         "version": "3.2a"},
    "screen":         {"bin": "/usr/bin/screen",       "version": "4.9.0"},
    "build-essential":{"bin": "/usr/bin/gcc",          "version": "12.3.0"},
    "gcc":            {"bin": "/usr/bin/gcc",          "version": "11.4.0"},
    "make":           {"bin": "/usr/bin/make",         "version": "4.3"},
    "strace":         {"bin": "/usr/bin/strace",       "version": "5.16"},
    "gdb":            {"bin": "/usr/bin/gdb",          "version": "12.1"},
    "certbot":        {"bin": "/usr/bin/certbot",      "version": "1.21.0"},
    "php8.1-fpm":     {"bin": "/usr/sbin/php-fpm8.1", "version": "8.1.2"},
    "jq":             {"bin": "/usr/bin/jq",           "version": "1.6"},
    "unzip":          {"bin": "/usr/bin/unzip",        "version": "6.0"},
    "zip":            {"bin": "/usr/bin/zip",          "version": "3.0"},
}

KNOWN_SERVICES = {
    "ssh":        {"active": True,  "enabled": True},
    "sshd":       {"active": True,  "enabled": True},
    "nginx":      {"active": False, "enabled": False},
    "apache2":    {"active": False, "enabled": False},
    "mysql":      {"active": False, "enabled": False},
    "postgresql": {"active": False, "enabled": False},
    "docker":     {"active": True,  "enabled": True},
    "cron":       {"active": True,  "enabled": True},
    "ufw":        {"active": False, "enabled": False},
    "fail2ban":   {"active": False, "enabled": False},
}


def _init_session_packages(session):
    if not hasattr(session, "_packages_initialized"):
        for pkg in session.profile.get("hardware", {}).get("installed_packages", []):
            name = pkg.get("name", "")
            ver = pkg.get("version", "1.0")
            meta = KNOWN_PACKAGES.get(name, {"bin": f"/usr/bin/{name}", "version": ver})
            session.installed_packages[name] = {
                "version": ver,
                "bin": meta.get("bin", f"/usr/bin/{name}"),
            }
        # Init service state from known services + installed packages
        for svc, state in KNOWN_SERVICES.items():
            session.services[svc] = "active" if state["active"] else "inactive"
        session._packages_initialized = True


def _fake_install(session, bure, pkg_name, pkg_manager="apt"):
    meta = KNOWN_PACKAGES.get(pkg_name, {
        "bin": f"/usr/bin/{pkg_name}",
        "version": f"{random.randint(1,5)}.{random.randint(0,9)}.{random.randint(0,20)}",
    })
    session.installed_packages[pkg_name] = {
        "version": meta["version"],
        "bin": meta["bin"],
    }
    # Auto-enable service if it maps to one
    if pkg_name in KNOWN_SERVICES:
        session.services[pkg_name] = "inactive"


# ---------------------------------------------------------------------------
# apt
# ---------------------------------------------------------------------------

def cmd_apt(session, args, bure):
    _init_session_packages(session)
    if not args:
        session.write("apt: missing command\n")
        return
    subcmd = args[0]
    pkgs = [a for a in args[1:] if not a.startswith("-")]

    if subcmd in ("update",):
        bure.log("APT: Refreshing package index...")
        session.write("Hit:1 http://archive.ubuntu.com/ubuntu jammy InRelease\n")
        session.write("Hit:2 http://archive.ubuntu.com/ubuntu jammy-updates InRelease\n")
        session.write("Hit:3 http://security.ubuntu.com/ubuntu jammy-security InRelease\n")
        bure.simulated_check("Package Index Refresh", "base_check_medium_ms")
        session.write(f"Reading package lists... Done\n")
        session.write(f"Building dependency tree... Done\n")
        session.write(f"Reading state information... Done\n")
        session.write(f"{random.randint(0,20)} packages can be upgraded.\n")
        return

    if subcmd in ("upgrade", "full-upgrade", "dist-upgrade"):
        bure.log("APT: System upgrade requested.")
        session.write("Reading package lists... Done\n")
        session.write("Building dependency tree... Done\n")
        n = random.randint(3, 15)
        session.write(f"{n} upgraded, 0 newly installed, 0 to remove and 0 not upgraded.\n")
        session.write(f"Need to get {random.randint(10,100)} MB of archives.\n")
        bure.download_progress("upgrades.tar", random.randint(10000, 100000))
        return

    if subcmd in ("install",):
        if not pkgs:
            session.write("apt: 'install' requires at least one package\n")
            return
        session.write("Reading package lists... Done\n")
        session.write("Building dependency tree... Done\n")
        session.write("Reading state information... Done\n")

        deps = []
        for pkg in pkgs:
            if pkg not in session.installed_packages:
                meta = KNOWN_PACKAGES.get(pkg, {"bin": f"/usr/bin/{pkg}",
                                                 "version": f"1.{random.randint(0,9)}.0"})
                deps.append((pkg, meta.get("version", "1.0.0")))

        if not deps:
            session.write(f"{', '.join(pkgs)} is already the newest version.\n0 upgraded, 0 newly installed.\n")
            return

        total_kb = sum(random.randint(200, 8000) for _ in deps)
        session.write(f"The following NEW packages will be installed:\n")
        session.write(f"  {' '.join(p[0] for p in deps)}\n")
        session.write(f"0 upgraded, {len(deps)} newly installed, 0 to remove and 0 not upgraded.\n")
        session.write(f"Need to get {total_kb} kB of archives.\n")
        session.write(f"Do you want to continue? [Y/n] ")
        confirm = session.prompt("")
        if confirm.lower() in ("n", "no"):
            session.write("Abort.\n")
            return

        for pkg, ver in deps:
            kb = random.randint(200, 8000)
            session.write(f"Get:{random.randint(1,5)} http://archive.ubuntu.com/ubuntu jammy/main amd64 {pkg} amd64 {ver}\n")
            bure.download_progress(f"{pkg}_{ver}_amd64.deb", kb)
            if not _was_stalled(bure):
                session.write(f"Selecting previously unselected package {pkg}.\n")
                session.write(f"Preparing to unpack .../{pkg}_{ver}_amd64.deb ...\n")
                session.write(f"Unpacking {pkg} ({ver}) ...\n")
                session.write(f"Setting up {pkg} ({ver}) ...\n")
                bure.simulated_check(f"Post-install configuration for {pkg}", "base_check_short_ms")
                _fake_install(session, bure, pkg)

        session.write(f"Processing triggers for man-db (2.10.2) ...\n")
        return

    if subcmd in ("remove", "purge"):
        for pkg in pkgs:
            if pkg in session.installed_packages:
                del session.installed_packages[pkg]
                session.write(f"Removing {pkg} ...\n")
            else:
                session.write(f"Package '{pkg}' is not installed, so not removed.\n")
        return

    if subcmd == "list":
        for name, info in session.installed_packages.items():
            session.write(f"{name}/{name} {info['version']} amd64 [installed]\n")
        return

    session.write(f"apt: '{subcmd}' is not a recognized command\n")


def _was_stalled(bure):
    return False  # Download always stalls internally; install proceeds anyway for realism


# ---------------------------------------------------------------------------
# pip / pip3
# ---------------------------------------------------------------------------

def cmd_pip(session, args, bure):
    _init_session_packages(session)
    if not args:
        session.write("pip: missing command\n")
        return
    subcmd = args[0]
    pkgs = [a for a in args[1:] if not a.startswith("-")]

    if subcmd == "install":
        if not pkgs:
            session.write("ERROR: You must give at least one requirement to install\n")
            return
        for pkg in pkgs:
            ver = f"{random.randint(0,5)}.{random.randint(0,20)}.{random.randint(0,10)}"
            size_kb = random.randint(50, 5000)
            session.write(f"Collecting {pkg}\n")
            session.write(f"  Downloading {pkg}-{ver}-py3-none-any.whl ({size_kb} kB)\n")
            steps = 20
            for i in range(steps + 1):
                pct = int((i / steps) * 100)
                bar = "━" * i + " " * (steps - i)
                session.write(f"\r     [{bar}] {size_kb * i // steps} kB/{size_kb} kB")
                time.sleep(0.15)
            session.write("\n")
            session.write(f"Installing collected packages: {pkg}\n")
            session.write(f"Successfully installed {pkg}-{ver}\n")
            _fake_install(session, bure, pkg, "pip")
        return

    if subcmd in ("list", "freeze"):
        for name, info in session.installed_packages.items():
            session.write(f"{name}=={info['version']}\n")
        return

    if subcmd == "show":
        for pkg in pkgs:
            if pkg in session.installed_packages:
                info = session.installed_packages[pkg]
                session.write(
                    f"Name: {pkg}\nVersion: {info['version']}\n"
                    f"Location: /usr/local/lib/python3.10/dist-packages\n"
                    f"Requires: \nRequired-by: \n"
                )
            else:
                session.write(f"WARNING: Package(s) not found: {pkg}\n")
        return

    session.write(f"pip: unknown command '{subcmd}'\n")


# ---------------------------------------------------------------------------
# npm
# ---------------------------------------------------------------------------

def cmd_npm(session, args, bure):
    _init_session_packages(session)
    if not args:
        session.write("npm <command>\n")
        return
    subcmd = args[0]
    pkgs = [a for a in args[1:] if not a.startswith("-")]

    if subcmd == "install" or subcmd == "i":
        if not pkgs:
            session.write("\nadded 0 packages in 0s\n")
            return
        for pkg in pkgs:
            ver = f"{random.randint(1,9)}.{random.randint(0,20)}.{random.randint(0,10)}"
            deps = random.randint(1, 80)
            session.write(f"\nadded {deps} packages in {random.uniform(1,8):.1f}s\n")
            _fake_install(session, bure, pkg, "npm")
        return

    if subcmd in ("list", "ls"):
        session.write("project@1.0.0\n")
        for name, info in list(session.installed_packages.items())[:10]:
            session.write(f"├── {name}@{info['version']}\n")
        return

    session.write(f"npm: unknown command: {subcmd}\n")


# ---------------------------------------------------------------------------
# yarn
# ---------------------------------------------------------------------------

def cmd_yarn(session, args, bure):
    _init_session_packages(session)
    if not args:
        session.write("yarn <command>\n")
        return
    subcmd = args[0]
    pkgs = [a for a in args[1:] if not a.startswith("-")]

    if subcmd in ("add", "install"):
        for pkg in pkgs:
            ver = f"{random.randint(1,9)}.{random.randint(0,20)}.{random.randint(0,10)}"
            session.write(f"yarn add v1.22.19\n[1/4] Resolving packages...\n")
            session.write(f"[2/4] Fetching packages...\n[3/4] Linking dependencies...\n")
            session.write(f"[4/4] Building fresh packages...\n")
            session.write(f"success Saved 1 new dependency.\n└─ {pkg}@{ver}\n")
            session.write(f"Done in {random.uniform(1,5):.2f}s.\n")
            _fake_install(session, bure, pkg, "yarn")
        return

    session.write(f"yarn: command not found: {subcmd}\n")


# ---------------------------------------------------------------------------
# cargo (Rust)
# ---------------------------------------------------------------------------

def cmd_cargo(session, args, bure):
    _init_session_packages(session)
    if not args:
        session.write("cargo <COMMAND>\n")
        return
    subcmd = args[0]
    pkgs = [a for a in args[1:] if not a.startswith("-")]

    if subcmd in ("install",):
        for pkg in pkgs:
            ver = f"{random.randint(0,5)}.{random.randint(0,20)}.{random.randint(0,10)}"
            session.write(f"    Updating crates.io index\n")
            session.write(f"  Downloaded {pkg} v{ver}\n")
            bure.compile_progress(pkg)
        return

    if subcmd in ("build",):
        bure.compile_progress(args[1] if len(args) > 1 else "project")
        return

    session.write(f"error: no such subcommand: `{subcmd}`\n")


# ---------------------------------------------------------------------------
# gem (Ruby)
# ---------------------------------------------------------------------------

def cmd_gem(session, args, bure):
    _init_session_packages(session)
    if not args:
        session.write("gem <COMMAND>\n")
        return
    subcmd = args[0]
    pkgs = [a for a in args[1:] if not a.startswith("-")]

    if subcmd == "install":
        for pkg in pkgs:
            ver = f"{random.randint(1,5)}.{random.randint(0,9)}.{random.randint(0,5)}"
            size_kb = random.randint(50, 2000)
            session.write(f"Fetching {pkg}-{ver}.gem\n")
            session.write(f"Successfully installed {pkg}-{ver}\n")
            session.write(f"1 gem installed\n")
            _fake_install(session, bure, pkg, "gem")
        return

    session.write(f"ERROR: Unknown command {subcmd}\n")


# ---------------------------------------------------------------------------
# snap
# ---------------------------------------------------------------------------

def cmd_snap(session, args, bure):
    _init_session_packages(session)
    if not args:
        session.write("snap <command>\n")
        return
    subcmd = args[0]
    pkgs = [a for a in args[1:] if not a.startswith("-")]

    if subcmd == "install":
        for pkg in pkgs:
            ver = f"{random.randint(1,9)}.{random.randint(0,20)}"
            size_mb = random.randint(10, 200)
            session.write(f"{pkg} {ver} from Publisher installed\n")
            _fake_install(session, bure, pkg, "snap")
        return

    if subcmd == "list":
        session.write(f"{'Name':<20} {'Version':<12} {'Rev':>5} {'Tracking':<20} Publisher\n")
        for name, info in session.installed_packages.items():
            session.write(f"{name:<20} {info['version']:<12} {random.randint(1000,9999):>5} "
                          f"{'latest/stable':<20} canonical\n")
        return

    session.write(f"error: unknown command \"{subcmd}\"\n")


# ---------------------------------------------------------------------------
# dpkg
# ---------------------------------------------------------------------------

def cmd_dpkg(session, args, bure):
    _init_session_packages(session)
    flags = [a for a in args if a.startswith("-")]
    pkgs = [a for a in args if not a.startswith("-")]

    if "-l" in flags or "--list" in flags:
        session.write(
            f"Desired=Unknown/Install/Remove/Purge/Hold\n"
            f"| Status=Not/Inst/Conf-files/Unpacked/halF-conf/Half-inst/trig-aWait/Trig-pend\n"
            f"|/ Err?=(none)/Reinst-required (Status,Err: uppercase=bad)\n"
            f"||/ Name                     Version              Architecture Description\n"
            f"+++-========================-====================-============-===============================\n"
        )
        filter_pkg = pkgs[0] if pkgs else None
        for name, info in session.installed_packages.items():
            if filter_pkg and filter_pkg.lower() not in name.lower():
                continue
            desc = f"Package {name}"
            session.write(f"ii  {name:<25} {info['version']:<20} amd64        {desc}\n")
        return

    if "-s" in flags or "--status" in flags:
        for pkg in pkgs:
            if pkg in session.installed_packages:
                info = session.installed_packages[pkg]
                session.write(
                    f"Package: {pkg}\nStatus: install ok installed\nPriority: optional\n"
                    f"Section: misc\nInstalled-Size: {random.randint(100,5000)}\n"
                    f"Architecture: amd64\nVersion: {info['version']}\n"
                    f"Description: {pkg} package\n"
                )
            else:
                session.write(f"dpkg-query: package '{pkg}' is not installed\n")
        return

    session.write("dpkg: error processing\n")


# ---------------------------------------------------------------------------
# which / whereis
# ---------------------------------------------------------------------------

def cmd_which(session, args, bure):
    _init_session_packages(session)
    for cmd in args:
        # Check installed packages first
        for name, info in session.installed_packages.items():
            bin_path = info.get("bin", "")
            if bin_path.endswith("/" + cmd) or name == cmd:
                session.write(bin_path + "\n")
                break
        else:
            # Check built-ins
            pkg = KNOWN_PACKAGES.get(cmd)
            if pkg:
                session.write(pkg["bin"] + "\n")
            else:
                session.write(f"{cmd} not found\n")


def cmd_whereis(session, args, bure):
    _init_session_packages(session)
    for cmd in args:
        pkg = KNOWN_PACKAGES.get(cmd) or next(
            (info for name, info in session.installed_packages.items()
             if name == cmd), None)
        if pkg:
            bin_path = pkg.get("bin", f"/usr/bin/{cmd}")
            session.write(
                f"{cmd}: {bin_path} /usr/share/man/man1/{cmd}.1.gz\n"
            )
        else:
            session.write(f"{cmd}:\n")


# ---------------------------------------------------------------------------
# systemctl / service
# ---------------------------------------------------------------------------

def cmd_systemctl(session, args, bure):
    _init_session_packages(session)
    if not args:
        session.write("systemctl <command> [service]\n")
        return

    subcmd = args[0]
    svc = args[1].replace(".service", "") if len(args) > 1 else None

    if subcmd == "list-units" or subcmd == "list-unit-files":
        session.write(f"{'UNIT':<35} {'LOAD':<8} {'ACTIVE':<8} {'SUB':<8} DESCRIPTION\n")
        for name, state in session.services.items():
            active = "active" if state == "active" else "inactive"
            sub = "running" if active == "active" else "dead"
            session.write(f"{name+'.service':<35} {'loaded':<8} {active:<8} {sub:<8} {name}\n")
        return

    if not svc:
        session.write(f"systemctl: missing service name\n")
        return

    if subcmd == "status":
        state = session.services.get(svc, "inactive")
        active = state == "active"
        pid = random.randint(400, 9000)
        session.write(
            f"● {svc}.service - {svc.capitalize()} Service\n"
            f"     Loaded: loaded (/lib/systemd/system/{svc}.service; "
            f"{'enabled' if active else 'disabled'}; vendor preset: enabled)\n"
            f"     Active: {'active (running)' if active else 'inactive (dead)'} "
            f"since {__import__('datetime').datetime.now().strftime('%a %Y-%m-%d %H:%M:%S %Z')}; "
            f"{random.randint(1,60)}min ago\n"
        )
        if active:
            session.write(f"    Main PID: {pid} ({svc})\n")
            session.write(f"       Tasks: {random.randint(1,20)}\n")
            session.write(f"      Memory: {random.uniform(1,100):.1f}M\n")
        return

    if subcmd == "start":
        if svc not in session.installed_packages and svc not in KNOWN_SERVICES:
            session.write(f"Failed to start {svc}.service: Unit {svc}.service not found.\n")
            return
        bure.simulated_check(f"Service start authorization for {svc}", "base_check_short_ms")
        session.services[svc] = "active"
        return  # systemctl start produces no output on success

    if subcmd == "stop":
        session.services[svc] = "inactive"
        return

    if subcmd == "restart":
        bure.simulated_check(f"Service restart for {svc}", "base_check_short_ms")
        session.services[svc] = "active"
        return

    if subcmd == "enable":
        bure.log(f"Enabling {svc} at boot.")
        session.services[svc] = session.services.get(svc, "inactive")
        session.write(
            f"Created symlink /etc/systemd/system/multi-user.target.wants/{svc}.service "
            f"→ /lib/systemd/system/{svc}.service.\n"
        )
        return

    if subcmd == "disable":
        session.write(
            f"Removed /etc/systemd/system/multi-user.target.wants/{svc}.service.\n"
        )
        return

    session.write(f"Unknown operation '{subcmd}'.\n")


def cmd_service(session, args, bure):
    if len(args) < 2:
        session.write("Usage: service <service> <command>\n")
        return
    svc, subcmd = args[0], args[1]
    cmd_systemctl(session, [subcmd, svc], bure)


# ---------------------------------------------------------------------------
# man (bureaucratic version)
# ---------------------------------------------------------------------------

def cmd_man(session, args, bure):
    if not args:
        session.write("What manual page do you want?\n")
        return
    page = args[0]
    bure.log(f"FACM: Manual page '{page}' access requested.")
    bure.simulated_check("Documentation Repository Index Lookup", "base_check_short_ms")
    bure.forward('FS_ACCESS', f"man:{page}", "Manual Page Access")
    session.write(
        f"\nMANUAL PAGE ACCESS REQUEST — Ref: MAN-{bure._short_ref()[:6]}\n"
        f"Page '{page}' located in Documentation Repository.\n"
        f"Rendering requires Documentation Access Authorization (DAA-7702).\n"
        f"Submit request via IT portal. Estimated processing: 2-4 hours.\n\n"
    )
