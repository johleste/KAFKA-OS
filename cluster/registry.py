import threading


class ClusterRegistry:
    """Thread-safe singleton registry of all running KAFKA-OS instances.

    Each instance registers its fake IP, port, hostname, and profile so that
    sibling-aware commands (nmap subnet scans, ssh routing) can query it.
    """

    _instance = None
    _singleton_lock = threading.Lock()

    @classmethod
    def get(cls):
        if cls._instance is None:
            with cls._singleton_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self):
        self._lock = threading.Lock()
        self._instances = {}  # instance_id -> {ip, port, hostname, profile}

    def register(self, instance_id, ip, port, hostname, profile):
        with self._lock:
            self._instances[instance_id] = {
                "ip": ip,
                "port": port,
                "hostname": hostname,
                "profile": profile,
            }

    def unregister(self, instance_id):
        with self._lock:
            self._instances.pop(instance_id, None)

    def get_all(self):
        with self._lock:
            return dict(self._instances)

    def get_siblings(self, my_id):
        with self._lock:
            return {k: v for k, v in self._instances.items() if k != my_id}

    def get_by_ip(self, ip):
        with self._lock:
            return next(
                (v for v in self._instances.values() if v["ip"] == ip), None
            )

    def all_ips(self):
        with self._lock:
            return [v["ip"] for v in self._instances.values()]
