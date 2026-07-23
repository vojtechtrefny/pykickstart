#
# Vojtech Trefny <vtrefny@redhat.com>
#
# Copyright 2026 Red Hat, Inc.
#
# This copyrighted material is made available to anyone wishing to use, modify,
# copy, or redistribute it subject to the terms and conditions of the GNU
# General Public License v.2.  This program is distributed in the hope that it
# will be useful, but WITHOUT ANY WARRANTY expressed or implied, including the
# implied warranties of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.  Any Red Hat
# trademarks that are incorporated in the source code or documentation are not
# subject to the GNU General Public License and may only be used or replicated
# with the express permission of Red Hat, Inc.
#
from pykickstart.version import F45
from pykickstart.base import BaseData, KickstartCommand
from pykickstart.errors import KickstartParseError, KickstartParseWarning
from pykickstart.options import KSOptionParser, mountpoint

import warnings
from pykickstart.i18n import _


class F45_StratisFsData(BaseData):
    removedKeywords = BaseData.removedKeywords
    removedAttrs = BaseData.removedAttrs

    def __init__(self, *args, **kwargs):
        BaseData.__init__(self, *args, **kwargs)
        self.size = kwargs.get("size", None)
        self.grow = kwargs.get("grow", False)
        self.maxSizeMB = kwargs.get("maxSizeMB", 0)
        self.name = kwargs.get("name", "")
        self.poolname = kwargs.get("poolname", "")
        self.preexist = kwargs.get("preexist", False)
        self.mountpoint = kwargs.get("mountpoint", "")

    def __eq__(self, y):
        if not y:
            return False

        return self.poolname == y.poolname and self.name == y.name

    def __ne__(self, y):
        return not self == y

    def _getArgsAsStr(self):
        retval = ""

        if self.size:
            retval += " --size=%d" % self.size
        if self.grow:
            retval += " --grow"
        if self.maxSizeMB:
            retval += " --maxsize=%d" % self.maxSizeMB
        if self.preexist:
            retval += " --useexisting"

        return retval

    def __str__(self):
        retval = BaseData.__str__(self)

        args = self._getArgsAsStr()
        args += " --name=%s" % self.name
        args += " --poolname=%s" % self.poolname

        retval += "stratisfs %s%s\n" % (self.mountpoint, args)
        return retval


class F45_StratisFs(KickstartCommand):
    removedKeywords = KickstartCommand.removedKeywords
    removedAttrs = KickstartCommand.removedAttrs
    conflictingCommands = ["autopart", "mount"]

    def __init__(self, writePriority=135, *args, **kwargs):
        KickstartCommand.__init__(self, writePriority, *args, **kwargs)
        self.op = self._getParser()

        self.fsList = kwargs.get("fsList", [])

    def __str__(self):
        retval = ""

        for fs in self.fsList:
            retval += fs.__str__()

        return retval

    def _getParser(self):
        op = KSOptionParser(prog="stratisfs", description="""
                            Create a Stratis filesystem.""", epilog="""
                            Create the partition first, then create the Stratis
                            pool, and then create the Stratis filesystem.
                            For example::

                                part stratis.01 --size 3000
                                stratispool mypool stratis.01
                                stratisfs / --poolname=mypool --name=rootfs --size=2000
                            """, version=F45, conflicts=self.conflictingCommands)
        op.add_argument("mntpoint", metavar="<mntpoint>", type=mountpoint, nargs=1,
                        version=F45, help="""
                        Mountpoint for this Stratis filesystem or 'none'.
                        """)
        op.add_argument("--size", type=int, version=F45, help="""
                        Size of this Stratis filesystem in MiB.""")
        op.add_argument("--grow", action="store_true", default=False,
                        version=F45, help="""
                        Tells the filesystem to grow to fill available space
                        (if any), or up to the maximum size setting. Can only
                        be used with non-overprovisioned pools.""")
        op.add_argument("--maxsize", dest="maxSizeMB", type=int,
                        version=F45, help="""
                        The maximum size in MiB the filesystem may grow to.
                        Specify an integer value here, and do not append any
                        units.  This option is only relevant if ``--grow`` is
                        specified as well.""")
        op.add_argument("--name", required=True, version=F45, help="""
                        The name of this Stratis filesystem.""")
        op.add_argument("--poolname", required=True, version=F45, help="""
                        Name of the Stratis pool this filesystem belongs to.
                        """)
        op.add_argument("--useexisting", dest="preexist", version=F45,
                        action="store_true", default=False,
                        help="Use an existing Stratis filesystem.")
        return op

    def parse(self, args):
        (ns, extra) = self.op.parse_known_args(args=args, lineno=self.lineno)

        if extra:
            mapping = {"command": "stratisfs", "options": extra}
            raise KickstartParseError(_("Unexpected arguments to %(command)s command: %(options)s") % mapping, lineno=self.lineno)

        fsd = self.dataClass()  # pylint: disable=not-callable
        self.set_to_obj(ns, fsd)
        fsd.lineno = self.lineno
        fsd.mountpoint = ns.mntpoint[0]

        if fsd.maxSizeMB and not fsd.grow:
            raise KickstartParseError(_("--maxsize requires --grow"), lineno=self.lineno)

        # Check for duplicates in the data list.
        if fsd in self.dataList():
            warnings.warn(_("A stratisfs with the name %(stratisfs_name)s has already been defined in pool %(pool_name)s.") % {"stratisfs_name": fsd.name, "pool_name": fsd.poolname}, KickstartParseWarning)

        return fsd

    def dataList(self):
        return self.fsList

    @property
    def dataClass(self):
        return self.handler.StratisFsData
