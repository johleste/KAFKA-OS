import os
import pty
import subprocess
import select
import termios
import tty


def launch_operator_shell(channel, real_shell="/bin/bash"):
    """
    Spawn a real PTY shell and bridge it to the Paramiko channel.
    Called when an operator authenticates via SSH key.
    """
    master_fd, slave_fd = pty.openpty()

    proc = subprocess.Popen(
        [real_shell],
        stdin=slave_fd,
        stdout=slave_fd,
        stderr=slave_fd,
        close_fds=True,
        env={**os.environ, "TERM": "xterm-256color"},
    )
    os.close(slave_fd)

    try:
        while proc.poll() is None:
            r, _, _ = select.select([master_fd, channel], [], [], 0.1)
            if master_fd in r:
                data = os.read(master_fd, 1024)
                if data:
                    channel.sendall(data)
            if channel in r:
                data = channel.recv(1024)
                if not data:
                    break
                os.write(master_fd, data)
    except Exception:
        pass
    finally:
        try:
            os.close(master_fd)
        except Exception:
            pass
        try:
            proc.terminate()
        except Exception:
            pass
        channel.close()
