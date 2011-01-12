import unittest
from cloudboot.bootfabtasks import _iftar

class FabtasksUnitTests(unittest.TestCase):
    def test_not_tarname(self):
        assert _iftar("") is None
        assert _iftar(" ") is None
        assert _iftar("somefile") is None
        assert _iftar("/some/absolute/file") is None
        assert _iftar(".tar.gz") is None
        assert _iftar("xyz.tar") is None
        assert _iftar("xyz.gz") is None

    def test_is_tarname(self):
        assert _iftar("xyz.tar.gz") == "xyz"
        assert _iftar("/something/else.tar.gz") == "/something/else"

if __name__ == '__main__':
    unittest.main()
