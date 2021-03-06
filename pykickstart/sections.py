#
# sections.py:  Kickstart file sections.
#
# Chris Lumens <clumens@redhat.com>
#
# Copyright 2011-2016 Red Hat, Inc.
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
"""
This module exports the classes that define a section of a kickstart file.  A
section is a chunk of the file starting with a %tag and ending with a %end.
Examples of sections include %packages, %pre, and %post.

You may use this module to define your own custom sections which will be
treated just the same as a predefined one by the kickstart parser.  All that
is necessary is to create a new subclass of Section and call
parser.registerSection with an instance of your new class.
"""
from pykickstart.constants import KS_SCRIPT_PRE, KS_SCRIPT_POST, KS_SCRIPT_TRACEBACK, \
                                  KS_SCRIPT_PREINSTALL, KS_MISSING_IGNORE, KS_MISSING_PROMPT
from pykickstart.errors import KickstartParseError, formatErrorMsg
from pykickstart.options import KSOptionParser
from pykickstart.version import FC4, F7, F9, F18, F21, F22

from pykickstart.i18n import _

# import static typing information if avaialble
# pylint: disable=unused-import
try:
    from typing import Any, Dict, List, Union
    from pykickstart.base import BaseHandler
except ImportError:
    pass
# pylint: enable=unused-import

class Section(object):
    """The base class for defining kickstart sections.  You are free to
       subclass this as appropriate.

       Class attributes:

       allLines    -- Does this section require the parser to call handleLine
                      for every line in the section, even blanks and comments?
       sectionOpen -- The string that denotes the start of this section.  You
                      must start your tag with a percent sign.
       timesSeen   -- This attribute is for informational purposes only.  It is
                      incremented every time handleHeader is called to keep
                      track of the number of times a section of this type is
                      seen.
    """
    allLines = False
    sectionOpen = ""
    timesSeen = 0

    def __init__(self, handler, **kwargs):  # type: (Section, BaseHandler, **Any) -> None
        """Create a new Script instance.  At the least, you must pass in an
           instance of a baseHandler subclass.

           Valid kwargs:

           dataObj -- A class that should be populated by this Section.  It almost
                      always should be Script, or some subclass of it.
        """
        self.handler = handler
        self.version = self.handler.version

        # FIXME: The type should be some sort of Callable but mypy doesn't give a way to
        # annotate a callable with optional or keyword args.
        self.dataObj = kwargs.get("dataObj", None)  # type: ignore

    def finalize(self): # type: (Section) -> None
        """This method is called when the %end tag for a section is seen.  It
           is not required to be provided.
        """
        pass

    def handleLine(self, line): # type: (Section, str) -> None
        """This method is called for every line of a section.  Take whatever
           action is appropriate.  While this method is not required to be
           provided, not providing it does not make a whole lot of sense.

           Arguments:

           line -- The complete line, with any trailing newline.
        """
        pass

    # pylint: disable=unused-argument
    def handleHeader(self, lineno, args):   # type: (Section, int, List[str]) -> None
        """This method is called when the opening tag for a section is seen.
           Not all sections will need this method, though all provided with
           kickstart include one.

           Arguments:

           args -- A list of all strings passed as arguments to the section
                   opening tag.
        """
        self.timesSeen += 1
    # pylint: enable=unused-argument

    @property
    def seen(self):
        """This property is given for consistency with KickstartCommand objects
           only.  It simply returns whether timesSeen is non-zero.
        """
        return self.timesSeen > 0

class NullSection(Section):
    """This defines a section that pykickstart will recognize but do nothing
       with.  If the parser runs across a %section that has no object registered,
       it will raise an error.  Sometimes, you may want to simply ignore those
       sections instead.  This class is useful for that purpose.
    """
    def __init__(self, *args, **kwargs):    # type: (NullSection, *Any, **Any) -> None
        """Create a new NullSection instance.  You must pass a sectionOpen
           parameter (including a leading '%') for the section you wish to
           ignore.
        """
        Section.__init__(self, *args, **kwargs)
        self.sectionOpen = kwargs.get("sectionOpen")    # type: str

