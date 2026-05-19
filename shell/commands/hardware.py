import datetime
import os
import random


def _hw(session):
    return session.profile.get("hardware", {})


def _identity(session):
    return session.profile.get("identity", {})


def _net(session):
    return session.profile.get("network", {})


def cmd_lscpu(session, args, bure):
    hw = _hw(session)
    identity = _identity(session)
    cores = hw.get("cpu_cores", 4)
    threads = hw.get("cpu_threads", cores * 2)
    sockets = hw.get("cpu_sockets", 1)
    cores_per_socket = cores // sockets
    threads_per_core = threads // cores
    session.write(
        f"Architecture:            {identity.get('arch','x86_64')}\n"
        f"CPU op-mode(s):          32-bit, 64-bit\n"
        f"Address sizes:           39 bits physical, 48 bits virtual\n"
        f"Byte Order:              Little Endian\n"
        f"CPU(s):                  {threads}\n"
        f"On-line CPU(s) list:     0-{threads-1}\n"
        f"Vendor ID:               GenuineIntel\n"
        f"Model name:              {hw.get('cpu_model','Intel(R) CPU')}\n"
        f"CPU family:              6\n"
        f"Model:                   165\n"
        f"Thread(s) per core:      {threads_per_core}\n"
        f"Core(s) per socket:      {cores_per_socket}\n"
        f"Socket(s):               {sockets}\n"
        f"Stepping:                5\n"
        f"CPU max MHz:             {int(hw.get('cpu_model','@ 2.90GHz').split('@')[-1].strip().split('GHz')[0].strip().replace('.','').ljust(4,'0')[:4]) if '@' in hw.get('cpu_model','') else 2900:.1f}\n"
        f"BogoMIPS:                {random.randint(4000,8000)}.00\n"
        f"Caches (sum of all):\n"
        f"  L1d:                   {cores * 32} KiB ({cores} instances)\n"
        f"  L1i:                   {cores * 32} KiB ({cores} instances)\n"
        f"  L2:                    {cores * 256} KiB ({cores} instances)\n"
        f"  L3:                    16 MiB (1 instance)\n"
        f"NUMA node(s):            1\n"
        f"NUMA node0 CPU(s):       0-{threads-1}\n"
        f"Vulnerability Itlb multihit: Not affected\n"
        f"Vulnerability L1tf:      Not affected\n"
        f"Vulnerability Meltdown:  Not affected\n"
        f"Vulnerability Spectre v1: Mitigation; usercopy/swapgs barriers and __user pointer sanitization\n"
        f"Vulnerability Spectre v2: Mitigation; Enhanced IBRS, IBPB conditional, RSB filling\n"
        f"Flags:                   fpu vme de pse tsc msr pae mce cx8 apic sep mtrr pge mca cmov\n"
        f"                         pat pse36 clflush dts acpi mmx fxsr sse sse2 ss ht tm pbe\n"
        f"                         syscall nx pdpe1gb rdtscp lm constant_tsc art arch_perfmon\n"
    )


def cmd_lshw(session, args, bure):
    hw = _hw(session)
    identity = _identity(session)
    net = _net(session)
    bure.log("Hardware enumeration initiated via lshw.")
    bure.simulated_check("Hardware Inventory Scan", "base_check_short_ms")
    session.write(
        f"{identity.get('hostname','host')}\n"
        f"    description: Desktop Computer\n"
        f"    product: {hw.get('product_name','Unknown')}\n"
        f"    vendor: {hw.get('bios_vendor','Unknown')}\n"
        f"    serial: {hw.get('serial_number','N/A')}\n"
        f"    width: 64 bits\n"
        f"  *-core\n"
        f"       description: Motherboard\n"
        f"     *-cpu\n"
        f"          description: CPU\n"
        f"          product: {hw.get('cpu_model','CPU')}\n"
        f"          vendor: Intel Corp.\n"
        f"          physical id: 0\n"
        f"          bus info: cpu@0\n"
        f"          width: 64 bits\n"
        f"          capabilities: fpu fpu_exception wp vme de pse tsc msr pae mce\n"
        f"     *-memory\n"
        f"          description: System Memory\n"
        f"          physical id: 1\n"
        f"          size: {hw.get('ram_gb',8)}GiB\n"
        f"     *-network\n"
        f"          description: Ethernet interface\n"
        f"          physical id: 2\n"
        f"          logical name: {net.get('primary_iface','eth0')}\n"
        f"          serial: {net.get('mac','00:00:00:00:00:00')}\n"
        f"          ip: {net.get('ip','10.0.0.1')}\n"
    )
    for drive in hw.get("drives", []):
        session.write(
            f"     *-disk\n"
            f"          description: ATA Disk\n"
            f"          product: {drive.get('model','Disk')}\n"
            f"          logical name: /dev/{drive.get('dev','sda')}\n"
            f"          size: {drive.get('size_gb',100)}GiB\n"
        )


