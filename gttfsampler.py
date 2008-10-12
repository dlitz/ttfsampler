#!/usr/bin/python
# gttfsampler - a GUI interface to ttfsampler
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


__version__ = "0.0"
__revision__ = "$Id$"

import Tkinter as T
import tkFileDialog

import os
import re
import fnmatch

def pack_widget(_w, **kw):
    _w.pack(**kw)
    return _w

FILE_EXTENSIONS = "*.ttf *.otf *.TTF *.OTF" # List of file exstensions. (NB: tcl substitution will happen on this string.)

class MainWindow(T.Frame):
    def __init__(self, master=None):
        T.Frame.__init__(self, master)
        self.master.title("gTTFSampler %s" % (__version__,))
        self.pack(expand=True, fill="both")
        self.widgets = {}
        self.widgets['font_selector'] = pack_widget(MainWindow_FontSelector(self), fill="both", expand=True)
        self.widgets['options_selector'] = pack_widget(MainWindow_OptionsSelector(self), fill="x")
        self.widgets['button_savePDF'] = pack_widget(T.Button(self, text="Save PDF..."))

class MainWindow_FontSelector(T.LabelFrame):
    def __init__(self, master):
        T.LabelFrame.__init__(self, master, text="Input font(s)")
        self.widgets = {}

        # Toolbar
        f = pack_widget(T.Frame(self), fill="x")
        self.widgets['button_addFile'] = pack_widget(T.Button(f, text="Add file(s)..."), side="left", expand=True, fill="x")
        self.widgets['button_addFolder'] = pack_widget(T.Button(f, text="Add folder..."), side="left", expand=True, fill="x")
        self.widgets['button_removeSelected'] = pack_widget(T.Button(f, text="Remove selected"), side="left", expand=True, fill="x")

        # List
        self.widgets['listbox'] = pack_widget(T.Listbox(self, selectmode="extended"), fill="both", expand=True)

        # Add event handlers
        self.widgets['button_addFile']['command'] = self.button_addFile_click
        self.widgets['button_addFolder']['command'] = self.button_addFolder_click
        self.widgets['button_removeSelected']['command'] = self.button_removeSelected_click

    def button_addFile_click(self):
        filetypes = [
            ('TrueType/OpenType fonts', FILE_EXTENSIONS),
            ('All files', '*'),
        ]
        dialog = tkFileDialog.Open(self, multiple=True, filetypes=filetypes)
        filenames = dialog.show()
        if not filenames:   # User pressed "Cancel"
            return
        lb = self.widgets['listbox']
        for filename in filenames:
            lb.insert("end", filename)

    def button_addFolder_click(self):
        dialog = tkFileDialog.Directory(self)
        rootpath = dialog.show()

        if not rootpath:   # User pressed "Cancel"
            return

        # Build a list of globs
        gg = {}
        for g in FILE_EXTENSIONS.split(" "):
            g = g.lower()
            gg[g] = re.compile(fnmatch.translate(g), re.I)
        regexps = gg.values()
        del gg

        lb = self.widgets['listbox']
        for (dirpath, dirnames, filenames) in os.walk(rootpath):
            for filename in filenames:
                for regexp in regexps:
                    if regexp.search(filename):
                        lb.insert("end", os.path.join(dirpath, filename))
                        break

    def button_removeSelected_click(self):
        lb = self.widgets['listbox']

        indices = list(lb.curselection())
        indices.sort(reverse=True)  # Sort in reverse order so we don't delete the wrong items

        for idx in indices:
            lb.delete(idx)

class MainWindow_OptionsSelector(T.LabelFrame):
    def __init__(self, master):
        T.LabelFrame.__init__(self, master, text="Options")
        self.widgets = {}

        # Font size
        f = pack_widget(T.Frame(self), anchor="w")
        pack_widget(T.Label(f, text="Font size:", justify="left"), side="left")
        self.widgets['spinbox_fontSize'] = pack_widget(T.Spinbox(f, from_=1, to=100), side="left")

        # Ignore broken/duplicate fonts
        self.widgets['check_ignoreBad'] = pack_widget(T.Checkbutton(self, text="Ignore broken/duplicate fonts", justify="left"), anchor="w")

        # Specify text
        f = pack_widget(T.Frame(self), anchor="w", fill="x")
        self.widgets['check_specifyText'] = pack_widget(T.Checkbutton(f, text="Specify text:", justify="left"), side="left")
        self.widgets['text_specifyText'] = pack_widget(T.Entry(f), side="left", expand=True, fill="x")

if __name__ == '__main__':
    #root = T.Tk()
    #root.withdraw()
    #top = T.Toplevel(root, class_="GTTFSampler")
    #app = MainWindow(top)
    app = MainWindow()

    # Don't let the window be smaller than its initial size
    #app.master.minsize(app.master.winfo_reqwidth(), app.master.winfo_reqheight())
    app.master.minsize(100, 100)    # Don't let the window get absurdly small

    app.mainloop()

# vim:set ts=4 sw=4 sts=4 expandtab:
