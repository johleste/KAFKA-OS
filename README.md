# KAFKA-OS

A fully interactive SSH tarpit disguised as a real Linux system. Attackers get a convincing shell — complete filesystem, working commands, plausible processes — but nothing consequential ever succeeds. Downloads stall at 94%. Builds fail at 97%. `sudo` requires MFA, justification codes, and committee approval. Everything is logged.

Inspired by Franz Kafka. Weaponized for network defense.

---

## How It Works

Every inbound SSH connection using password authentication drops into KAFKA-OS regardless of what credentials are provided. The attacker sees a real Ubuntu login, a real shell prompt, and a fully populated filesystem. They can browse files, run commands, and attempt privilege escalation — but every meaningful action is routed through a bureaucratic engine that delays, redirects, and ultimately denies it through procedurally generated compliance failures.

Operators authenticate via SSH key and get a real shell on the host.

```
Attacker (password auth) ──► KAFKA-OS tarpit shell
                                  │
                                  ├── Profile-driven VFS (unique per session)
                                  ├── 80+ Linux commands implemented
                                  ├── Bureaucracy engine (delays, rejections, loops)
                                  ├── Attacker tool registry (fake recon output)
                                  └── Session logger (keystrokes, credentials, intel)

Operator (key auth) ──────► Real PTY shell on host
```

In cluster mode, multiple instances run simultaneously and know about each other. An attacker who runs `nmap 10.0.0.0/24` discovers the whole fake subnet. `ssh 10.0.0.12` drops them into a different machine with a different profile.

---

## Features

### Convincing Machine Identity

Each profile defines a complete machine persona: hostname, OS version, kernel, hardware specs, network interfaces, users, and running processes. `uname -a`, `ps aux`, `df -h`, `lscpu`, `lshw`, `smartctl`, `dmidecode`, and `ip addr` all return consistent output derived from the active profile.

### Fresh Virtual Filesystem Per Session

The VFS is built in memory for each new connection from the active profile. It includes:
- `/etc/passwd`, `/etc/shadow`, `/etc/hosts`, `/etc/crontab`, SSH configs
- Per-user home directories with `.bash_history`, `.bashrc`, `.ssh/authorized_keys`
- AWS credential files, `.env` files with fake database credentials, application source code
- Auth logs with realistic login history
- `/proc/cpuinfo`, `/proc/meminfo`, `/proc/mounts`, per-PID stubs, `/sys/class/net/`
- Profile-specific layouts: web server has nginx configs and WordPress files; workstation has dev projects and API keys

### 80+ Linux Commands

All standard commands work against the VFS. The trap is in what happens when something matters:

| Command | Behavior |
|---|---|
| `ls`, `cd`, `pwd`, `find`, `grep` | Works normally against VFS |
| `cat` on normal files | Works |
| `cat` on sensitive files | Security hold — forwarded for FACM review |
| `cat` on interesting files | Starts, then suspends for compliance audit |
| `sudo` | Password → MFA → justification → multi-step review → denied |
| `su` | PAM validation → always fails |
| `curl` / `wget` | Routes through attacker tool registry (see below) |
| `ssh <sibling>` | Full profile/VFS swap into sibling machine (cluster mode) |
| `vim` / `nano` | Opens, accepts edits, confirms write → changes silently discarded |
| `crontab -e` | Accepts job → pending 5-10 business day review |
| `gcc` / `make` / `python3` | Runs → fails at 97% with compliance error |
| `apt install` | Downloads → stalls → flagged by Static Analysis Daemon |
| `rm` | Queued for WOID approval (3-7 business days) |
| `ping` | 25-75% packet loss, anomaly report filed |
| `lscpu`, `lshw`, `lspci`, `lsusb` | Returns full hardware inventory from profile |
| `smartctl`, `hdparm`, `dmidecode` | Realistic drive health and BIOS output |
| `systemctl` | Fake service state tracking; start/stop/status per session |
| `pip`, `npm`, `cargo`, `gem`, `snap` | Fake package install with progress bars |

### Attacker Tool Registry

Tools are categorized and handled according to their purpose. Behavior is configurable per category in `download_behavior` config:

| Category | Default behavior | Examples |
|---|---|---|
| `recon` | `fake_execute` — produces convincing fake findings | linpeas, pspy64, nmap, gobuster, nikto, enum4linux, nuclei |
| `exploit` | `fake_install` — appears ready, fails on use | msfconsole, sqlmap, searchsploit, generic exploits |
| `lateral` | `fake_install` | chisel, crackmapexec, impacket, bloodhound |
| `persistence` | `fake_install` | backdoor.sh, rootkit.sh, install.sh |
| `exfil` | `stall` — always blocked at 94% | rclone, s3cmd |

When a tool is downloaded via `wget` or `curl`, it either stalls (exfil), or appears to download fully and is registered in the session. Running it directly (`./linpeas.sh`, `nmap 10.0.0.0/24`, `msfconsole`) dispatches to the matching generator:

- **linpeas** produces a full fake SUID list, sudo check, interesting files, cron jobs, and open ports — all drawn from the profile to look consistent with the machine
- **pspy** streams fake process events until Ctrl-C
- **nmap** generates per-profile open ports; subnet scans (`/24`) enumerate all cluster members
- **metasploit** opens an interactive `msf6 >` prompt, lets them load a module, and fails at the point of use
- **netcat** appears to connect for a reverse shell, then times out
- **crackmapexec** returns `STATUS_LOGON_FAILURE`
- **rclone**, **bloodhound**, **impacket**, and others each return appropriate failure output

### Cluster Mode

Run multiple instances simultaneously, each with its own port, fake IP, and machine profile. The instances know about each other.

```
10.0.0.11 :2222  dev-ws-042    (workstation profile)
10.0.0.12 :2223  web-prod-03   (webserver profile)
10.0.0.13 :2224  dev-ws-042-02 (workstation profile)
```

From inside any instance:
- `nmap 10.0.0.0/24` — shows all cluster members with per-profile open ports
- `nmap 10.0.0.12` — shows that specific machine's ports
- `ssh 10.0.0.12` — fully swaps the live session into that sibling's profile and a fresh VFS; `exit` returns to the original host

**`new_machine_on_disconnect`** — after each attacker session ends, the instance regenerates with a random hostname. The next attacker sees what appears to be a different machine on the same IP, making the subnet feel larger and more active.

### Bureaucracy Engine

All meaningful operations pass through a configurable friction layer:
- **Simulated checks** — named subsystem validations with realistic delays
- **Audit forwarding** — events forwarded to named review bodies (FACM, PEAD, PECU, NASL) with accumulating pending review counts
- **Mandate checks** — arbitrary lockout rules (prime minute Tuesdays, audit backlog thresholds, random 5% spot-checks)
- **Circular verification** — unknown commands trigger multi-cycle verification loops ending in accusation
- **Intent verification** — high-risk commands require confirmation phrases, re-authentication, and justification codes

### Hidden Operator Channel

SSH key authentication bypasses the tarpit entirely and spawns a real PTY shell on the host. A console magic string (optional) provides the same bypass via password for local access.

### Session Logging

Every session is recorded:
- Full keystroke and output transcripts in JSONL per session
- Credential detection heuristic flags lines containing passwords, tokens, or keys
- Session summaries with full command history appended to an intelligence log on disconnect

---

## Setup

### Requirements

```bash
pip3 install -r requirements.txt
```

Dependencies: `paramiko`, `pyyaml`, `cryptography`

### Run (single instance)

```bash
python3 main.py
```

On first run, an RSA host key is generated at `kafka_host_rsa`. The SSH server listens on port 22 by default (requires root, or change the port in config).

```bash
# Override profile
python3 main.py --profile webserver

# Custom config
python3 main.py --config config/default.yaml
```

### Run (cluster mode)

Enable cluster mode in `config/default.yaml`:

```yaml
cluster:
  enabled: true
  instances: 3
  port_start: 2222
```

Or force it from the command line:

```bash
python3 main.py --cluster
```

Each instance gets its own host key (`kafka_host_rsa_instance-0`, etc.), its own port, and its own fake IP drawn from the `base_ip` / `ip_start` config.

### Operator Access

```bash
ssh-keygen -t ed25519 -f ~/.ssh/kafka_operator
cat ~/.ssh/kafka_operator.pub >> ~/.ssh/kafka_operator_authorized_keys
ssh -i ~/.ssh/kafka_operator user@target
```

---

## Configuration

### `config/default.yaml`

```yaml
profile: workstation       # which machine persona to load

cluster:
  enabled: false
  instances: 3              # concurrent fake machines
  port_start: 2222          # first instance on 2222, next 2223, etc.
  base_ip: "10.0.0"        # fake internal subnet prefix
  ip_start: 11             # 10.0.0.11, 10.0.0.12, ...
  profiles:
    - workstation
    - webserver
  respawn: true             # auto-restart instance on error
  new_machine_on_disconnect: false  # regenerate identity after each session

bureaucracy:
  friction_level: 3        # 1 = believable lag, 5 = pure hell
  download_stall_at: 0.94  # progress bars die here
  compile_fail_at: 0.97    # builds fail here
  sudo_success_chance: 0.0

download_behavior:
  default: fake_install
  categories:
    recon: fake_execute
    exploit: fake_install
    lateral: fake_install
    persistence: fake_install
    exfil: stall

endpoints:
  ssh:
    enabled: true
    port: 22
    banner: "OpenSSH_8.9p1 Ubuntu-3ubuntu0.6, OpenSSL 3.0.2 15 Mar 2022"

operator:
  authorized_keys_file: ~/.ssh/kafka_operator_authorized_keys
  console_magic: ""
  real_shell: /bin/bash

logging:
  session_dir: /var/log/kafka-os/sessions
  intelligence_log: /var/log/kafka-os/intelligence.jsonl
```

### Profiles

Profiles live in `config/profiles/`. Each defines the machine's identity, hardware, network, users, running processes, pre-installed packages, and filesystem layout.

| Profile | Persona |
|---|---|
| `workstation.yaml` | Developer workstation — Docker, VS Code, Python API project, postgres |
| `webserver.yaml` | Production nginx/PHP web server — WordPress, deploy user, php-fpm |

To add a profile, copy an existing one and adjust the fields. The VFS generator builds the entire filesystem from the profile automatically.

---

## Logs

```bash
# Watch live
tail -f /var/log/kafka-os/intelligence.jsonl | python3 -m json.tool

# Review a session
cat /var/log/kafka-os/sessions/*.jsonl | python3 -m json.tool
```

Sessions are written to `session_dir` as JSONL files named `{session_id}_{username}_{ip}.jsonl`. The intelligence log aggregates flagged credentials and per-session command summaries across all sessions.

---

## Architecture

```
main.py                    Entry point — single or cluster mode
config/
  default.yaml             Master configuration
  profiles/                Machine identity profiles
cluster/
  registry.py              Thread-safe singleton registry of running instances
  manager.py               Spawns N instances; handles respawn and identity rotation
vfs/
  tree.py                  In-memory virtual filesystem (VFSNode tree)
  generator.py             Builds VFS from profile (users, /proc, history, credentials)
shell/
  interpreter.py           Session state, command dispatch, shell loop
  commands/
    filesystem.py          ls, cat, find, grep, cp, mv, rm, chmod, head, tail
    system.py              ps, df, free, uname, uptime, who, id, date, history
    network.py             ping, ssh (with cluster sibling routing), curl, wget, netstat, ip
    auth.py                sudo, su, passwd
    editors.py             vim, vi, nano
    execution.py           python3, bash, gcc, make, apt, crontab
    hardware.py            lscpu, lshw, lspci, lsusb, lsblk, smartctl, hdparm, dmidecode
    packages.py            pip, npm, cargo, gem, snap, dpkg, systemctl, which, man
    attacker_tools.py      Tool registry, fake download, fake output generators
  bureaucracy/
    engine.py              Delays, checks, forwarding, mandate rules, circular rejection
endpoints/
  ssh.py                   Paramiko SSH server — operator key detection, per-session VFS
op_shell/
  shell.py                 PTY bridge for real operator shell
session_log/
  session.py               Per-session JSONL recording, credential detection, intel log
```
