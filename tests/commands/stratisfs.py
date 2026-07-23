import unittest
from tests.baseclass import CommandTest, CommandSequenceTest
from pykickstart.commands.stratisfs import F45_StratisFsData
from pykickstart.errors import KickstartParseWarning
from pykickstart.version import F45


class StratisFs_TestCase(unittest.TestCase):
    def runTest(self):
        data1 = F45_StratisFsData()
        data2 = F45_StratisFsData()

        # test default object values
        self.assertEqual(data1.grow, False)
        self.assertEqual(data1.maxSizeMB, 0)
        self.assertEqual(data1.preexist, False)

        # test that new objects are always equal
        self.assertEqual(data1, data2)
        self.assertNotEqual(data1, None)

        # test for objects difference
        for atr in ['name', 'poolname']:
            setattr(data1, atr, '')
            setattr(data2, atr, 'test')
            # objects that differ in only one attribute
            # are not equal
            self.assertNotEqual(data1, data2)
            self.assertNotEqual(data2, data1)
            setattr(data1, atr, '')
            setattr(data2, atr, '')


class F45_TestCase(CommandTest):
    command = "stratisfs"

    def runTest(self):
        self.assertFalse(self.assert_parse("stratisfs / --size=1024 --name=NAME --poolname=POOL") is None)
        self.assertTrue(self.assert_parse("stratisfs / --size=1024 --name=NAME --poolname=POOL") !=
                        self.assert_parse("stratisfs / --size=1024 --name=OTHER --poolname=POOL"))
        self.assertFalse(self.assert_parse("stratisfs / --size=1024 --name=NAME --poolname=POOL") ==
                         self.assert_parse("stratisfs / --size=1024 --name=OTHER --poolname=POOL"))
        self.assertFalse(self.assert_parse("stratisfs / --size=1024 --name=NAME --poolname=POOL") ==
                         self.assert_parse("stratisfs / --size=1024 --name=NAME --poolname=OTHERPOOL"))

        # --name and --poolname
        self.assert_parse("stratisfs / --size=10240 --name=NAME --poolname=POOL",
                          "stratisfs / --size=10240 --name=NAME --poolname=POOL\n")
        # --grow
        self.assert_parse("stratisfs / --grow --size=10240 --name=NAME --poolname=POOL",
                          "stratisfs / --size=10240 --grow --name=NAME --poolname=POOL\n")
        # --size
        self.assert_parse("stratisfs / --size=1024 --name=NAME --poolname=POOL",
                          "stratisfs / --size=1024 --name=NAME --poolname=POOL\n")
        # --maxsize with --grow
        self.assert_parse("stratisfs / --maxsize=2048 --grow --size=1024 --name=NAME --poolname=POOL",
                          "stratisfs / --size=1024 --grow --maxsize=2048 --name=NAME --poolname=POOL\n")
        # --useexisting
        self.assert_parse("stratisfs / --useexisting --name=NAME --poolname=POOL",
                          "stratisfs / --useexisting --name=NAME --poolname=POOL\n")
        # mountpoint none
        self.assert_parse("stratisfs none --size=1024 --name=NAME --poolname=POOL",
                          "stratisfs none --size=1024 --name=NAME --poolname=POOL\n")

        # assert data types
        self.assert_type("stratisfs", "size", "int")
        self.assert_type("stratisfs", "maxsize", "int")

        # fail - incorrect type
        self.assert_parse_error("stratisfs / --name=NAME --poolname=POOL --size=SIZE",
                                regex="argument --size: invalid int value: 'SIZE'")
        self.assert_parse_error("stratisfs / --name=NAME --poolname=POOL --maxsize=MAXSIZE",
                                regex="argument --maxsize: invalid int value: 'MAXSIZE'")

        # fail - missing required arguments
        self.assert_parse_error("stratisfs --name=NAME --poolname=POOL")
        self.assert_parse_error("stratisfs / --poolname=POOL")
        self.assert_parse_error("stratisfs / --name=NAME")

        # fail - maxsize without grow
        self.assert_parse_error("stratisfs / --maxsize=2048 --size=1024 --name=NAME --poolname=POOL")

        # fail - invalid argument
        self.assert_parse_error("stratisfs / --name=NAME --poolname=POOL --bogus-option")

        # extra test coverage
        cmd = self.handler().commands[self.command]
        cmd.fsList = ["fs.01"]
        self.assertEqual(cmd.__str__(), "fs.01")


class F45_Multiple_TestCase(CommandSequenceTest):
    def __init__(self, *args, **kwargs):
        CommandSequenceTest.__init__(self, *args, **kwargs)
        self.version = F45

    def runTest(self):
        # two filesystems, same pool
        self.assert_parse("""
stratisfs / --size=1024 --name=rootfs --poolname=mypool
stratisfs /home --size=2048 --name=homefs --poolname=mypool""")

        # two filesystems, different pools
        self.assert_parse("""
stratisfs / --size=1024 --name=rootfs --poolname=pool1
stratisfs /home --size=2048 --name=homefs --poolname=pool2""")

        # same fs name but two different pools
        self.assert_parse("""
stratisfs none --size=1024 --name=data --poolname=pool1
stratisfs none --size=2048 --name=data --poolname=pool2""")


class F45_Duplicate_TestCase(CommandSequenceTest):
    def __init__(self, *args, **kwargs):
        CommandSequenceTest.__init__(self, *args, **kwargs)
        self.version = F45

    def runTest(self):
        self.assert_parse("""
stratisfs / --size=1024 --name=NAME --poolname=POOL
stratisfs /home --size=1024 --name=OTHER --poolname=POOL""")

        self.assert_parse_error("""
stratisfs / --size=1024 --name=NAME --poolname=POOL
stratisfs /home --size=1024 --name=NAME --poolname=POOL""", KickstartParseWarning, 'A stratisfs with the name NAME has already been defined in pool POOL.')


class F45_Conflict_TestCase(CommandSequenceTest):
    def __init__(self, *args, **kwargs):
        CommandSequenceTest.__init__(self, *args, **kwargs)
        self.version = F45

    def runTest(self):
        # fail - can't use both autopart and stratisfs
        self.assert_parse_error("""
autopart
stratisfs / --size=1024 --name=NAME --poolname=POOL""")

        self.assert_parse_error("""
mount /dev/sda1 /boot
stratisfs / --size=1024 --name=NAME --poolname=POOL""")

if __name__ == "__main__":
    unittest.main()
