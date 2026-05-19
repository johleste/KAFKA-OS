import os
import stat
import time
import random


class VFSNode:
    def __init__(self, name, is_dir=False, content="", owner="root", group="root",
                 mode=0o644, mtime=None):
        self.name = name
        self.is_dir = is_dir
        self.content = content
        self.owner = owner
        self.group = group
        self.mode = mode if not is_dir else (mode | 0o111)
        self.mtime = mtime or (time.time() - random.randint(3600, 86400 * 30))
        self.children = {} if is_dir else None

    def size(self):
        return len(self.content.encode()) if not self.is_dir else 4096

    def mode_str(self):
        bits = self.mode
        d = "d" if self.is_dir else "-"
        chars = ""
        for shift in (6, 3, 0):
            r = "r" if bits & (0o4 << shift) else "-"
            w = "w" if bits & (0o2 << shift) else "-"
            x = "x" if bits & (0o1 << shift) else "-"
            chars += r + w + x
        return d + chars


class VFS:
    def __init__(self):
        self._root = VFSNode("/", is_dir=True, mode=0o755)

    def _resolve(self, path):
        parts = [p for p in path.split("/") if p]
        node = self._root
        for part in parts:
            if not node.is_dir or part not in node.children:
                return None
            node = node.children[part]
        return node

    def makedirs(self, path, owner="root", group="root", mode=0o755):
        parts = [p for p in path.split("/") if p]
        node = self._root
        for part in parts:
            if part not in node.children:
                node.children[part] = VFSNode(part, is_dir=True,
                                               owner=owner, group=group, mode=mode)
            node = node.children[part]
        return node

    def mkfile(self, path, content="", owner="root", group="root", mode=0o644, mtime=None):
        parent_path, name = path.rsplit("/", 1)
        parent = self._resolve(parent_path) if parent_path else self._root
        if parent is None:
            parent = self.makedirs(parent_path, owner=owner, group=group)
        node = VFSNode(name, is_dir=False, content=content,
                       owner=owner, group=group, mode=mode, mtime=mtime)
        parent.children[name] = node
        return node

    def exists(self, path):
        return self._resolve(path) is not None

    def is_dir(self, path):
        node = self._resolve(path)
        return node is not None and node.is_dir

    def listdir(self, path):
        node = self._resolve(path)
        if node is None or not node.is_dir:
            return None
        return node.children

    def read(self, path):
        node = self._resolve(path)
        if node is None or node.is_dir:
            return None
        return node.content

    def get_node(self, path):
        return self._resolve(path)

    def write(self, path, content):
        node = self._resolve(path)
        if node is not None and not node.is_dir:
            # Appear to succeed — but content is silently discarded
            return True
        return False