def cmd_lspci(session, args, bure):
    for dev in _hw(session).get("pci_devices", []):
        session.write(dev + "\n")


def cmd_lsusb(session, args, bure):
    for dev in _hw(session).get("usb_devices", []):
        session.write(dev + "\n")


def cmd_lsblk(session, args, bure):
    long_fmt = "-f" in args or "--fs" in args
    session.write(
        f"{'NAME':<12} {'MAJ:MIN':<8} {'RM':>3} {'SIZE':>6} {'RO':>3} {'TYPE':<6} "
        f"{'MOUNTPOINT'}\n"
    )
    for drive in _hw(session).get("drives", []):
        dev = drive.get("dev", "sda")
        size = drive.get("size_gb", 100)
        session.write(
            f"{dev:<12} {'8:0':<8} {'0':>3} {str(size)+'G':>6} {'0':>3} {'disk':<6}\n"
        )
        for part in drive.get("partitions", []):
            pname = f"{dev}{part['num']}"
            psize = part.get("size_gb", 1)
            mount = part.get("mount", "")
            session.write(
                f"{'└─'+pname:<12} {'8:1':<8} {'0':>3} {str(psize)+'G':>6} {'0':>3} "
                f"{'part':<6} {mount}\n"
            )


def cmd_fdisk(session, args, bure):
    if "-l" not in args:
        session.write("fdisk: requires -l flag for listing\n")
        return
    bure.log("FACM: Partition table enumeration requested.")
    for drive in _hw(session).get("drives", []):
        dev = drive.get("dev", "sda")
        size = drive.get("size_gb", 100)
        model = drive.get("model", "Disk")
        session.write(
            f"Disk /dev/{dev}: {size} GiB, {size * 1073741824} bytes, "
            f"{size * 1953125} sectors\n"
            f"Disk model: {model}\n"
            f"Units: sectors of 1 * 512 = 512 bytes\n"
            f"Sector size (logical/physical): 512 bytes / 512 bytes\n"
            f"I/O size (minimum/optimal): 512 bytes / 512 bytes\n"
            f"Disklabel type: gpt\n\n"
            f"{'Device':<20} {'Start':>12} {'End':>12} {'Sectors':>12} {'Size':>6} {'Type'}\n"
        )
        start = 2048
        for part in drive.get("partitions", []):
            sectors = part.get("size_gb", 1) * 1953125
            end = start + sectors - 1
            ptype = "EFI System" if part.get("fs") == "vfat" else "Linux filesystem"
            session.write(
                f"/dev/{dev}{part['num']:<17} {start:>12} {end:>12} "
                f"{sectors:>12} {str(part.get('size_gb',1))+'G':>6} {ptype}\n"
            )
            start = end + 1
        session.write("\n")


