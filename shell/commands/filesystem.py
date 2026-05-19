import datetime
import os
import random
import time


def _fmt_size(n):
    for unit in ["", "K", "M", "G"]:
        if n < 1024:
            return f"{n:.0f}{unit}" if unit else f"{n}"
        n /= 1024
    return f"{n:.1f}T"


def _ls_row(name, node, long_fmt=False):
    if long_fmt:
        mtime = datetime.datetime.fromtimestamp(node.mtime).strftime("%b %d %H:%M")
        return (f"{node.mode_str()} 1 {node.owner:<10} {node.group:<10} "
                f"{node.size():>8} {mtime} {name}")
    return name


def cmd_ls(session, args, bure):
    flags = set()
    paths = []
    for a in args:
        if a.startswith("-"):
            flags.update(a[1:])
        else:
            paths.append(a)

    target = paths[0] if paths else session.cwd
    if not target.startswith("/"):
        target = os.path.normpath(session.cwd + "/" + target)

    if not bure.check_mandate("FILESYSTEM"):
        return

    node = session.vfs.get_node(target)
    if node is None:
        session.write(f"ls: cannot access '{target}': No such file or directory\n")
        return

    long_fmt = "l" in flags
    show_hidden = "a" in flags

    if node.is_dir:
        children = session.vfs.listdir(target)
        entries = sorted(children.keys())
        if show_hidden:
            entries = [".", ".."] + entries
        else:
            entries = [e for e in entries if not e.startswith(".")]

        if long_fmt:
            session.write(f"total {len(entries) * 8}\n")
            for name in entries:
                child = children[name] if name not in (".", "..") else node
                session.write(_ls_row(name, child, long_fmt=True) + "\n")
        else:
            session.write("  ".join(entries) + "\n")
    else:
        session.write(_ls_row(target.rsplit("/", 1)[-1], node, long_fmt=long_fmt) + "\n")


def cmd_cd(session, args, bure):
    target = args[0] if args else session.home
    if target == "~":
        target = session.home
    if not target.startswith("/"):
        target = os.path.normpath(session.cwd + "/" + target)
    target = os.path.normpath(target)

    if not session.vfs.exists(target):
        session.write(f"bash: cd: {target}: No such file or directory\n")
        return
    if not session.vfs.is_dir(target):
        session.write(f"bash: cd: {target}: Not a directory\n")
        return
    session.cwd = target


def cmd_pwd(session, args, bure):
    session.write(session.cwd + "\n")


def cmd_cat(session, args, bure):
    if not args:
        session.write("cat: missing operand\n")
        return

    for path in args:
        if not path.startswith("/"):
            path = os.path.normpath(session.cwd + "/" + path)

        sensitive = session.profile.get("filesystem", {}).get("sensitive_paths", [])
        if path in sensitive:
            bure.log(f"FACM: File access request for '{path}' — elevated sensitivity detected.")
            bure.simulated_check("ACL Validation & Sensitivity Assessment", "base_check_medium_ms")
            bure.forward('FS_ACCESS', f"cat:{path}", "Sensitive File Access Attempt")
            bure.log(f"FACM: SECURITY HOLD placed on '{path}'. "
                     f"Access forwarded to Filesystem Access Control Monitor.", level="WARN")
            bure.log(f"FACM: Estimated clearance processing time: 2-5 business days.", level="WARN")
            ref = bure._short_ref()
            session.write(f"\ncat: {path}: Operation not permitted — FACM Security Hold "
                          f"(Ref: FACM-{ref})\n")
            session.write(f"File access has been logged. Contact your administrator to request clearance.\n\n")
            return

        content = session.vfs.read(path)
        if content is None:
            if session.vfs.is_dir(path):
                session.write(f"cat: {path}: Is a directory\n")
            else:
                session.write(f"cat: {path}: No such file or directory\n")
            return

        # Partial read then stall for "interesting" files
        interesting = session.profile.get("filesystem", {}).get("interesting_paths", [])
        if path in interesting and len(content) > 200:
            lines = content.splitlines()
            preview = lines[:min(5, len(lines))]
            for line in preview:
                session.write(line + "\n")
                time.sleep(0.1)
            bure.log(f"FACM: Content stream for '{path}' flagged for compliance review.")
            bure.simulated_check("Content Compliance Scan", "base_check_medium_ms")
            bure.log(f"FACM: Output stream suspended pending audit completion.", level="WARN")
            session.write(f"\n... output suspended — content audit in progress (Ref: FACM-{bure._short_ref()}) ...\n\n")
        else:
            session.write(content)


def cmd_find(session, args, bure):
    if not args:
        args = [session.cwd]

    start = args[0] if args[0].startswith("/") else os.path.normpath(session.cwd + "/" + args[0])

    bure.log(f"FACM: Recursive directory scan initiated from '{start}'.")
    bure.simulated_check("Filesystem Traversal Authorization", "base_check_short_ms")

    def _walk(path, depth=0):
        if depth > 8:
            return
        node = session.vfs.get_node(path)
        if node is None:
            return
        yield path
        if node.is_dir:
            children = session.vfs.listdir(path)
            for name, child in sorted(children.items()):
                yield from _walk(path.rstrip("/") + "/" + name, depth + 1)

    name_filter = None
    for i, a in enumerate(args):
        if a == "-name" and i + 1 < len(args):
            name_filter = args[i + 1].replace("*", "")

    results = []
    for p in _walk(start):
        if name_filter is None or name_filter.lower() in p.lower():
            results.append(p)
        time.sleep(0.02)

    for r in results:
        session.write(r + "\n")


def cmd_grep(session, args, bure):
    if len(args) < 2:
        session.write("Usage: grep PATTERN FILE...\n")
        return

    pattern = args[0].lower()
    for path in args[1:]:
        if not path.startswith("/"):
            path = os.path.normpath(session.cwd + "/" + path)
        content = session.vfs.read(path)
        if content is None:
            session.write(f"grep: {path}: No such file or directory\n")
            continue
        for line in content.splitlines():
            if pattern in line.lower():
                session.write(line + "\n")


def cmd_mkdir(session, args, bure):
    if not args:
        session.write("mkdir: missing operand\n")
        return
    for path in args:
        if not path.startswith("/"):
            path = os.path.normpath(session.cwd + "/" + path)
        bure.log(f"FACM: Directory creation request for '{path}'. Validating ACL...")
        bure.simulated_check("Write ACL Verification", "base_check_short_ms")
        # Appears to succeed
        session.vfs.makedirs(path, owner=session.username)
        bure.forward('FS_WRITE', f"mkdir:{path}", "Directory Creation Event")
        session.write(f"mkdir: created directory '{path}'\n")


def cmd_rm(session, args, bure):
    if not args:
        session.write("rm: missing operand\n")
        return
    flags = [a for a in args if a.startswith("-")]
    paths = [a for a in args if not a.startswith("-")]
    for path in paths:
        if not path.startswith("/"):
            path = os.path.normpath(session.cwd + "/" + path)
        bure.log(f"FACM: Deletion request for '{path}'. Initiating Irreversibility Review.")
        bure.simulated_check("Irreversible Operation Risk Assessment", "base_check_long_ms")
        bure.forward('FS_WRITE', f"rm:{path}", "File Deletion Attempt")
        bure.log(f"FACM: Deletion of '{path}' queued for approval by Write Operation "
                 f"Integrity Daemon. ETA: 3-7 business days.", level="WARN")
        session.write(f"rm: cannot remove '{path}': Operation pending WOID approval "
                      f"(Ref: WOID-{bure._short_ref()})\n")