class ScriptSection(Section):
    allLines = True

    def __init__(self, *args, **kwargs):    # type: (ScriptSection, *Any, **Any) -> None
        Section.__init__(self, *args, **kwargs)
        self._script = {}   # type: Dict[str, Any]
        self._resetScript()

    def _getParser(self):   # type: (ScriptSection) -> KSOptionParser
        op = KSOptionParser(self.version)
        op.add_argument("--erroronfail", dest="errorOnFail", action="store_true", default=False)
        op.add_argument("--interpreter", dest="interpreter", default="/bin/sh")
        op.add_argument("--log", "--logfile", dest="log")
        return op

    def _resetScript(self): # type: (ScriptSection) -> None
        self._script = {"interp": "/bin/sh", "log": None, "errorOnFail": False,
                        "lineno": None, "chroot": False, "body": []}

    def handleLine(self, line): # type: (ScriptSection, str) -> None
        self._script["body"].append(line)

    def finalize(self): # type: (ScriptSection) -> None
        if " ".join(self._script["body"]).strip() == "":
            return

        kwargs = {"interp": self._script["interp"],
                  "inChroot": self._script["chroot"],
                  "lineno": self._script["lineno"],
                  "logfile": self._script["log"],
                  "errorOnFail": self._script["errorOnFail"],
                  "type": self._script["type"]}

        if self.dataObj is not None:
            s = self.dataObj (self._script["body"], **kwargs)
            self._resetScript()
            self.handler.scripts.append(s)

    def handleHeader(self, lineno, args):   # type: (ScriptSection, int, List[str]) -> None
        """Process the arguments to a %pre/%post/%traceback header for later
           setting on a Script instance once the end of the script is found.
           This method may be overridden in a subclass if necessary.
        """
        Section.handleHeader(self, lineno, args)
        op = self._getParser()

        ns = op.parse_args(args=args[1:], lineno=lineno)

        self._script["interp"] = ns.interpreter
        self._script["lineno"] = lineno
        self._script["log"] = ns.log
        self._script["errorOnFail"] = ns.errorOnFail
        if hasattr(ns, "nochroot"):
            self._script["chroot"] = not ns.nochroot

class PreScriptSection(ScriptSection):
    sectionOpen = "%pre"

    def _resetScript(self): # type: (PreScriptSection) -> None
        ScriptSection._resetScript(self)
        self._script["type"] = KS_SCRIPT_PRE

class PreInstallScriptSection(ScriptSection):
    sectionOpen = "%pre-install"

    def _resetScript(self): # type: (PreInstallScriptSection) -> None
        ScriptSection._resetScript(self)
        self._script["type"] = KS_SCRIPT_PREINSTALL

class PostScriptSection(ScriptSection):
    sectionOpen = "%post"

    def _getParser(self):   # type: (PostScriptSection) -> KSOptionParser
        op = ScriptSection._getParser(self)
        op.add_argument("--nochroot", dest="nochroot", action="store_true", default=False)
        return op

    def _resetScript(self): # type: (PostScriptSection) -> None
        ScriptSection._resetScript(self)
        self._script["chroot"] = True
        self._script["type"] = KS_SCRIPT_POST

class TracebackScriptSection(ScriptSection):
    sectionOpen = "%traceback"

    def _resetScript(self): # type: (TracebackScriptSection) -> None
        ScriptSection._resetScript(self)
        self._script["type"] = KS_SCRIPT_TRACEBACK

class PackageSection(Section):
    sectionOpen = "%packages"

    def handleLine(self, line): # type: (PackageSection, str) -> None
        h = line.partition('#')[0]
        line = h.rstrip()
        self.handler.packages.add([line])

    def handleHeader(self, lineno, args):   # type: (PackageSection, int, List[str]) -> None
        """Process the arguments to the %packages header and set attributes
           on the Version's Packages instance appropriate.  This method may be
           overridden in a subclass if necessary.
        """
        Section.handleHeader(self, lineno, args)
        op = KSOptionParser(version=self.version)
        op.add_argument("--excludedocs", action="store_true", default=False)
        op.add_argument("--ignoremissing", action="store_true", default=False)
        op.add_argument("--nobase", action="store_true", default=False, deprecated=F18, removed=F22)
        op.add_argument("--nocore", action="store_true", default=False, introduced=F21)
        op.add_argument("--ignoredeps", dest="resolveDeps", action="store_false", deprecated=FC4, removed=F9)
        op.add_argument("--resolvedeps", dest="resolveDeps", action="store_true", deprecated=FC4, removed=F9)
        op.add_argument("--default", dest="defaultPackages", action="store_true", default=False, introduced=F7)
        op.add_argument("--instLangs", default=None, introduced=F9)
        op.add_argument("--multilib", dest="multiLib", action="store_true", default=False, introduced=F18)

        ns = op.parse_args(args=args[1:], lineno=lineno)

        if ns.defaultPackages and ns.nobase:
            raise KickstartParseError(formatErrorMsg(lineno, msg=_("--default and --nobase cannot be used together")))
        elif ns.defaultPackages and ns.nocore:
            raise KickstartParseError(formatErrorMsg(lineno, msg=_("--default and --nocore cannot be used together")))

        self.handler.packages.excludeDocs = ns.excludedocs
        self.handler.packages.addBase = not ns.nobase
        if ns.ignoremissing:
            self.handler.packages.handleMissing = KS_MISSING_IGNORE
        else:
            self.handler.packages.handleMissing = KS_MISSING_PROMPT

        if ns.defaultPackages:
            self.handler.packages.default = True

        if ns.instLangs is not None:
            self.handler.packages.instLangs = ns.instLangs

        self.handler.packages.nocore = ns.nocore
        self.handler.packages.multiLib = ns.multiLib
        self.handler.packages.seen = True
