import os
import socket
import threading
import logging

import paramiko

from shell.interpreter import Session, run_shell, COMMANDS
from shell.bureaucracy.engine import BureaucracyEngine
from op_shell.shell import launch_operator_shell
from session_log.session import SessionLogger
from vfs.generator import build_vfs

log = logging.getLogger(__name__)


class KafkaSSHServer(paramiko.ServerInterface):

    def __init__(self, profile, config, operator_keys):
        self.profile = profile
        self.config = config
        self.operator_keys = operator_keys
        self.authenticated_user = None
        self.is_operator = False
        self._event = threading.Event()

    def check_channel_request(self, kind, chanid):
        if kind == "session":
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_auth_password(self, username, password):
        console_magic = self.config.get("operator", {}).get("console_magic", "")
        if console_magic and password == console_magic:
            self.authenticated_user = username
            self.is_operator = True
            log.info(f"Operator console access via magic string: {username}")
            return paramiko.AUTH_SUCCESSFUL

        self.authenticated_user = username
        self.is_operator = False
        log.info(f"Tarpit auth: {username} from password")
        return paramiko.AUTH_SUCCESSFUL

    def check_auth_publickey(self, username, key):
        for op_key in self.operator_keys:
            if key.get_name() == op_key.get_name() and key.asbytes() == op_key.asbytes():
                self.authenticated_user = username
                self.is_operator = True
                log.info(f"Operator key auth: {username}")
                return paramiko.AUTH_SUCCESSFUL
        self.authenticated_user = username
        self.is_operator = False
        return paramiko.AUTH_SUCCESSFUL

    def check_channel_shell_request(self, channel):
        self._event.set()
        return True

    def check_channel_pty_request(self, channel, term, width, height,
                                   pixelwidth, pixelheight, modes):
        return True

    def get_allowed_auths(self, username):
        return "password,publickey"


def _load_operator_keys(config):
    keys = []
    key_file = os.path.expanduser(
        config.get("operator", {}).get("authorized_keys_file",
                                       "~/.ssh/kafka_operator_authorized_keys")
    )
    if not os.path.exists(key_file):
        return keys
    try:
        with open(key_file) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split()
                if len(parts) < 2:
                    continue
                key_type, key_data = parts[0], parts[1]
                import base64
                raw = base64.b64decode(key_data)
                msg = paramiko.Message(raw)
                key = paramiko.PKey.from_type_string(key_type, msg)
                keys.append(key)
    except Exception as e:
        log.warning(f"Could not load operator keys: {e}")
    return keys


def handle_client(client_sock, addr, host_key, profile, config, vfs, session_logger,
                  cluster_registry=None, instance_id=None, on_session_end=None):
    transport = paramiko.Transport(client_sock)
    transport.add_server_key(host_key)

    banner = config.get("endpoints", {}).get("ssh", {}).get(
        "banner", "OpenSSH_8.9p1 Ubuntu-3ubuntu0.6")
    transport.local_version = f"SSH-2.0-{banner.split(',')[0]}"

    operator_keys = _load_operator_keys(config)
    server = KafkaSSHServer(profile, config, operator_keys)

    try:
        transport.start_server(server=server)
    except Exception as e:
        log.debug(f"Transport start failed: {e}")
        return

    channel = transport.accept(30)
    if channel is None:
        return

    server._event.wait(10)

    remote_ip = addr[0]
    username = server.authenticated_user or "unknown"
    session_logger.start_session(username, remote_ip)

    try:
        if server.is_operator:
            real_shell = config.get("operator", {}).get("real_shell", "/bin/bash")
            launch_operator_shell(channel, real_shell)
        else:
            _run_tarpit(channel, username, remote_ip, profile, config, vfs,
                        session_logger, cluster_registry=cluster_registry,
                        instance_id=instance_id)
    finally:
        session_logger.end_session(username)
        if on_session_end:
            try:
                on_session_end()
            except Exception:
                pass
        try:
            channel.close()
        except Exception:
            pass
        transport.close()