def cmd_dmidecode(session, args, bure):
    hw = _hw(session)
    identity = _identity(session)
    bure.log("FACM: DMI/BIOS data requested via dmidecode.")
    bure.simulated_check("DMI Table Read", "base_check_short_ms")
    session.write(
        f"# dmidecode 3.3\n"
        f"Getting SMBIOS data from sysfs.\n"
        f"SMBIOS 3.1.1 present.\n\n"
        f"Handle 0x0000, DMI type 0, 26 bytes\n"
        f"BIOS Information\n"
        f"\tVendor: {hw.get('bios_vendor','Unknown')}\n"
        f"\tVersion: {hw.get('bios_version','1.0')}\n"
        f"\tRelease Date: {hw.get('bios_date','01/01/2020')}\n"
        f"\tROMSize: 32 MB\n\n"
        f"Handle 0x0001, DMI type 1, 27 bytes\n"
        f"System Information\n"
        f"\tManufacturer: {hw.get('bios_vendor','Unknown')}\n"
        f"\tProduct Name: {hw.get('product_name','Unknown')}\n"
        f"\tVersion: Not Specified\n"
        f"\tSerial Number: {hw.get('serial_number','N/A')}\n"
        f"\tUUID: {__import__('uuid').uuid4()}\n"
        f"\tWake-up Type: Power Switch\n\n"
        f"Handle 0x0004, DMI type 4, 48 bytes\n"
        f"Processor Information\n"
        f"\tSocket Designation: CPU0\n"
        f"\tType: Central Processor\n"
        f"\tVersion: {hw.get('cpu_model','CPU')}\n"
        f"\tCore Count: {hw.get('cpu_cores',4)}\n"
        f"\tThread Count: {hw.get('cpu_threads', hw.get('cpu_cores',4)*2)}\n"
    )


def cmd_smartctl(session, args, bure):
    hw = _hw(session)
    drives = hw.get("drives", [{"dev": "sda", "model": "Disk", "size_gb": 100}])
    dev_arg = next((a for a in args if "sd" in a or "nvme" in a), f"/dev/{drives[0]['dev']}")
    dev_name = dev_arg.replace("/dev/", "")
    drive = next((d for d in drives if d.get("dev") == dev_name), drives[0])
    bure.log(f"FACM: SMART data requested for {dev_arg}.")
    bure.simulated_check("SMART Attribute Read", "base_check_short_ms")
    hours = random.randint(2000, 20000)
    session.write(
        f"smartctl 7.2 2020-12-30 r5155 [x86_64-linux-5.15.0] (local build)\n"
        f"=== START OF INFORMATION SECTION ===\n"
        f"Device Model:     {drive.get('model','Disk')}\n"
        f"Serial Number:    {__import__('uuid').uuid4().hex[:12].upper()}\n"
        f"Firmware Version: SVT01B6Q\n"
        f"User Capacity:    {drive.get('size_gb',100) * 1_000_000_000} bytes [{drive.get('size_gb',100)} GB]\n"
        f"Sector Size:      512 bytes logical/physical\n"
        f"Rotation Rate:    {'Solid State Device' if drive.get('rpm',0)==0 else str(drive.get('rpm',7200))+' rpm'}\n"
        f"SMART support is: Available - device has SMART capability.\n"
        f"SMART support is: Enabled\n\n"
        f"=== START OF READ SMART DATA SECTION ===\n"
        f"SMART overall-health self-assessment test result: PASSED\n\n"
        f"ID# ATTRIBUTE_NAME          FLAG     VALUE WORST THRESH TYPE      UPDATED  WHEN_FAILED RAW_VALUE\n"
        f"  5 Reallocated_Sector_Ct   0x0033   100   100   010    Pre-fail  Always       -       0\n"
        f"  9 Power_On_Hours           0x0032   099   099   000    Old_age   Always       -       {hours}\n"
        f" 12 Power_Cycle_Count        0x0032   099   099   000    Old_age   Always       -       {random.randint(50,500)}\n"
        f"190 Airflow_Temperature_Cel  0x0022   068   055   045    Old_age   Always       -       32\n"
        f"194 Temperature_Celsius      0x0011   032   045   000    Old_age   Always       -       32\n"
        f"197 Current_Pending_Sector   0x0012   100   100   000    Old_age   Always       -       0\n"
        f"198 Offline_Uncorrectable    0x0010   100   100   000    Old_age   Offline      -       0\n"
    )


