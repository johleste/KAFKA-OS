import copy
import logging
import os
import random
import threading
import time

import yaml

from cluster.registry import ClusterRegistry
from endpoints.ssh import start_ssh_server
from session_log.session import SessionLogger

log = logging.getLogger(__name__)

_ADJECTIVES = ["dev", "web", "db", "app", "svc", "api", "lab", "bld", "ops", "cfg"]
_NOUNS = ["ws", "srv", "node", "host", "box", "vm", "svr", "stn"]


def _random_hostname():
    return f"{random.choice(_ADJECTIVES)}-{random.choice(_NOUNS)}-{random.randint(1, 999):03d}"


def _fake_ip(cluster_cfg, index):
    base = cluster_cfg.get("base_ip", "10.0.0")
    start = cluster_cfg.get("ip_start", 11)
    return f"{base}.{start + index}"


def _variant_profile(base_profile, fake_ip, index):
    """Build a profile variant for a specific cluster slot."""
    p = copy.deepcopy(base_profile)
    identity = p.setdefault("identity", {})
    base_host = identity.get("hostname", "host")
    identity["hostname"] = base_host if index == 0 else f"{base_host}-{index:02d}"
    p.setdefault("network", {})["ip"] = fake_ip
    return p


def _fresh_profile(base_profile, fake_ip):
    """Generate a new random identity variant for new_machine_on_disconnect."""
    p = copy.deepcopy(base_profile)
    p.setdefault("identity", {})["hostname"] = _random_hostname()
    p.setdefault("network", {})["ip"] = fake_ip
    return p


class ClusterManager:
    """Spawns and manages multiple KAFKA-OS instances, each on its own port."""

    def __init__(self, config, profiles_dir="config/profiles",
                 host_key_base="kafka_host_rsa"):
        self.config = config
        self.cluster_cfg = config.get("cluster", {})
        self.profiles_dir = profiles_dir
        self.host_key_base = host_key_base
        self.registry = ClusterRegistry.get()
        self._threads = []

    def _load_base_profile(self, name):
        path = os.path.join(self.profiles_dir, f"{name}.yaml")
        with open(path) as f:
            return yaml.safe_load(f)

    def _spawn_instance(self, instance_id, port, profile_name, fake_ip, index):
        new_machine = self.cluster_cfg.get("new_machine_on_disconnect", False)
        respawn = self.cluster_cfg.get("respawn", True)
        host_key_path = f"{self.host_key_base}_{instance_id}"
        session_logger = SessionLogger(self.config)
        base_profile = self._load_base_profile(profile_name)
        registry = self.registry
        config = self.config

        def run():
            profile = _variant_profile(base_profile, fake_ip, index)
            hostname = profile.get("identity", {}).get("hostname", instance_id)
            registry.register(instance_id, fake_ip, port, hostname, profile)
            log.info(f"[{instance_id}] Spawning on :{port}  {hostname} ({fake_ip})")

            def profile_factory():
                p = _fresh_profile(base_profile, fake_ip) if new_machine else \
                    _variant_profile(base_profile, fake_ip, index)
                h = p.get("identity", {}).get("hostname", instance_id)
                registry.register(instance_id, fake_ip, port, h, p)
                log.info(f"[{instance_id}] New identity: {h}")
                return p

            while True:
                try:
                    start_ssh_server(
                        profile=profile,
                        config=config,
                        host_key_path=host_key_path,
                        session_logger=session_logger,
                        port=port,
                        cluster_registry=registry,
                        instance_id=instance_id,
                        profile_factory=profile_factory if new_machine else None,
                    )
                except Exception as e:
                    log.error(f"[{instance_id}] Server error: {e}")

                if not respawn:
                    break
                log.info(f"[{instance_id}] Restarting in 1s...")
                time.sleep(1)

        t = threading.Thread(target=run, daemon=True, name=instance_id)
        t.start()
        return t

    def start(self):
        n = self.cluster_cfg.get("instances", 1)
        port_start = self.cluster_cfg.get("port_start", 2222)
        profiles = self.cluster_cfg.get(
            "profiles", [self.config.get("profile", "workstation")]
        )

        for i in range(n):
            port = port_start + i
            profile_name = profiles[i % len(profiles)]
            ip = _fake_ip(self.cluster_cfg, i)
            t = self._spawn_instance(f"instance-{i}", port, profile_name, ip, i)
            self._threads.append(t)

        log.info(
            f"Cluster: {n} instance(s) on ports {port_start}–{port_start + n - 1}"
        )

        try:
            for t in self._threads:
                t.join()
        except KeyboardInterrupt:
            log.info("Cluster shutting down.")