def cmd_cp(session, args, bure):
    if len(args) < 2:
        session.write("cp: missing file operand\n")
        return
    src, dst = args[0], args[-1]
    bure.log(f"FACM: Copy operation '{src}' → '{dst}'. Validating...")
    bure.simulated_check("Copy Operation ACL Check", "base_check_medium_ms")
    bure.forward('FS_WRITE', f"cp:{src}:{dst}", "File Copy Event")
    session.write(f"cp: cannot create regular file '{dst}': "
                  f"Write quota pending allocation (Ref: WQ-{bure._short_ref()})\n")


def cmd_mv(session, args, bure):
    if len(args) < 2:
        session.write("mv: missing file operand\n")
        return
    src, dst = args[0], args[-1]
    bure.log(f"FACM: Move/rename '{src}' → '{dst}'.")
    bure.simulated_check("Move Operation Conflict Detection", "base_check_medium_ms")
    bure.forward('FS_WRITE', f"mv:{src}:{dst}", "File Move Event")
    session.write(f"mv: cannot move '{src}' to '{dst}': "
                  f"Namespace lock held by Audit Process (Ref: NL-{bure._short_ref()})\n")


def cmd_chmod(session, args, bure):
    if len(args) < 2:
        session.write("chmod: missing operand\n")
        return
    mode, path = args[0], args[1]
    bure.log(f"FACM: Permission change request on '{path}' to {mode}.")
    bure.simulated_check("Permission Change Audit", "base_check_short_ms")
    # Silently succeed (but change nothing)
    bure.forward('FS_WRITE', f"chmod:{mode}:{path}", "Permission Change Event")
    # No output — looks like it worked


def cmd_chown(session, args, bure):
    if len(args) < 2:
        session.write("chown: missing operand\n")
        return
    owner, path = args[0], args[1]
    bure.log(f"FACM: Ownership change '{path}' to '{owner}'.")
    bure.simulated_check("Ownership Transfer Authorization", "base_check_medium_ms")
    bure.forward('FS_WRITE', f"chown:{owner}:{path}", "Ownership Change Event")
    session.write(f"chown: changing ownership of '{path}': Operation not permitted\n")


def cmd_head(session, args, bure):
    if not args:
        session.write("head: missing operand\n")
        return
    n = 10
    paths = []
    i = 0
    while i < len(args):
        if args[i] in ("-n",) and i + 1 < len(args):
            try:
                n = int(args[i + 1])
            except ValueError:
                pass
            i += 2
        else:
            paths.append(args[i])
            i += 1
    for path in paths:
        if not path.startswith("/"):
            path = os.path.normpath(session.cwd + "/" + path)
        content = session.vfs.read(path)
        if content is None:
            session.write(f"head: cannot open '{path}': No such file or directory\n")
            continue
        for line in content.splitlines()[:n]:
            session.write(line + "\n")


def cmd_tail(session, args, bure):
    if not args:
        session.write("tail: missing operand\n")
        return
    n = 10
    follow = False
    paths = []
    i = 0
    while i < len(args):
        if args[i] in ("-n",) and i + 1 < len(args):
            try:
                n = int(args[i + 1])
            except ValueError:
                pass
            i += 2
        elif args[i] == "-f":
            follow = True
            i += 1
        else:
            paths.append(args[i])
            i += 1
    for path in paths:
        if not path.startswith("/"):
            path = os.path.normpath(session.cwd + "/" + path)
        content = session.vfs.read(path)
        if content is None:
            session.write(f"tail: cannot open '{path}': No such file or directory\n")
            continue
        lines = content.splitlines()
        for line in lines[-n:]:
            session.write(line + "\n")
        if follow:
            bure.log(f"FACM: tail -f on '{path}' — real-time monitoring requires "
                     f"streaming authorization (Form RM-2201).", level="WARN")
            session.write(f"tail: cannot follow '{path}': "
                          f"Real-time stream authorization pending (Ref: RM-{bure._short_ref()})\n")
