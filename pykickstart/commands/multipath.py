#
# Chris Lumens <clumens@redhat.com>
# Peter Jones <pjones@redhat.com>
#
# Copyright 2006, 2007 Red Hat, Inc.
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
from pykickstart.base import BaseData, DeprecatedCommand, KickstartCommand
from pykickstart.errors import KickstartParseError, formatErrorMsg
from pykickstart.options import KSOptionParser

from pykickstart.i18n import _

class FC6_MpPathData(BaseData):
    removedKeywords = BaseData.removedKeywords
    removedAttrs = BaseData.removedAttrs

    def __init__(self, *args, **kwargs):
        BaseData.__init__(self, *args, **kwargs)
        self.mpdev = kwargs.get("mpdev", "")
        self.device = kwargs.get("device", "")
        self.rule = kwargs.get("rule", "")

    def __str__(self):
        return " --device=%s --rule=\"%s\"" % (self.device, self.rule)

class FC6_MultiPathData(BaseData):
    removedKeywords = BaseData.removedKeywords
    removedAttrs = BaseData.removedAttrs

    def __init__(self, *args, **kwargs):
        BaseData.__init__(self, *args, **kwargs)
        self.name = kwargs.get("name", "")
        self.paths = kwargs.get("paths", [])

    def __str__(self):
        retval = BaseData.__str__(self)

        for path in self.paths:
            retval += "multipath --name=%s%s\n" % (self.name, path.__str__())

        return retval

class FC6_MultiPath(KickstartCommand):
    removedKeywords = KickstartCommand.removedKeywords
    removedAttrs = KickstartCommand.removedAttrs

    def __init__(self, writePriority=50, *args, **kwargs):
        KickstartCommand.__init__(self, writePriority, *args, **kwargs)
        self.op = self._getParser()

        self.mpaths = kwargs.get("mpaths", [])

    def __str__(self):
        retval = ""
        for mpath in self.mpaths:
            retval += mpath.__str__()

        return retval

    def _getParser(self):
        op = KSOptionParser()
        op.add_argument("--name", required=True)
        op.add_argument("--device", required=True)
        op.add_argument("--rule", required=True)
        return op

    def parse(self, args):
        ns = self.op.parse_args(args=args, lineno=self.lineno)
        dd = FC6_MpPathData()
        self.set_to_obj(ns, dd)
        dd.lineno = self.lineno
        dd.mpdev = dd.name.split('/')[-1]

        parent = None
        for x in range(0, len(self.mpaths)):
            mpath = self.mpaths[x]
            for path in mpath.paths:
                if path.device == dd.device:
                    mapping = {"device": path.device, "multipathdev": path.mpdev}
                    raise KickstartParseError(formatErrorMsg(self.lineno, msg=_("Device '%(device)s' is already used in multipath '%(multipathdev)s'") % mapping))
            if mpath.name == dd.mpdev:
                parent = x

        if parent is None:
            mpath = FC6_MultiPathData(name=dd.name)
            mpath.paths.append(dd)
            return mpath
        else:
            mpath = self.mpaths[parent]
            mpath.paths.append(dd)
            return dd

    def dataList(self):
        return self.mpaths

class F24_MultiPath(DeprecatedCommand):
    def __init__(self):
        DeprecatedCommand.__init__(self)
