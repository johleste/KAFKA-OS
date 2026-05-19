import datetime
import random
import time


def cmd_uname(session, args, bure):
    identity = session.profile.get("identity", {})
    flags = set("".join(a.lstrip("-") for a in args if a.startswith("-")))
    if "a" in flags:
        session.write(
            f"Linux {identity.get('hostname','host')} "
            f"{identity.get('kernel','5.15.0-generic')} "
            f"#{random.randint(1,200)}-Ubuntu SMP "
            f"{identity.get('arch','x86_64')} GNU/Linux\n"
        )
    elif "r" in flags:
        kernel = identity.get("kernel", "5.15.0-91-generic").split()[0]
        session.write(kernel + "\n")
    else:
        session.write("Linux\n")


def cmd_uptime(session, args, bure):
    identity = session.profile.get("identity", {})
    days_range = identity.get("uptime_days_range", [1, 30])
    days = random.randint(*days_range)
    hours = random.randint(0, 23)
    mins = random.randint(0, 59)
    users = random.randint(1, 3)
    load = [round(random.uniform(0.1, 2.0), 2) for _ in range(3)]
    now = datetime.datetime.now().strftime("%H:%M:%S")
    session.write(
        f" {now} up {days} days, {hours:02d}:{mins:02d}, "
        f"{users} user{'s' if users != 1 else ''}, "
        f"load average: {load[0]}, {load[1]}, {load[2]}\n"
    )


def cmd_df(session, args, bure):
    hw = session.profile.get("hardware", {})
    disk_gb = hw.get("disk_gb", 256)
    used_gb = round(disk_gb * random.uniform(0.35, 0.72), 1)
    avail_gb = round(disk_gb - used_gb, 1)
    pct = int((used_gb / disk_gb) * 100)
    session.write(
        f"Filesystem      Size  Used Avail Use% Mounted on\n"
        f"/dev/sda1       {disk_gb}G  {used_gb}G  {avail_gb}G  {pct}% /\n"
        f"tmpfs           {hw.get('ram_gb',16) // 2}G     0  {hw.get('ram_gb',16) // 2}G   0% /dev/shm\n"
        f"tmpfs           1.6G  1.4M  1.6G   1% /run\n"
    )


def cmd_free(session, args, bure):
    meminfo = session.vfs.read("/proc/meminfo")
    if meminfo:
        vals = {}
        for line in meminfo.splitlines():
            if ":" in line:
                key, val = line.split(":", 1)
                try:
                    vals[key.strip()] = int(val.strip().split()[0])
                except (ValueError, IndexError):
                    pass
        total = vals.get("MemTotal", 16 * 1024 * 1024) // 1024
        free = vals.get("MemFree", total // 2) // 1024
        avail = vals.get("MemAvailable", free) // 1024
        cached = vals.get("Cached", 0) // 1024
        buffers = vals.get("Buffers", 0) // 1024
        used = total - free - cached - buffers
        shared = random.randint(50, 300)
        swap_total = vals.get("SwapTotal", total // 2) // 1024
        swap_free = vals.get("SwapFree", swap_total) // 1024
    else:
        hw = session.profile.get("hardware", {})
        total = hw.get("ram_gb", 16) * 1024
        used = int(total * random.uniform(0.4, 0.75))
        free = total - used
        shared = random.randint(50, 300)
        cached = random.randint(500, 2000)
        avail = free + cached
        swap_total = total // 2
        swap_free = swap_total
    suffix = ""
    if "-h" in args:
        suffix = " (human readable not implemented)"
    session.write(
        f"               total        used        free      shared  buff/cache   available\n"
        f"Mem:        {total:>9}    {used:>9}    {free:>9}    {shared:>9}    {cached:>9}    {avail:>9}\n"
        f"Swap:       {swap_total:>9}           0    {swap_free:>9}\n"
    )


def cmd_ps(session, args, bure):
    procs = session.profile.get("processes", [])
    flags = " ".join(args)
    session.write(
        f"{'USER':<12} {'PID':>6} {'%CPU':>5} {'%MEM':>5} {'COMMAND'}\n"
    )
    for p in procs:
        session.write(
            f"{p.get('user','root'):<12} {p.get('pid',1):>6} "
            f"{p.get('cpu',0.0):>5.1f} {p.get('mem',0.0):>5.1f} "
            f"{p.get('cmd', p.get('name',''))}\n"
        )


def cmd_top(session, args, bure):
    cmd_uptime(session, [], bure)
    session.write(f"Tasks: {random.randint(140,200)} total, 1 running, "
                  f"{random.randint(139,199)} sleeping\n")
    session.write(f"%Cpu(s): {random.uniform(1,15):.1f} us, {random.uniform(0,3):.1f} sy\n")
    cmd_free(session, [], bure)
    session.write("\n")
    cmd_ps(session, [], bure)


def cmd_who(session, args, bure):
    identity = session.profile.get("identity", {})
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    session.write(f"{session.username}   pts/0        {now} ({session.remote_ip})\n")


def cmd_w(session, args, bure):
    cmd_uptime(session, [], bure)
    session.write(f"{'USER':<10} TTY      {'FROM':<20} LOGIN@  IDLE JCPU PCPU WHAT\n")
    now = datetime.datetime.now().strftime("%H:%M")
    session.write(f"{session.username:<10} pts/0    {session.remote_ip:<20} {now}   0.00s 0.01s 0.00s -bash\n")


def cmd_id(session, args, bure):
    users = session.profile.get("users", [])
    user = next((u for u in users if u["username"] == session.username), None)
    if user:
        uid = user.get("uid", 1000)
        gid = user.get("gid", 1000)
        groups_str = f"{gid}({user['username']})"
        for g in user.get("groups", []):
            gid_extra = random.randint(1001, 1099)
            groups_str += f",{gid_extra}({g})"
        session.write(f"uid={uid}({user['username']}) gid={gid}({user['username']}) "
                      f"groups={groups_str}\n")
    else:
        session.write(f"uid=1000({session.username}) gid=1000({session.username}) "
                      f"groups=1000({session.username})\n")


def cmd_whoami(session, args, bure):
    session.write(session.username + "\n")


def cmd_hostname(session, args, bure):
    identity = session.profile.get("identity", {})
    session.write(identity.get("hostname", "localhost") + "\n")


def cmd_env(session, args, bure):
    identity = session.profile.get("identity", {})
    session.write(
        f"USER={session.username}\n"
        f"HOME={session.home}\n"
        f"SHELL=/bin/bash\n"
        f"PWD={session.cwd}\n"
        f"HOSTNAME={identity.get('hostname','localhost')}\n"
        f"TERM=xterm-256color\n"
        f"PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin\n"
        f"LANG=en_US.UTF-8\n"
    )


def cmd_date(session, args, bure):
    session.write(datetime.datetime.now().strftime("%a %b %d %H:%M:%S %Z %Y") + "\n")


def cmd_history(session, args, bure):
    for i, cmd in enumerate(session.history[-50:], 1):
        session.write(f"  {i:>4}  {cmd}\n")


def cmd_exit(session, args, bure):
    bure.log("Session termination requested by user.")
    bure.simulated_check("Session Teardown & Audit Log Flush", "base_check_short_ms")
    bure.forward('SHUTDOWN', "user-exit", "Session Exit Event")
    session.write("logout\n")
    raise SystemExit(0)


def cmd_clear(session, args, bure):
    session.write("\033[2J\033[H")


def cmd_echo(session, args, bure):
    session.write(" ".join(args) + "\n")
