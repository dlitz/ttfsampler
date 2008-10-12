#!/usr/bin/python
# ttfsampler - Generates a PDF sample sheet from a list of TrueType fonts.
###########################################################################
# Copyright (c) 2008 Dwayne C. Litzenberger <dlitz@dlitz.net>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
###########################################################################

__version__ = "0.4"
__revision__ = "$Id$"

import sys
import getopt
import locale
import logging

from reportlab.pdfgen.canvas import Canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfbase.ttfonts import TTFont, TTFError

VERBOSITY_1 = "<1>"
VERBOSITY_2 = "<2>"
VERBOSITY_3 = "<3>"

def exit_usage():
    print "Usage: %s [-fSv] [-s font-size] [-t text] -o output.pdf font.ttf..." % (sys.argv[0],)
    print """\
Create a sample sheet from a list of TrueType fonts.

    -f      Skip broken or duplicate fonts rather than returning an error.
    -S      Don't sort.  Fonts will be displayed in the order specified
            on the command line.
    -t      Specify text to render instead of the default of using the font
            name.  (When this option is enabled, the font name will be
            displayed before the rendered text.)
    -v      Increase verbosity.
"""
    print "Version %s" % (__version__,)
    sys.exit(2)

class Config(object):
    def __init__(self):
        self.verbosity = 0
        self.allow_broken_fonts = False
        self.input_filenames = None
        self.output_filename = None
        self.font_size = 12.0
        self.sort_fonts = True
        self.top_margin = 1.0 * inch
        self.bottom_margin = 1.0 * inch
        self.specified_text = None

class error(Exception):
    pass

class TTFSampler(object):
    def __init__(self, config=None, log=None):
        if config is None:
            self.cfg = Config()
        else:
            self.cfg = config

        if log is None:
            self.log = self.make_logger()
        else:
            self.log = log

    def make_logger(self):
        return logging.getLogger(self.__class__.__name__)

    def verbose_print(self, verbosity, s):
        if self.cfg.verbosity >= verbosity:
            self.log.debug("<%d>%s" % (verbosity, s))

    def print_error(self, msg):
        self.log.error(msg)

    def print_warning(self, msg):
        self.log.warning(msg)

    def run(self):
        self.load_fonts()
        self.register_fonts()
        self.render()
        self.save()

    def render_line(self, text, font_id, font_size, face_name):
        start_x = text.getX()
        if self.cfg.specified_text is not None:
            text.setFont(font_id, font_size)
            text.textOut(self.cfg.specified_text)
            text.setFont("Times-Roman", font_size)
            text.textOut(u"  (%s)" % (face_name,))
        else:
            text.setFont(font_id, font_size)
            text.textOut(face_name)
        end_x = text.getX()
        text.textLine("")
        width = abs(end_x - start_x)
        return width

    def load_fonts(self):
        self.log.debug(VERBOSITY_1 + "Loading fonts...")
        self.fonts = []
        psfontnames = {}
        self.skipped_fonts = 0
        for i, ttf_filename in enumerate(self.cfg.input_filenames):
            font_id = "_font%d" % (i,)
            self.log.debug(VERBOSITY_2 + "  Loading font %s ..." % (ttf_filename,))
            try:
                font = TTFont(font_id, ttf_filename)
            except TTFError, exc:
                if self.cfg.allow_broken_fonts:
                    self.log.warning("skipping font %s: %s" % (ttf_filename, str(exc)))
                    self.skipped_fonts += 1
                    continue
                else:
                    msg = "can't use font %s: %s" % (ttf_filename, str(exc))
                    self.log.error(msg)
                    raise error(msg)

            face_name = font.face.fullName
            # Decode face name to Unicode.  Try UTF-8, and fall back to Latin-1
            if not isinstance(face_name, unicode):
                try:
                    face_name = face_name.decode('utf-8')
                except UnicodeDecodeError:
                    face_name = face_name.decode('latin1')

            if font.face.name in psfontnames:
                if self.cfg.allow_broken_fonts:
                    self.log.warning("skipping font %s; has same name (%r) as font %s" % (ttf_filename, font.face.name, psfontnames[font.face.name]))
                    self.skipped_fonts += 1
                    continue
                else:
                    msg = "error: font %s has same name (%r) as font %s" % (ttf_filename, font.face.name, psfontnames[font.face.name])
                    self.log.error(msg)
                    raise error(msg)
            else:
                psfontnames[font.face.name] = ttf_filename

            self.log.debug(VERBOSITY_3 + "  -> %r" % (face_name,))
            self.fonts.append((font_id, font, face_name))

        # Sort fonts by face_name
        if self.cfg.sort_fonts:
            self.fonts.sort(key=lambda tup: tup[2])

    def register_fonts(self):
        # Register fonts
        self.log.debug(VERBOSITY_1 + "Registering %d fonts..." % (len(self.fonts),))
        for (font_id, font, face_name) in self.fonts:
            self.log.debug(VERBOSITY_2 + "  Registering font %r ..." % (face_name,))
            pdfmetrics.registerFont(font)

    def render(self):
        self.log.debug(VERBOSITY_2 + "Setting up canvas ...")
        page_size = letter
        self.pdf = Canvas(self.cfg.output_filename, pagesize=page_size)
        self.pdf.setStrokeColorRGB(1, 0, 0)

        page_height = page_size[1] - self.cfg.top_margin - self.cfg.bottom_margin

        i = 0
        self.page_count = 0
        while i < len(self.fonts):
            self.page_count += 1
            self.log.debug(VERBOSITY_1 + "Rendering page %d ..." % (self.page_count,))

            # Render once so we can figure out the bounding box
            text = self.pdf.beginText(0, 0)
            width = height = 0
            j = i
            page_fonts = [] # fonts shown on this page
            while j < len(self.fonts):
                (font_id, font, face_name) = self.fonts[j]
                prev_height = height
                self.log.debug(VERBOSITY_3 + "  Pre-rendering font %r" % (face_name,))
                linewidth = self.render_line(text, font_id, self.cfg.font_size, face_name)
                width = max(width, linewidth)
                height = abs(text.getY())
                if height > page_height:
                    height = prev_height
                    break
                else:
                    page_fonts.append(self.fonts[j])
                    j += 1

            # Render again, centering the text
            text = self.pdf.beginText((page_size[0]-width)/2.0, (page_size[1]+height)/2.0)
            for (font_id, font, face_name) in page_fonts:
                self.log.debug(VERBOSITY_2 + "  Rendering font %r" % (face_name,))
                self.render_line(text, font_id, self.cfg.font_size, face_name)

            self.pdf.drawText(text)
            self.pdf.showPage()
            i += len(page_fonts)

        if self.skipped_fonts:
            self.log.warning("skipped %d fonts" % (self.skipped_fonts,))

    def save(self):
        self.log.debug(VERBOSITY_1 + "Writing %d pages (%d fonts) to %r" % (self.page_count, len(self.fonts), self.cfg.output_filename,))
        self.pdf.save()

