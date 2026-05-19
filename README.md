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
                                  ├── Fully generated VFS (profile-driven)
                                  ├── 64 Linux commands implemented
                                  ├── Bureaucracy engine (delays, rejections, loops)
                                  └── Session logger (keystrokes, credentials, intel)

Operator (key auth) ──────► Real PTY shell on host
```

---

## Features

### Convincing Machine Identity
Each profile defines a complete machine persona: hostname, OS version, kernel, hardware specs, network interfaces, users, and running processes. `uname -a`, `ps aux`, `df -h`, `id`, and `ip addr` all return plausible, consistent output derived from the active profile.

### Fully Generated Virtual Filesystem
The VFS is built at startup from the profile. It includes:
- `/etc/passwd`, `/etc/shadow`, `/etc/hosts`, `/etc/crontab`, SSH configs
- Per-user home directories with `.bash_history`, `.bashrc`, `.ssh/authorized_keys`
- AWS credential files, `.env` files, application source code
- Auth logs with realistic login history
- Profile-specific layouts (web server has nginx configs and WordPress files; workstation has dev projects and API keys)

### 64 Linux Commands
All standard commands are implemented against the VFS. Most work normally at first glance — the trap is in what happens when something matters:

| Command | Behavior |
|---|---|
| `ls`, `cd`, `pwd`, `find`, `grep` | Works normally against VFS |
| `cat` on normal files | Works |
| `cat` on sensitive files | Security hold — forwarded for FACM review |
| `cat` on interesting files | Starts, then suspends for compliance audit |
| `sudo` | Password → MFA → justification → multi-step review → denied |
| `su` | PAM validation → always fails |
| `curl` / `wget` | Progress bar → stalls at 94% → TLS cert pending PKI approval |
| `ssh <host>` | Connects → nested tarpit session |
| `vim` / `nano` | Opens, accepts edits, confirms write → changes silently discarded |
| `crontab -e` | Accepts job → confirms scheduled → pending 5-10 business day review |
| `gcc` / `make` / `python3` | Runs → fails at 97% with compliance error |
| `apt install` | Downloads → stalls → package flagged by Static Analysis Daemon |
| `rm` | Queued for WOID approval (3-7 business days) |
| `ping` | Runs with 25-75% packet loss, anomaly report filed |
| `chmod` | Silently appears to succeed — permissions unchanged |
| `history` | Returns plausible session history |

### Bureaucracy Engine
The core of the tarpit. All meaningful operations pass through a configurable friction layer:
- **Simulated checks** — named subsystem validations with realistic delays
- **Audit forwarding** — events forwarded to named review bodies (FACM, PEAD, PECU, etc.) with accumulating pending review counts
- **Operational mandate checks** — arbitrary lockout rules (prime minute Tuesdays, audit backlog thresholds, random spot-checks)
- **Circular verification** — unknown commands trigger multi-cycle verification loops that always end in accusation
- **Intent verification** — high-risk commands require typed confirmation phrases, re-authentication, and justification codes

### Hidden Operator Channel
SSH key authentication bypasses the tarpit entirely and spawns a real PTY shell on the host. Operator keys are loaded from a configurable `authorized_keys` file. A console magic string (optional) provides the same bypass via password for local access.

### Session Logging
Every session is recorded:
- Full keystroke and output transcripts written to JSONL per session
- Credential detection heuristic flags potential passwords and keys
- Session summaries with full command history written to an intelligence log on disconnect

---

## Setup

### Requirements

```bash
pip3 install -r requirements.txt
```

Dependencies: `paramiko`, `pyyaml`, `jinja2`, `cryptography`

### Run

```bash
python3 main.py
```

On first run, an RSA host key is generated at `kafka_host_rsa`. The SSH server listens on port 22 by default (requires root, or change the port in config).

```bash
# Custom config or profile
python3 main.py --config config/default.yaml --profile webserver
```

### Operator Access

Generate a key pair for operator access:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/kafka_operator
```

Add the public key to your operator authorized keys file (configured in `default.yaml`):

```bash
cat ~/.ssh/kafka_operator.pub >> ~/.ssh/kafka_operator_authorized_keys
```

Operator connections bypass the tarpit:

```bash
ssh -i ~/.ssh/kafka_operator user@target
```

---

## Configuration

### `config/default.yaml`

```yaml
profile: workstation       # which machine persona to load

bureaucracy:
  friction_level: 3        # 1 = believable lag, 5 = pure hell
  download_stall_at: 0.94  # progress bars die here
  compile_fail_at: 0.97    # builds fail here
  sudo_success_chance: 0.0 # probability sudo ever grants access

endpoints:
  ssh:
    enabled: true
    port: 22
    banner: "OpenSSH_8.9p1 Ubuntu-3ubuntu0.6, OpenSSL 3.0.2 15 Mar 2022"

operator:
  authorized_keys_file: ~/.ssh/kafka_operator_authorized_keys
  console_magic: ""        # optional password-based bypass for local console
  real_shell: /bin/bash

logging:
  session_dir: /var/log/kafka-os/sessions
  intelligence_log: /var/log/kafka-os/intelligence.jsonl
```

### Profiles

Profiles live in `config/profiles/`. Each defines the machine's identity, hardware, network, users, running processes, and filesystem layout.

| Profile | Persona |
|---|---|
| `workstation.yaml` | Developer workstation with Docker, VS Code, Python API project |
| `webserver.yaml` | Production nginx/PHP web server with WordPress and deployment user |

To add a profile, copy an existing one and adjust the fields. The VFS generator builds the filesystem from the profile automatically.

---

## Logs

Sessions are written to the configured `session_dir` as JSONL files named `{session_id}_{username}_{ip}.jsonl`. Each file contains timestamped input, output, and event records for the full session.

The intelligence log at `intelligence_log` aggregates potential credentials and per-session command summaries across all sessions.

```bash
# Watch live sessions
tail -f /var/log/kafka-os/intelligence.jsonl | python3 -m json.tool

# Review a session
cat /var/log/kafka-os/sessions/*.jsonl | python3 -m json.tool
```

---

## Architecture

```
main.py                    Entry point — loads config, builds VFS, starts endpoints
config/
  default.yaml             Master configuration
  profiles/                Machine identity profiles
vfs/
  tree.py                  In-memory virtual filesystem
  generator.py             Builds VFS from profile (users, files, history, credentials)
shell/
  interpreter.py           Bash-like shell loop, command dispatch, session state
  commands/
    filesystem.py          ls, cat, find, grep, cp, mv, rm, chmod, head, tail
    system.py              ps, df, free, uname, uptime, who, id, date, history
    network.py             ping, ssh, curl, wget, netstat, ip
    auth.py                sudo, su, passwd
    editors.py             vim, vi, nano
    execution.py           python3, bash, gcc, make, apt, crontab
  bureaucracy/
    engine.py              Delays, checks, forwarding, mandate rules, circular rejection
endpoints/
  ssh.py                   Paramiko SSH server, operator key detection, channel handling
op_shell/
  shell.py                 PTY bridge for real operator shell
logging/
  session.py               Per-session JSONL recording, credential detection, intel log
```
