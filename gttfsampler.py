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

__version__ = "0.4"
__revision__ = "$Id$"

import Tkinter as T
import tkFileDialog
import tkMessageBox

import sys
import os
import re
import fnmatch
import threading
import Queue

ttfsampler = None   # This will be imported when the user choses "Save PDF..."

def pack_widget(_w, **kw):
    _w.pack(**kw)
    return _w

FILE_EXTENSIONS = "*.ttf *.otf *.TTF *.OTF" # List of file exstensions. (NB: tcl substitution will happen on this string.)

class GUILog(object):
    def __init__(self, config, queue):
        self.cfg = config
        self.queue = queue

    def debug(self, msg):
        self.queue.put(self._parse(msg))

    def warning(self, msg):
        self.queue.put(('W', self._parse(msg)[1]))

    def error(self, msg):
        self.queue.put(('E', self._parse(msg)[1]))

    def _parse(self, msg):
        if msg.startswith("<") and msg[2:3] == '>':
            return (int(msg[1]), msg[3:])
        else:
            return (0, msg)


class BatchThread(threading.Thread):
    def __init__(self, config, listbox):
        threading.Thread.__init__(self, None, None, self.__class__.__name__)
        self.cfg = config
        self.listbox = listbox
        self.queue = Queue.Queue()
        self.log = GUILog(self.cfg, self.queue)
        self.core = ttfsampler.TTFSampler(self.cfg, self.log)
        self.finished = False
        self.error = None

    def run(self):
        try:
            try:
                self.core.run()
            except ttfsampler.error, exc:
                self.error = str(exc)
            except Exception, exc:
                self.error = str(exc)
                raise
            else:
                self.error = None
                self.queue.put((1, "Finished successfully."))
        finally:
            self.finished = True

    def process_queue(self):
        assert threading.currentThread() is not self

        # Check if the window is scrolled to the bottom

        if self.listbox.yview()[1] == 1.0:
            scroll_to_bottom = True
        else:
            scroll_to_bottom = False

        try:
            while True:
                (loglevel, msg) = self.queue.get_nowait()
                i = self.listbox.index("end")
                if loglevel == 'E':
                    self.listbox.insert(i, "Error: " + msg)
                    self.listbox.itemconfigure(i, background="pink")
                elif loglevel == 'W':
                    self.listbox.insert(i, "Warning: " + msg)
                    self.listbox.itemconfigure(i, background="light yellow")
                elif self.cfg.verbosity >= loglevel:
                    self.listbox.insert(i, msg)
        except Queue.Empty:
            pass

        # Scroll the window to the bottom, if that's where the user wants it.
        if scroll_to_bottom:
            self.listbox.yview("moveto", 1.0)

        if self.finished:
            if self.error is None:
                msgbox = tkMessageBox.Message(title="gTTFSampler", icon="info", parent=self.listbox.master, type="ok", message="PDF file generated successfully.")
                msgbox.show()
            else:
                msgbox = tkMessageBox.Message(title="gTTFSampler", icon="error", parent=self.listbox.master, type="ok", message="Error: %s" % (self.error,))
                msgbox.show()
        else:
            # process the queue in the GUI thread
            self.listbox.master.after(100, self.process_queue)