def _run_tarpit(channel, username, remote_ip, profile, config, vfs, session_logger,
                cluster_registry=None, instance_id=None):
    def write(text):
        try:
            channel.sendall(text.replace("\n", "\r\n"))
            session_logger.log_output(username, text)
        except Exception:
            pass

    def prompt(text=""):
        write(text)
        buf = ""
        try:
            while True:
                data = channel.recv(1)
                if not data:
                    raise EOFError()
                ch = data.decode("utf-8", errors="replace")
                if ch in ("\r", "\n"):
                    write("\r\n")
                    break
                elif ch in ("\x7f", "\x08"):
                    if buf:
                        buf = buf[:-1]
                        write("\x08 \x08")
                elif ch == "\x03":
                    raise KeyboardInterrupt()
                elif ch == "\x04" and not buf:
                    raise EOFError()
                else:
                    buf += ch
                    write(ch)
        except (EOFError, OSError):
            raise EOFError()
        session_logger.log_input(username, text + buf)
        return buf

    def prompt_secret(text=""):
        write(text)
        buf = ""
        try:
            while True:
                data = channel.recv(1)
                if not data:
                    raise EOFError()
                ch = data.decode("utf-8", errors="replace")
                if ch in ("\r", "\n"):
                    write("\r\n")
                    break
                elif ch in ("\x7f", "\x08"):
                    if buf:
                        buf = buf[:-1]
                elif ch == "\x03":
                    raise KeyboardInterrupt()
                else:
                    buf += ch
        except (EOFError, OSError):
            raise EOFError()
        session_logger.log_input(username, f"{text}[REDACTED]")
        return buf

    bure = BureaucracyEngine(config, output_func=write)
    session = Session(
        username=username,
        profile=profile,
        vfs=vfs,
        config=config,
        write_func=write,
        prompt_func=prompt,
        prompt_secret_func=prompt_secret,
        remote_ip=remote_ip,
        cluster_registry=cluster_registry,
        instance_id=instance_id,
    )

    try:
        run_shell(session, bure)
    except (EOFError, SystemExit, OSError):
        pass


def start_ssh_server(profile, config, host_key_path, session_logger,
                     port=None, cluster_registry=None, instance_id=None,
                     profile_factory=None,
                     # legacy positional compat: old callers passed vfs as 3rd arg
                     vfs=None):
    """Start the SSH accept loop.

    port overrides config endpoint port.
    profile_factory() is called after each session ends to regenerate identity
    (used by new_machine_on_disconnect). VFS is always built fresh per connection.
    """
    if port is None:
        port = config.get("endpoints", {}).get("ssh", {}).get("port", 22)

    if not os.path.exists(host_key_path):
        log.info(f"Generating host key at {host_key_path}")
        key = paramiko.RSAKey.generate(2048)
        key.write_private_key_file(host_key_path)
    else:
        key = paramiko.RSAKey(filename=host_key_path)

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", port))
    sock.listen(20)
    log.info(f"SSH tarpit listening on :{port}")

    current_profile = [profile]
    profile_lock = threading.Lock()

    while True:
        try:
            client, addr = sock.accept()
        except Exception as e:
            log.error(f"Accept error: {e}")
            continue

        log.info(f"Connection from {addr[0]}:{addr[1]}")

        with profile_lock:
            p = current_profile[0]

        # Always build a fresh VFS per connection — eliminates shared mutable state
        # and ensures each attacker starts clean.
        session_vfs = build_vfs(p)

        def on_done(p_ref=p):
            if profile_factory:
                with profile_lock:
                    new_p = profile_factory()
                    current_profile[0] = new_p

        t = threading.Thread(
            target=handle_client,
            args=(client, addr, key, p, config, session_vfs, session_logger),
            kwargs={
                "cluster_registry": cluster_registry,
                "instance_id": instance_id,
                "on_session_end": on_done,
            },
            daemon=True,
        )
        t.start()
