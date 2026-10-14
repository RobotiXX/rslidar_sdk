"""SIGINT/SIGTERM regression without a LiDAR or privileged ports."""
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time
import unittest

from ament_index_python.packages import get_package_prefix
import yaml


class ShutdownTest(unittest.TestCase):
    def test_signals(self):
        binary = Path(get_package_prefix('rslidar_sdk')) / 'lib/rslidar_sdk/rslidar_sdk_node'
        for sig in (signal.SIGINT, signal.SIGTERM):
            with self.subTest(signal=sig), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                config = {'common': {'msg_source': 1, 'send_point_cloud_ros': True},
                          'lidar': [{'driver': {'lidar_type': 'RSHELIOS',
                                                'host_address': '127.0.0.1',
                                                'msop_port': 23699, 'difop_port': 23788},
                                     'ros': {'ros_send_point_cloud_topic': '/test_cloud'}}]}
                (root / 'config.yaml').write_text(yaml.safe_dump(config))
                env = dict(os.environ, ROS_DOMAIN_ID='97', ROS_LOCALHOST_ONLY='1')
                with (root / 'node.log').open('w') as log:
                    process = subprocess.Popen(
                        [str(binary), '--ros-args', '-p', f'config_path:={root / "config.yaml"}'],
                        env=env, stdout=log, stderr=subprocess.STDOUT)
                    try:
                        deadline = time.monotonic() + 8
                        while time.monotonic() < deadline:
                            if process.poll() is not None:
                                self.fail((root / 'node.log').read_text())
                            if 'Driver is running' in (root / 'node.log').read_text():
                                break
                            time.sleep(0.05)
                        else:
                            self.fail('Driver did not become ready')
                        process.send_signal(sig)
                        self.assertEqual(process.wait(timeout=8), 0,
                                         (root / 'node.log').read_text())
                    finally:
                        if process.poll() is None:
                            process.kill()
                            process.wait()


if __name__ == '__main__':
    unittest.main()
