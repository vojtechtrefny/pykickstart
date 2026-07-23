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
from pykickstart.options import KSOptionParser

import warnings
from pykickstart.i18n import _


class F45_StratisPoolData(BaseData):
    removedKeywords = BaseData.removedKeywords
    removedAttrs = BaseData.removedAttrs

    def __init__(self, *args, **kwargs):
        BaseData.__init__(self, *args, **kwargs)
        self.preexist = kwargs.get("preexist", False)
        self.encrypted = kwargs.get("encrypted", False)
        self.passphrase = kwargs.get("passphrase", "")
        self.overprovisioning = kwargs.get("overprovisioning", False)
        self.name = kwargs.get("name", "")
        self.blockdevs = kwargs.get("blockdevs", [])

    def __eq__(self, y):
        if not y:
            return False

        return self.name == y.name

    def __ne__(self, y):
        return not self == y

    def _getArgsAsStr(self):
        retval = ""
        if self.preexist:
            retval += " --useexisting"
        if self.encrypted:
            retval += " --encrypted"
        if self.passphrase:
            retval += " --passphrase=\"%s\"" % self.passphrase
        if self.overprovisioning:
            retval += " --overprovisioning"

        return retval

    def __str__(self):
        retval = BaseData.__str__(self)
        retval += "stratispool %s" % self.name
        retval += self._getArgsAsStr()

        if not self.preexist:
            retval += " " + " ".join(self.blockdevs)

        return retval.strip() + "\n"


class F45_StratisPool(KickstartCommand):
    removedKeywords = KickstartCommand.removedKeywords
    removedAttrs = KickstartCommand.removedAttrs
    conflictingCommands = ["autopart", "mount"]

    def __init__(self, writePriority=134, *args, **kwargs):
        KickstartCommand.__init__(self, writePriority, *args, **kwargs)
        self.op = self._getParser()

        self.poolList = kwargs.get("poolList", [])

    def __str__(self):
        retval = ""
        for pool in self.poolList:
            retval += pool.__str__()

        return retval

    def _getParser(self):
        op = KSOptionParser(prog="stratispool", description="""
                            Creates a Stratis storage pool.""", epilog="""
                            Create the partition first, then create the Stratis
                            pool, and then create the Stratis filesystem.
                            For example::

                                part stratis.01 --size 3000
                                stratispool mypool stratis.01
                                stratisfs / --poolname=mypool --name=rootfs --size=2000
                            """, version=F45, conflicts=self.conflictingCommands)
        op.add_argument("name", metavar="<name>", nargs="*", version=F45, help="""
                        Name given to the Stratis pool.""")
        op.add_argument("blockdevs", metavar="<blockdevs*>", nargs="*", help="""
                        Block devices to be included in this Stratis pool.""",
                        version=F45)
        op.add_argument("--useexisting", dest="preexist", action="store_true",
                        default=False, version=F45, help="""
                        Use an existing Stratis pool. Do not specify blockdevs
                        when using this option.""")
        op.add_argument("--encrypted", action="store_true", default=False,
                        version=F45, help="""
                        Encrypt this Stratis pool.""")
        op.add_argument("--passphrase", version=F45, help="""
                        Passphrase to use for encrypting this Stratis pool.
                        Only valid with --encrypted.""")
        op.add_argument("--overprovisioning", action="store_true", default=False,
                        version=F45, help="""
                        Enable overprovisioning for this Stratis pool.""")
        return op

    def parse(self, args):
        (ns, extra) = self.op.parse_known_args(args=args, lineno=self.lineno)
        if not ns.blockdevs:
            if extra:
                ns.blockdevs = extra
                extra = []
            elif ns.name:
                ns.blockdevs = ns.name[1:]
                ns.name = [ns.name[0]]

        pool = self.dataClass()   # pylint: disable=not-callable
        self.set_to_obj(ns, pool)
        pool.lineno = self.lineno

        if not ns.name:
            raise KickstartParseError(_("stratispool must be given a pool name"), lineno=self.lineno)

        if not any([ns.blockdevs, ns.preexist]):
            raise KickstartParseError(_("stratispool must be given a list of blockdevs"), lineno=self.lineno)
        elif ns.blockdevs and ns.preexist:
            raise KickstartParseError(_("Members may not be specified for preexisting stratispool"), lineno=self.lineno)

        if ns.passphrase and not ns.encrypted:
            raise KickstartParseError(_("--passphrase can only be used with --encrypted"), lineno=self.lineno)

        pool.name = ns.name[0]

        if ns.blockdevs:
            pool.blockdevs = ns.blockdevs

        # Check for duplicates in the data list.
        if pool in self.dataList():
            warnings.warn(_("A stratispool with the name %s has already been defined.") % pool.name, KickstartParseWarning)

        return pool

    def dataList(self):
        return self.poolList

    @property
    def dataClass(self):
        return self.handler.StratisPoolData
