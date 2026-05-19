import os


def _editor_session(session, bure, editor_name, path=None):
    bure.log(f"Launching {editor_name}...")
    bure.simulated_check(f"{editor_name.capitalize()} License Validation", "base_check_short_ms")

    if path:
        if not path.startswith("/"):
            path = os.path.normpath(session.cwd + "/" + path)
        content = session.vfs.read(path) or ""
        session.write(f"\n--- {editor_name}: {path} ---\n")
        # Show first few lines
        for line in content.splitlines()[:5]:
            session.write(line + "\n")
        if len(content.splitlines()) > 5:
            session.write(f"... ({len(content.splitlines())} lines total) ...\n")
    else:
        session.write(f"\n--- {editor_name}: new buffer ---\n")
        path = "[No Name]"

    session.write(f"\n[{editor_name.upper()}] Enter text (type :wq or Ctrl-X to save and exit):\n")

    lines = []
    while True:
        try:
            line = session.prompt("> ")
        except (KeyboardInterrupt, EOFError):
            break
        if line in (":wq", ":q!", ":x", "\\x") or line.strip() == "\x18":
            break
        lines.append(line)

    if lines:
        new_content = "\n".join(lines) + "\n"
        # Appear to write — silently discard
        result = session.vfs.write(path, new_content)
        bure.simulated_check("Write Buffer Flush & ACL Re-validation", "base_check_short_ms")
        bure.forward('FS_WRITE', f"{editor_name}:save:{path}", "Editor Save Event")
        session.write(f'"{path}" written, {len(lines)} lines\n')
        # File content unchanged — write was discarded by vfs.write()
    else:
        session.write(f'"{path}" unchanged\n')


def cmd_vim(session, args, bure):
    path = args[0] if args else None
    _editor_session(session, bure, "vim", path)


def cmd_vi(session, args, bure):
    path = args[0] if args else None
    _editor_session(session, bure, "vi", path)


def cmd_nano(session, args, bure):
    path = args[0] if args else None
    _editor_session(session, bure, "nano", path)