class MainWindow(T.Frame):
    def __init__(self, master=None):
        T.Frame.__init__(self, master)
        self.master.title("gTTFSampler %s" % (__version__,))
        self.pack(expand=True, fill="both")
        self.widgets = {}
        self.widgets['font_selector'] = pack_widget(MainWindow_FontSelector(self), fill="both", expand=True)
        self.widgets['options_selector'] = pack_widget(MainWindow_OptionsSelector(self), fill="x")
        self.widgets['button_savePDF'] = pack_widget(T.Button(self, text="Save PDF..."))

        self.widgets['button_savePDF']['command'] = self.button_savePDF_click

    def button_savePDF_click(self):
        font_filenames = self.widgets['font_selector'].get_filenames()
        if not font_filenames:
            msgbox = tkMessageBox.Message(title="gTTFSampler Error", icon="error", parent=self, type="ok", message="No font(s) selected.")
            msgbox.show()
            return

        options = self.widgets['options_selector'].get_options()

        dialog = tkFileDialog.SaveAs(self, title="Save PDF...", defaultextension='.pdf', filetypes=[('PDF file', '*.pdf')])
        output_filename = dialog.show()
        if not output_filename:   # User pressed "Cancel"
            return

        cfg = ttfsampler.Config()
        cfg.verbosity = 1
        cfg.font_size = float(options['fontSize'])
        cfg.allow_broken_fonts = True   # Always skip broken/duplicate fonts
        cfg.specified_text = options['specifyText']
        cfg.sort_fonts = options['sort']
        cfg.input_filenames = font_filenames
        cfg.output_filename = output_filename

        logwindow = T.Toplevel()
        logwindow.title("ttfsampler output")
        logwindow.geometry("600x300")
        logwindow.minsize(100, 100)
        logwidget = ScrolledListbox(logwindow)
        logwidget.pack(expand=True, fill="both")

        t = BatchThread(cfg, logwidget)
        t.process_queue()
        t.start()


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
        self.widgets['listbox'] = pack_widget(ScrolledListbox(self), fill="both", expand=True)

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
            lb.insert("end", os.path.abspath(filename))

    def button_addFolder_click(self):
        kw = {}
        if os.environ.has_key('SystemRoot'):    # HACK for win32
            kw['initialdir'] = os.path.join(os.environ['SystemRoot'], u"Fonts")
        dialog = tkFileDialog.Directory(self, **kw)
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
            dirnames.sort()
            filenames.sort()
            for filename in filenames:
                for regexp in regexps:
                    if regexp.search(filename):
                        lb.insert("end", os.path.abspath(os.path.join(dirpath, filename)))
                        break

    def button_removeSelected_click(self):
        lb = self.widgets['listbox']

        indices = list(lb.curselection())
        indices.sort(reverse=True)  # Sort in reverse order so we don't delete the wrong items

        for idx in indices:
            lb.delete(idx)

    def get_filenames(self):
        return self.widgets['listbox'].get(0, "end")

class ScrolledListbox(T.Frame):
    def __init__(self, master):
        T.Frame.__init__(self, master)
        self.widgets = {}

        self.widgets['listbox'] = pack_widget(T.Listbox(self, selectmode="extended"), side="left", expand=True, fill="both")
        self.widgets['scrollbar'] = pack_widget(T.Scrollbar(self), side="right", fill="y")

        # Connect the listbox to the scrollbar
        self.widgets['listbox']['yscrollcommand'] = self.widgets['scrollbar'].set
        self.widgets['scrollbar']['command'] = self.widgets['listbox'].yview

        # Proxy listbox methods
        for name in ('curselection', 'delete', 'get', 'index', 'insert', 'itemconfigure', 'yview'):
            setattr(self, name, getattr(self.widgets['listbox'], name))

class MainWindow_OptionsSelector(T.LabelFrame):
    def __init__(self, master):
        T.LabelFrame.__init__(self, master, text="Options")
        self.widgets = {}
        self.vars = {
            'fontSize': T.IntVar(master),
            'specifyText_check': T.BooleanVar(master),
            'specifyText_text': T.StringVar(master),
            'sort': T.BooleanVar(master),
        }
        self.vars['fontSize'].set(12)
        self.vars['specifyText_check'].set(False)
        self.vars['specifyText_text'].set("The quick brown fox jumps over the lazy dog.")
        self.vars['sort'].set(True),

        # Font size
        f = pack_widget(T.Frame(self), anchor="w")
        pack_widget(T.Label(f, text="Font size:", justify="left"), side="left")
        self.widgets['spinbox_fontSize'] = pack_widget(T.Spinbox(f, from_=1, to=100, textvariable=self.vars['fontSize']), side="left")

        # Specify text
        f = pack_widget(T.Frame(self), anchor="w", fill="x")
        self.widgets['check_specifyText'] = pack_widget(T.Checkbutton(f, text="Specify text:", justify="left", variable=self.vars['specifyText_check']), side="left")
        self.widgets['text_specifyText'] = pack_widget(T.Entry(f, textvariable=self.vars['specifyText_text']), side="left", expand=True, fill="x")

        # Sort fonts
        self.widgets['check_sort'] = pack_widget(T.Checkbutton(self, text="Sort fonts by name", justify="left", variable=self.vars['sort']), anchor="w")

    def get_options(self):
        retval = {}
        retval['fontSize'] = self.vars['fontSize'].get()
        retval['sort'] = self.vars['sort'].get()
        if self.vars['specifyText_check'].get():
            retval['specifyText'] = self.vars['specifyText_text'].get()
        else:
            retval['specifyText'] = None
        return retval

if __name__ == '__main__':
    # Check if reportlab is installed
    try:
        import reportlab
    except ImportError:
        msgbox = tkMessageBox.Message(title="gTTFSampler Error", icon="error", type="ok", message="The ReportLab Toolkit is not installed.")
        msgbox.show()
        sys.exit(1)

    # Try to import ttfsampler (this should always work)
    import ttfsampler

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
