#!/usr/bin/env python3
import argparse
import logging
import os
import sys
import threading

import yaml

from vfs.generator import build_vfs
from endpoints.ssh import start_ssh_server
from session_log.session import SessionLogger

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("kafka-os")


def load_config(config_path="config/default.yaml"):
    with open(config_path) as f:
        return yaml.safe_load(f)


def load_profile(config: dict, profiles_dir="config/profiles"):
    profile_name = config.get("profile", "workstation")
    path = os.path.join(profiles_dir, f"{profile_name}.yaml")
    if not os.path.exists(path):
        log.error(f"Profile not found: {path}")
        sys.exit(1)
    with open(path) as f:
        return yaml.safe_load(f)


def main():
    parser = argparse.ArgumentParser(description="KAFKA-OS Tarpit")
    parser.add_argument("--config", default="config/default.yaml")
    parser.add_argument("--host-key", default="kafka_host_rsa")
    parser.add_argument("--profile", help="Override profile from config")
    parser.add_argument("--cluster", action="store_true",
                        help="Force cluster mode regardless of config")
    args = parser.parse_args()

    config = load_config(args.config)
    if args.profile:
        config["profile"] = args.profile
    if args.cluster:
        config.setdefault("cluster", {})["enabled"] = True

    cluster_cfg = config.get("cluster", {})
    use_cluster = cluster_cfg.get("enabled", False)

    if use_cluster:
        from cluster.manager import ClusterManager
        log.info("Starting in cluster mode.")
        mgr = ClusterManager(config, host_key_base=args.host_key)
        mgr.start()
        return

    # Single-instance mode
    profile = load_profile(config)
    log.info(f"Profile: {profile.get('identity',{}).get('hostname','unknown')}")

    vfs = build_vfs(profile)
    log.info("Virtual filesystem built.")

    session_logger = SessionLogger(config)

    threads = []

    if config.get("endpoints", {}).get("ssh", {}).get("enabled", True):
        t = threading.Thread(
            target=start_ssh_server,
            args=(profile, config, args.host_key, session_logger),
            daemon=True,
        )
        t.start()
        threads.append(t)

    if not threads:
        log.error("No endpoints enabled. Check config.")
        sys.exit(1)

    log.info("KAFKA-OS running. Press Ctrl-C to stop.")
    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        log.info("Shutting down.")


if __name__ == "__main__":
    main()
