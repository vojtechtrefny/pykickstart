import unittest
from tests.baseclass import CommandTest, CommandSequenceTest
from pykickstart.commands.stratispool import F45_StratisPoolData
from pykickstart.errors import KickstartParseWarning
from pykickstart.version import F45


class StratisPool_TestCase(unittest.TestCase):
    def runTest(self):
        data1 = F45_StratisPoolData()
        data2 = F45_StratisPoolData()

        # test default object values
        self.assertEqual(data1.preexist, False)
        self.assertEqual(data1.encrypted, False)
        self.assertEqual(data1.passphrase, "")
        self.assertEqual(data1.overprovisioning, False)

        # test that new objects are always equal
        self.assertEqual(data1, data2)
        self.assertNotEqual(data1, None)

        # test for objects difference
        for atr in ['name']:
            setattr(data1, atr, '')
            setattr(data2, atr, 'test')
            # objects that differ in only one attribute
            # are not equal
            self.assertNotEqual(data1, data2)
            self.assertNotEqual(data2, data1)
            setattr(data1, atr, '')
            setattr(data2, atr, '')


class F45_TestCase(CommandTest):
    command = "stratispool"

    def runTest(self):
        # pass - basic pool creation
        self.assert_parse("stratispool pool.01 stratis.01",
                          "stratispool pool.01 stratis.01\n")

        # pass - multiple partitions
        self.assert_parse("stratispool pool.01 stratis.01 stratis.02",
                          "stratispool pool.01 stratis.01 stratis.02\n")

        # --useexisting
        self.assert_parse("stratispool pool.01 --useexisting",
                          "stratispool pool.01 --useexisting\n")

        # --encrypted
        self.assert_parse("stratispool pool.01 stratis.01 --encrypted",
                          "stratispool pool.01 --encrypted stratis.01\n")

        # --encrypted --passphrase
        self.assert_parse("stratispool pool.01 stratis.01 --encrypted --passphrase=\"secret\"",
                          "stratispool pool.01 --encrypted --passphrase=\"secret\" stratis.01\n")

        # --overprovisioning
        self.assert_parse("stratispool pool.01 stratis.01 --overprovisioning",
                          "stratispool pool.01 --overprovisioning stratis.01\n")

        # assert data types
        self.assert_type("stratispool", "preexist", "boolean")
        self.assert_type("stratispool", "encrypted", "boolean")
        self.assert_type("stratispool", "overprovisioning", "boolean")

        self.assertFalse(self.assert_parse("stratispool pool.01 stratis.01") is None)
        self.assertTrue(self.assert_parse("stratispool pool.01 stratis.01") !=
                        self.assert_parse("stratispool pool.02 stratis.01"))
        self.assertFalse(self.assert_parse("stratispool pool.01 stratis.01") ==
                         self.assert_parse("stratispool pool.02 stratis.01"))

        # fail - missing name
        self.assert_parse_error("stratispool")

        # fail - missing list of partitions
        self.assert_parse_error("stratispool pool.01")

        # fail - both members and useexisting specified
        self.assert_parse_error("stratispool pool.01 stratis.01 stratis.02 --useexisting")
        self.assert_parse_error("stratispool pool.01 --useexisting stratis.01 stratis.02")

        # fail - passphrase without encrypted
        self.assert_parse_error("stratispool pool.01 stratis.01 --passphrase=\"secret\"")

        # fail - invalid argument
        self.assert_parse_error("stratispool --bogus-option")

        # extra test coverage
        cmd = self.handler().commands[self.command]
        cmd.poolList = ["pool.01"]
        self.assertEqual(cmd.__str__(), "pool.01")


class F45_Multiple_TestCase(CommandSequenceTest):
    def __init__(self, *args, **kwargs):
        CommandSequenceTest.__init__(self, *args, **kwargs)
        self.version = F45

    def runTest(self):
        # two pools with different names
        self.assert_parse("""
stratispool pool.01 stratis.01
stratispool pool.02 stratis.02""")

        self.assert_parse("""
stratispool pool.01 stratis.01 --encrypted --passphrase="secret"
stratispool pool.02 stratis.02 --overprovisioning""")

        # multiple block devices
        self.assert_parse("""
stratispool pool.01 stratis.01 stratis.02
stratispool pool.02 stratis.03 stratis.04""")


class F45_Duplicate_TestCase(CommandSequenceTest):
    def __init__(self, *args, **kwargs):
        CommandSequenceTest.__init__(self, *args, **kwargs)
        self.version = F45

    def runTest(self):
        self.assert_parse("""
stratispool pool.01 stratis.01
stratispool pool.02 stratis.01""")

        self.assert_parse_error("""
stratispool pool.01 stratis.01
stratispool pool.01 stratis.02""", KickstartParseWarning, 'A stratispool with the name pool.01 has already been defined.')


class F45_Conflict_TestCase(CommandSequenceTest):
    def __init__(self, *args, **kwargs):
        CommandSequenceTest.__init__(self, *args, **kwargs)
        self.version = F45

    def runTest(self):
        # fail - can't use both autopart and stratispool
        self.assert_parse_error("""
autopart
stratispool pool.01 stratis.01""")

        self.assert_parse_error("""
mount /dev/sda1 /boot
stratispool pool.01 stratis.01""")

if __name__ == "__main__":
    unittest.main()