def cmd_hdparm(session, args, bure):
    hw = _hw(session)
    drives = hw.get("drives", [{"dev": "sda"}])
    dev_arg = next((a for a in args if "sd" in a), f"/dev/{drives[0].get('dev','sda')}")
    bure.log(f"FACM: hdparm query on {dev_arg}.")
    bure.simulated_check("Drive Parameter Read", "base_check_short_ms")
    mbps = random.randint(400, 560)
    session.write(
        f"\n{dev_arg}:\n"
        f" Timing cached reads:   {random.randint(10000,20000)} MB in  2.00 seconds = {random.randint(5000,10000):.2f} MB/sec\n"
        f" Timing buffered disk reads: {random.randint(800,1600)} MB in  3.00 seconds = {mbps:.2f} MB/sec\n"
    )


def cmd_mount(session, args, bure):
    net = _net(session)
    iface = net.get("primary_iface", "eth0")
    session.write(
        f"sysfs on /sys type sysfs (rw,nosuid,nodev,noexec,relatime)\n"
        f"proc on /proc type proc (rw,nosuid,nodev,noexec,relatime)\n"
        f"udev on /dev type devtmpfs (rw,nosuid,relatime,size=8192k,nr_inodes=4096,mode=755)\n"
        f"tmpfs on /run type tmpfs (rw,nosuid,nodev,noexec,relatime,size=1633728k,mode=755)\n"
        f"/dev/sda2 on / type ext4 (rw,relatime)\n"
        f"/dev/sda1 on /boot/efi type vfat (rw,relatime,fmask=0077,dmask=0077)\n"
        f"tmpfs on /dev/shm type tmpfs (rw,nosuid,nodev)\n"
        f"tmpfs on /run/lock type tmpfs (rw,nosuid,nodev,noexec,relatime,size=5120k)\n"
        f"tmpfs on /run/user/1000 type tmpfs (rw,nosuid,nodev,relatime,size=1633724k,mode=700)\n"
    )


def cmd_du(session, args, bure):
    paths = [a for a in args if not a.startswith("-")]
    target = paths[0] if paths else session.cwd
    if not target.startswith("/"):
        import os as _os
        target = _os.path.normpath(session.cwd + "/" + target)
    summarize = "-s" in args or "--summarize" in args
    bure.log(f"FACM: Disk usage scan on '{target}'.")
    total = random.randint(1000, 500000)
    if summarize:
        session.write(f"{total}\t{target}\n")
    else:
        node = session.vfs.get_node(target)
        if node and node.is_dir:
            children = session.vfs.listdir(target) or {}
            for name in sorted(children.keys()):
                size = random.randint(4, total // max(len(children), 1))
                session.write(f"{size}\t{target}/{name}\n")
        session.write(f"{total}\t{target}\n")


def cmd_dmesg(session, args, bure):
    hw = _hw(session)
    identity = _identity(session)
    kernel = identity.get("kernel", "5.15.0-91-generic").split()[0]
    session.write(
        f"[    0.000000] Booting Linux on physical CPU 0x0000000000 [0x000806ea]\n"
        f"[    0.000000] Linux version {kernel} (buildd@ubuntu) (gcc version 11.4.0) #1 SMP\n"
        f"[    0.000000] Command line: BOOT_IMAGE=/vmlinuz-{kernel} root=/dev/sda2 ro quiet splash\n"
        f"[    0.000000] BIOS-provided physical RAM map:\n"
        f"[    0.000000] ACPI: BIOS IRQ0 pin2 override\n"
        f"[    0.152731] ACPI: IRQ0 used by override.\n"
        f"[    0.388914] pci 0000:00:02.0: vgaarb: setting as boot VGA device\n"
        f"[    1.204482] EXT4-fs (sda2): mounted filesystem with ordered data mode.\n"
        f"[    2.918847] systemd[1]: systemd {__import__('random').randint(249,255)} running in system mode.\n"
        f"[    3.441209] NET: Registered PF_INET6 protocol family\n"
        f"[    4.002341] audit: type=1400 audit(1.000:2): apparmor=\"STATUS\" operation=\"profile_load\"\n"
    )
