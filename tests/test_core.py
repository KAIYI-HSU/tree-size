import os
import shutil
import tempfile
import unittest
from utils import get_dir_size, format_bytes, scan_directory

class TestCoreLogic(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

        # Create some files
        self.file1 = os.path.join(self.test_dir, "file1.txt")
        with open(self.file1, "wb") as f:
            f.write(b"a" * 1024) # 1KB

        self.subdir = os.path.join(self.test_dir, "subdir")
        os.mkdir(self.subdir)

        self.file2 = os.path.join(self.subdir, "file2.txt")
        with open(self.file2, "wb") as f:
            f.write(b"b" * 2048) # 2KB

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_get_dir_size(self):
        size = get_dir_size(self.test_dir)
        self.assertEqual(size, 3072)

    def test_format_bytes(self):
        self.assertEqual(format_bytes(100), "100.00 B")
        self.assertEqual(format_bytes(1024), "1.00 KB")
        self.assertEqual(format_bytes(2048), "2.00 KB")

    def test_scan_directory(self):
        # Mock progress callback
        def mock_progress(value, text=None):
            pass

        data = scan_directory(self.test_dir, mock_progress)

        # We expect:
        # 1. Root node (test_dir)
        # 2. file1.txt
        # 3. subdir
        # 4. subdir/file2.txt (because depth=1 is traversed in _walk_and_add)

        # Check if root exists
        root_node = next((item for item in data if item['id'] == self.test_dir), None)
        self.assertIsNotNone(root_node)
        self.assertEqual(root_node['value'], 3072)

        # Check file1
        file1_node = next((item for item in data if item['id'] == self.file1), None)
        self.assertIsNotNone(file1_node)
        self.assertEqual(file1_node['value'], 1024)

        # Check subdir
        subdir_node = next((item for item in data if item['id'] == self.subdir), None)
        self.assertIsNotNone(subdir_node)
        self.assertEqual(subdir_node['value'], 2048)

        # Check file2 inside subdir
        file2_node = next((item for item in data if item['id'] == self.file2), None)
        self.assertIsNotNone(file2_node)
        self.assertEqual(file2_node['value'], 2048)

if __name__ == '__main__':
    unittest.main()
