from __future__ import annotations

import json
import os
import subprocess
import unittest
from pathlib import Path


def _inspect(container: str) -> dict:
    result = subprocess.run(
        ["docker", "inspect", container],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"docker inspect failed: {container}")
    payload = json.loads(result.stdout)
    if not payload:
        raise RuntimeError(f"empty docker inspect payload: {container}")
    return payload[0]


def _container_exists(container: str) -> bool:
    result = subprocess.run(
        ["docker", "ps", "-a", "--format", "{{.Names}}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return False
    names = {line.strip() for line in result.stdout.splitlines() if line.strip()}
    return container in names


class ProductionContainerGuardrails(unittest.TestCase):
    container = "openclaw"

    @classmethod
    def setUpClass(cls) -> None:
        if not _container_exists(cls.container):
            raise unittest.SkipTest("production container 'openclaw' not found")
        cls.info = _inspect(cls.container)

    def test_container_is_running(self) -> None:
        self.assertEqual(self.info["State"]["Running"], True)

    def test_restart_policy_unless_stopped(self) -> None:
        self.assertEqual(self.info["HostConfig"]["RestartPolicy"]["Name"], "unless-stopped")

    def test_hardening_flags(self) -> None:
        host = self.info["HostConfig"]
        self.assertEqual(host.get("ReadonlyRootfs"), True)
        cap_drop = set(host.get("CapDrop") or [])
        self.assertIn("ALL", cap_drop)
        tmpfs = host.get("Tmpfs") or {}
        self.assertIn("/tmp", tmpfs)

    def test_required_mount_destinations(self) -> None:
        destinations = {mount.get("Destination") for mount in self.info.get("Mounts", [])}
        self.assertIn("/home/node/.openclaw-prod", destinations)
        self.assertIn("/home/node/.openclaw", destinations)
        self.assertIn("/tmp/openclaw", destinations)
        self.assertIn("/home/node/clawd", destinations)


class BlueGreenIsolationChecks(unittest.TestCase):
    blue = "openclaw"
    green = "openclaw-next"

    @classmethod
    def setUpClass(cls) -> None:
        if not _container_exists(cls.blue):
            raise unittest.SkipTest("blue container 'openclaw' not found")
        cls.blue_info = _inspect(cls.blue)
        if not _container_exists(cls.green):
            raise unittest.SkipTest("green container 'openclaw-next' not found")
        cls.green_info = _inspect(cls.green)

    @staticmethod
    def _mount_map(info: dict) -> dict[str, str]:
        return {
            mount["Destination"]: mount["Source"]
            for mount in info.get("Mounts", [])
            if mount.get("Destination") and mount.get("Source")
        }

    def test_workspace_and_data_are_isolated(self) -> None:
        blue_mounts = self._mount_map(self.blue_info)
        green_mounts = self._mount_map(self.green_info)
        for destination in (
            "/home/node/.openclaw-prod",
            "/home/node/.openclaw",
            "/tmp/openclaw",
            "/home/node/clawd",
        ):
            self.assertIn(destination, blue_mounts)
            self.assertIn(destination, green_mounts)
            self.assertNotEqual(
                blue_mounts[destination],
                green_mounts[destination],
                f"mount collision detected for {destination}",
            )


if __name__ == "__main__":
    unittest.main()
