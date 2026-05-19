import random
import time

from shell.commands import attacker_tools


def cmd_ping(session, args, bure):
    if not args:
        session.write("ping: missing host\n")
        return
    host = [a for a in args if not a.startswith("-")]
    host = host[0] if host else "unknown"
    count_flag = next((args[i+1] for i, a in enumerate(args)
                       if a == "-c" and i+1 < len(args)), None)
    count = int(count_flag) if count_flag and count_flag.isdigit() else 4

    bure.log(f"NASL: ICMP packet emission to '{host}' requires egress authorization.")
    bure.simulated_check("ICMP Egress Policy Check", "base_check_short_ms")

    session.write(f"PING {host}: 56 data bytes\n")
    for i in range(count):
        time.sleep(1)
        rtt = round(random.uniform(80, 400), 3)
        session.write(f"64 bytes from {host}: icmp_seq={i} ttl=54 time={rtt} ms\n")

    # Always end with partial packet loss
    loss = random.choice([25, 50, 75])
    session.write(f"--- {host} ping statistics ---\n")
    session.write(f"{count} packets transmitted, {count * (100-loss)//100} received, "
                  f"{loss}% packet loss\n")
    if loss > 0:
        bure.log(f"NASL: Packet loss detected — network anomaly report filed "
                 f"(Ref: NASL-{bure._short_ref()[:6]}).", level="WARN")


def cmd_ssh(session, args, bure):
    targets = [a for a in args if not a.startswith("-")]
    if not targets:
        session.write("usage: ssh [user@]host\n")
        return

    target = targets[0]
    if "@" in target:
        remote_user, remote_host = target.split("@", 1)
    else:
        remote_user, remote_host = session.username, target

    topology = session.profile.get("filesystem", {}).get("network_topology", [])
    known = next((h for h in topology
                  if h.get("host") == remote_host or h.get("hostname") == remote_host), None)

    bure.log(f"NASL: Outbound SSH connection to '{remote_host}' as '{remote_user}' requested.")
    bure.simulated_check("SSH Egress Authorization Check", "base_check_medium_ms")
    bure.forward('NETWORK', f"ssh:{remote_user}@{remote_host}", "Outbound SSH Attempt")

    session.write(f"ssh: connect to host {remote_host} port 22: ")
    time.sleep(random.uniform(2, 4))

    if known:
        session.write(f"Connection established.\r\n")
        bure.log(f"NASL: SSH tunnel to {remote_host} active. Session nested.", level="INFO")
        # Nested tarpit — same experience, different hostname
        bure.log(f"Applying remote session policy for {remote_host}...", level="INFO")
        bure.simulated_check("Remote Session Policy Application", "base_check_medium_ms")
        identity = session.profile.get("identity", {})
        session.write(f"Welcome to {known.get('hostname', remote_host)}.\r\n")
        session.write(f"Last login: {_fake_last_login()} from {session.remote_ip}\r\n\r\n")
        # Drop back — session continues with same bureaucracy, just logged as nested
        session._nested_host = known.get("hostname", remote_host)
    else:
        session.write(f"Connection timed out\n")
        bure.log(f"NASL: Connection to '{remote_host}' failed — host not in approved "
                 f"egress list. Routing blocked.", level="ERROR")


def _fake_last_login():
    import datetime
    import random
    days_ago = random.randint(1, 30)
    dt = datetime.datetime.now() - datetime.timedelta(days=days_ago)
    return dt.strftime("%a %b %d %H:%M:%S %Y")


def cmd_scp(session, args, bure):
    bure.log("NASL: Secure copy operation initiated.")
    bure.network_stall(session, "remote-host", "SCP")


def cmd_curl(session, args, bure):
    urls = [a for a in args if not a.startswith("-") and ("http" in a or "/" in a)]
    url = urls[0] if urls else "unknown"
    filename = url.rsplit("/", 1)[-1] or "index.html"
    bure.log(f"NASL: HTTP request to '{url}' via curl.")
    attacker_tools.fake_download(session, bure, url, filename)


def cmd_wget(session, args, bure):
    urls = [a for a in args if not a.startswith("-") and "http" in a]
    url = urls[0] if urls else "unknown"
    filename = url.rsplit("/", 1)[-1] or "index.html"
    bure.log(f"NASL: HTTP download '{url}' via wget.")
    import datetime
    session.write(f"--{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}--  {url}\n")
    attacker_tools.fake_download(session, bure, url, filename)


def cmd_netstat(session, args, bure):
    identity = session.profile.get("identity", {})
    ip = identity.get("network", {}).get("ip", "10.0.0.1") if "network" in identity else \
         session.profile.get("network", {}).get("ip", "10.0.0.1")
    session.write(
        f"Active Internet connections (servers and established)\n"
        f"Proto Recv-Q Send-Q Local Address           Foreign Address         State\n"
        f"tcp        0      0 0.0.0.0:22              0.0.0.0:*               LISTEN\n"
        f"tcp        0      0 {ip}:22          {session.remote_ip}:{random.randint(49152,65535)}     ESTABLISHED\n"
        f"tcp6       0      0 :::80                   :::*                    LISTEN\n"
    )


def cmd_ss(session, args, bure):
    cmd_netstat(session, args, bure)


def cmd_ip(session, args, bure):
    if not args or args[0] not in ("addr", "a", "link", "route", "r"):
        session.write("ip: missing subcommand\n")
        return
    net = session.profile.get("network", {})
    iface = net.get("primary_iface", "eth0")
    ip = net.get("ip", "10.0.0.1")
    mac = net.get("mac", "00:00:00:00:00:00")
    netmask = net.get("netmask", "255.255.255.0")
    session.write(
        f"1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN\n"
        f"    link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00\n"
        f"    inet 127.0.0.1/8 scope host lo\n"
        f"2: {iface}: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc fq_codel state UP\n"
        f"    link/ether {mac} brd ff:ff:ff:ff:ff:ff\n"
        f"    inet {ip}/24 brd {ip.rsplit('.',1)[0]}.255 scope global dynamic {iface}\n"
    )


def cmd_ifconfig(session, args, bure):
    cmd_ip(session, ["addr"], bure)