class CLILog(object):
    def __init__(self, config):
        self.cfg = config

    def debug(self, msg):
        if msg.startswith(VERBOSITY_3) and self.cfg.verbosity >= 3:
            print msg[len(VERBOSITY_3):]
        elif msg.startswith(VERBOSITY_2) and self.cfg.verbosity >= 2:
            print msg[len(VERBOSITY_2):]
        elif msg.startswith(VERBOSITY_1) and self.cfg.verbosity >= 1:
            print msg[len(VERBOSITY_1):]

    def warning(self, msg):
        print >>sys.stderr, "warning: %s" % (msg,)

    def error(self, msg):
        print >>sys.stderr, "error: %s" % (msg,)

class CLI(object):
    def __init__(self):
        self.cfg = Config()
        self.log = CLILog(self.cfg)

    def run(self):
        self.parse_args()
        TTFSampler(self.cfg, self.log).run()

    def parse_args(self, args=None, program_name=None):
        if program_name is None:
            program_name = sys.argv[0]
        if args is None:
            args = sys.argv[1:]

        # Parse arguments
        try:
            (options, arguments) = getopt.getopt(args, "vfSo:s:t:")
        except getopt.GetoptError, exc:
            self.log.error(str(exc))
            exit_usage()

        for (opt, optarg) in options:
            if opt == '-v':
                self.cfg.verbosity += 1
            elif opt == '-f':
                self.cfg.allow_broken_fonts = True
            elif opt == '-o':
                self.cfg.output_filename = optarg
            elif opt == '-s':
                self.cfg.font_size = float(optarg)
            elif opt == '-S':
                self.cfg.sort_fonts = False
            elif opt == '-t':
                self.cfg.specified_text = optarg.decode(locale.getpreferredencoding())
            else:
                raise AssertionErrror("BUG: unrecognized option %r" % (opt,))
        if not arguments:
            self.log.error("no font(s) specified")
            exit_usage()
        if self.cfg.output_filename is None:
            self.log.error("no output file specified")
            exit_usage()
        self.cfg.input_filenames = arguments

if __name__ == '__main__':
    CLI().run()

# vim:set ts=4 sw=4 sts=4 expandtab:
