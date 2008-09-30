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

__version__ = "0.1"
__revision__ = "$Id$"

import sys
import getopt

from reportlab.pdfgen.canvas import Canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfbase.ttfonts import TTFont, TTFError

def exit_usage():
    print "Usage: %s [-fvS] [-s font-size] -o output.pdf font.ttf..." % (sys.argv[0],)
    print """\
Create a sample sheet from the list of TrueType fonts.

    -v      verbose
    -f      skip broken fonts rather than returning an error
    -S      Don't sort.  Fonts will be displayed in the order specified
            on the command line
"""
    print "Version %s" % (__version__,)
    sys.exit(2)

def verbose_print(s):
    if verbose:
        print s

# Parse arguments
try:
    (options, arguments) = getopt.getopt(sys.argv[1:], "vfSo:s:")
except getopt.GetoptError, exc:
    print >>sys.stderr, "error: %s" % (str(exc),)
    exit_usage()

verbose = False
allow_broken_fonts = False
output_filename = None
font_size = 12.0
sort_fonts = True
top_margin = 1.0 * inch
bottom_margin = 1.0 * inch
for (opt, optarg) in options:
    if opt == '-v':
        verbose = True
    elif opt == '-f':
        allow_broken_fonts = True
    elif opt == '-o':
        output_filename = optarg
    elif opt == '-s':
        font_size = float(optarg)
    elif opt == '-S':
        sort_fonts = False
    else:
        raise AssertionErrror("BUG: unrecognized option %r" % (opt,))
if not arguments:
    print >>sys.stderr, "error: no font(s) specified"
    exit_usage()
if output_filename is None:
    print >>sys.stderr, "error: no output file specified"
    exit_usage()

fonts = []
for i, ttf_filename in enumerate(arguments):
    font_id = "_font%d" % (i,)
    verbose_print("Loading font %s ..." % (ttf_filename,))
    try:
        font = TTFont(font_id, ttf_filename)
    except TTFError, exc:
        if allow_broken_fonts:
            print >>sys.stderr, "warning: skipping font %s: %s" % (ttf_filename, str(exc))
            continue
        else:
            print >>sys.stderr, "error: can't use font %s: %s" % (ttf_filename, str(exc))
            sys.exit(1)

    face_name = font.face.fullName
    # Decode face name to Unicode.  Try UTF-8, and fall back to Latin-1
    if not isinstance(face_name, unicode):
        try:
            face_name = face_name.decode('utf-8')
        except UnicodeDecodeError:
            face_name = face_name.decode('latin1')
    verbose_print("   -> %r" % (face_name,))
    fonts.append((font_id, font, face_name))

# Sort fonts by face_name
if sort_fonts:
    fonts.sort(key=lambda tup: tup[2])

# Register fonts
for (font_id, font, face_name) in fonts:
    verbose_print("Registering font %s ..." % (face_name,))
    pdfmetrics.registerFont(font)

verbose_print("Setting up canvas ...")
page_size = letter
pdf = Canvas(output_filename, pagesize=page_size)
pdf.setStrokeColorRGB(1, 0, 0)

page_height = page_size[1] - top_margin - bottom_margin

i = 0
while i < len(fonts):
    # Render once so we can figure out the bounding box
    text = pdf.beginText(0, 0)
    width = height = 0
    j = i
    page_fonts = [] # fonts shown on this page
    while j < len(fonts):
        (font_id, font, face_name) = fonts[j]
        prev_height = height
        verbose_print("Pre-rendering font %r" % (face_name,))
        text.setFont(font_id, font_size)
        text.textOut(face_name)
        width = max(width, text.getX())
        text.textLine("")
        height = abs(text.getY())
        if height > page_height:
            height = prev_height
            break
        else:
            page_fonts.append(fonts[j])
            j += 1

    # Render again, centering the text
    text = pdf.beginText((page_size[0]-width)/2.0, (page_size[1]+height)/2.0)
    for (font_id, font, face_name) in page_fonts:
        verbose_print("Rendering font %r" % (face_name,))
        text.setFont(font_id, font_size)
        text.textOut(face_name)
        text.textLine("")

    pdf.drawText(text)
    pdf.showPage()
    i += len(page_fonts)

verbose_print("Writing %r" % (output_filename,))
pdf.save()

# vim:set ts=4 sw=4 sts=4 expandtab:
