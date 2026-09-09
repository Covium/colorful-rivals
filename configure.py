#!/usr/bin/env python3
"""Tk color picker used by the source tree and packaged application."""
import json
import queue
import subprocess
import sys
import threading

try:
    import tkinter as tk
    from tkinter import colorchooser, filedialog, font as tkfont, messagebox, ttk
except ImportError:
    raise SystemExit('Tkinter is unavailable in this source Python installation.')

import build
from paths import find_games, resolve_game, resolve_retoc

BACKGROUND = '#000000'
FOREGROUND = '#FFFFFF'
CONTROL = '#CCC9CD'
ACCENT = '#E76238'
CONTROL_TEXT = '#000000'
ORDER = ['player', 'none', 'incomplete', 'complete', 'encount']
LABELS = {
    'player': 'Player',
    'none': 'Not raced yet',
    'incomplete': 'Raced, not won',
    'complete': 'Defeated',
    'encount': 'Currently racing',
}
SWATCHES = {'player': '#FF6D00', 'none': '#2979FF', 'incomplete': '#FFD600',
            'complete': '#00C853', 'encount': '#FF1744'}


def draw_control_surface(canvas, color):
    """Draw a borderless square surface behind a custom control."""
    width = max(canvas.winfo_width(), 1)
    height = max(canvas.winfo_height(), 1)
    canvas.delete('surface')
    canvas.create_rectangle(0, 0, width, height,
                            fill=color, outline=color, width=0, tags='surface')
    canvas.tag_lower('surface')


class FlatButton(tk.Canvas):
    def __init__(self, parent, text, command):
        font = tkfont.nametofont('TkDefaultFont')
        self.command = command
        self.enabled = True
        self.hovered = False
        self.pressed = False
        width = font.measure(text) + 22
        height = font.metrics('linespace') + 14
        super().__init__(parent, width=width, height=height, background=BACKGROUND,
                         highlightthickness=0, borderwidth=0, relief='flat',
                         cursor='hand2', takefocus=True)
        self.label = self.create_text(width / 2, height / 2, text=text,
                                      fill=CONTROL_TEXT, font=font)
        self.bind('<Configure>', self.redraw)
        self.bind('<Enter>', self.enter)
        self.bind('<Leave>', self.leave)
        self.bind('<ButtonPress-1>', self.press)
        self.bind('<ButtonRelease-1>', self.release)
        self.bind('<space>', self.keyboard_activate)
        self.bind('<Return>', self.keyboard_activate)
        self.redraw()

    def color(self):
        if not self.enabled:
            return '#747276'
        return ACCENT if self.hovered or self.pressed else CONTROL

    def redraw(self, _event=None):
        draw_control_surface(self, self.color())
        self.coords(self.label, self.winfo_width() / 2, self.winfo_height() / 2)
        self.itemconfigure(self.label, fill=CONTROL_TEXT if self.enabled else '#2B2A2B')
        self.tag_raise(self.label)

    def enter(self, _event=None):
        if self.enabled:
            self.hovered = True
            self.redraw()

    def leave(self, _event=None):
        self.hovered = False
        self.pressed = False
        self.redraw()

    def press(self, _event=None):
        if self.enabled:
            self.focus_set()
            self.pressed = True
            self.redraw()

    def release(self, _event=None):
        if self.enabled and self.pressed:
            self.pressed = False
            self.redraw()
            self.command()

    def keyboard_activate(self, _event=None):
        if self.enabled:
            self.command()
        return 'break'

    def set_enabled(self, enabled):
        self.enabled = enabled
        self.hovered = False
        self.pressed = False
        self.configure(cursor='hand2' if enabled else '')
        self.redraw()


class FlatField(tk.Canvas):
    def __init__(self, parent, child_factory, width, height):
        super().__init__(parent, width=width, height=height, background=BACKGROUND,
                         highlightthickness=0, borderwidth=0, relief='flat')
        self.hovered = False
        self.child = child_factory(self)
        self.window = self.create_window(7, height / 2, anchor='w', window=self.child)
        self.bind('<Configure>', self.redraw)
        for widget in (self, self.child):
            widget.bind('<Enter>', self.enter, add='+')
            widget.bind('<Leave>', self.leave, add='+')
        self.redraw()

    def color(self):
        return ACCENT if self.hovered else CONTROL

    def redraw(self, _event=None):
        color = self.color()
        draw_control_surface(self, color)
        width = max(1, self.winfo_width() - 14)
        height = max(1, self.winfo_height() - 6)
        self.coords(self.window, 7, self.winfo_height() / 2)
        self.itemconfigure(self.window, width=width, height=height)
        self.child.configure(background=color)
        self.tag_raise(self.window)

    def enter(self, _event=None):
        self.hovered = True
        self.redraw()

    def leave(self, _event=None):
        self.hovered = False
        self.redraw()


class FlatEntry(FlatField):
    def __init__(self, parent, textvariable, width=20):
        font = tkfont.nametofont('TkDefaultFont')

        def make_entry(container):
            return tk.Entry(container, textvariable=textvariable, relief='flat', borderwidth=0,
                            highlightthickness=0, foreground=CONTROL_TEXT,
                            insertbackground=CONTROL_TEXT, selectbackground=ACCENT,
                            selectforeground=CONTROL_TEXT, font=font)

        super().__init__(parent, make_entry, max(140, font.measure('0') * width + 14),
                         font.metrics('linespace') + 14)


class FlatText(FlatField):
    def __init__(self, parent, rows=8, columns=70):
        font = tkfont.nametofont('TkFixedFont')

        def make_text(container):
            return tk.Text(container, wrap='word', state='disabled', relief='flat',
                           borderwidth=0, highlightthickness=0, foreground=CONTROL_TEXT,
                           insertbackground=CONTROL_TEXT, selectbackground=ACCENT,
                           selectforeground=CONTROL_TEXT, font=font)

        super().__init__(parent, make_text, font.measure('0') * columns + 14,
                         font.metrics('linespace') * rows + 12)

    def set_state(self, state):
        self.child.configure(state=state)

    def insert(self, *args):
        return self.child.insert(*args)

    def see(self, *args):
        return self.child.see(*args)


class App:
    def __init__(self, root):
        self.root = root
        self.busy = False
        self.events = queue.Queue()
        self.colors = {}
        self.icon_image = None
        root.title('TXR Colorful Rivals')
        root.minsize(640, 480)
        root.configure(background=BACKGROUND)
        self.apply_icon()
        self.configure_theme()
        frame = ttk.Frame(root, padding=18)
        frame.pack(fill='both', expand=True)
        frame.columnconfigure(1, weight=1)
        ttk.Label(frame, text='Tokyo Xtreme Racer | Colorful Rivals',
                  font=('', 15, 'bold'), style='Header.TLabel').grid(
                      row=0, column=0, columnspan=4, sticky='w')
        ttk.Label(frame, text='Choose a color, or leave its field empty to keep the original.').grid(row=1, column=0, columnspan=4, sticky='w', pady=(8, 12))
        build.ensure_data_files()
        config = build.read_config(build.DATA_ROOT / 'colors.json')
        settings = build.read_settings()
        for row, key in enumerate(ORDER, 2):
            variable = tk.StringVar(value=config['colors'][key] or '')
            self.colors[key] = variable
            ttk.Label(frame, text=LABELS[key]).grid(row=row, column=0, sticky='w', padx=(0, 14))
            entry = FlatEntry(frame, variable, width=20)
            entry.grid(row=row, column=1, sticky='ew', pady=3)
            FlatButton(frame, text='Choose…', command=lambda k=key: self.pick(k)).grid(
                row=row, column=2, padx=6)
            FlatButton(frame, text='Original', command=lambda v=variable: v.set('')).grid(
                row=row, column=3)
        self.game = tk.StringVar(value=settings['game_path'] or '')
        ttk.Label(frame, text='Game folder').grid(row=7, column=0, sticky='w', pady=(18, 4))
        game_entry = FlatEntry(frame, self.game)
        game_entry.grid(row=7, column=1, columnspan=2, sticky='ew',
                        padx=(0, 6), pady=(18, 4))
        FlatButton(frame, text='Browse…', command=self.browse_game).grid(
            row=7, column=3, pady=(18, 4))
        FlatButton(frame, text='Find game', command=self.detect).grid(row=8, column=3, pady=5)
        ttk.Label(frame, text='Close Tokyo Xtreme Racer before installing.').grid(row=8, column=0, columnspan=3, sticky='w')
        buttons = ttk.Frame(frame)
        buttons.grid(row=9, column=0, columnspan=4, sticky='ew', pady=12)
        self.save_button = FlatButton(buttons, text='Save settings', command=self.save_clicked)
        self.save_button.pack(side='left')
        self.build_button = FlatButton(buttons, text='Build only', command=lambda: self.start(False))
        self.build_button.pack(side='left', padx=8)
        self.install_button = FlatButton(buttons, text='Build and install', command=lambda: self.start(True))
        self.install_button.pack(side='left')
        self.status = tk.StringVar(value='Ready')
        ttk.Label(frame, textvariable=self.status).grid(row=10, column=0, columnspan=4, sticky='w')
        self.log = FlatText(frame, rows=8, columns=70)
        self.log.grid(row=11, column=0, columnspan=4, sticky='nsew', pady=(8, 0))
        frame.rowconfigure(11, weight=1)
        root.protocol('WM_DELETE_WINDOW', self.close)
        root.after(100, self.poll)
        if not self.game.get():
            root.after(10, self.detect)

    def apply_icon(self):
        icon = build.RESOURCE_ROOT / 'assets' / 'TXR.ico'
        png = build.RESOURCE_ROOT / 'assets' / 'TXR.png'
        try:
            if sys.platform == 'win32':
                self.root.iconbitmap(str(icon))
            else:
                self.icon_image = tk.PhotoImage(file=png)
                self.root.iconphoto(True, self.icon_image)
        except (OSError, tk.TclError):
            pass

    def configure_theme(self):
        style = ttk.Style(self.root)
        if 'clam' in style.theme_names():
            style.theme_use('clam')
        style.configure('TFrame', background=BACKGROUND)
        style.configure('TLabel', background=BACKGROUND, foreground=FOREGROUND)
        style.configure('Header.TLabel', background=BACKGROUND, foreground=ACCENT)

    def pick(self, key):
        value = self.colors[key].get()
        try:
            build.rgb(value)
        except ValueError:
            value = SWATCHES[key]
        chosen = colorchooser.askcolor(value, title=f'{key.title()} color', parent=self.root)[1]
        if chosen:
            self.colors[key].set(chosen.upper())

    def browse_game(self):
        selected = filedialog.askdirectory(title='Select TokyoXtremeRacer installation')
        if selected:
            self.game.set(selected)

    def detect(self):
        def work():
            try:
                self.events.put(('detected', find_games()))
            except Exception as exc:
                self.events.put(('detect-error', str(exc)))
        self.status.set('Looking for TXR in Steam libraries…')
        threading.Thread(target=work, daemon=True).start()

    def save(self):
        config = {'colors': {key: variable.get().strip() or None for key, variable in self.colors.items()}}
        for value in config['colors'].values():
            if value is not None:
                build.rgb(value)
        settings = {'game_path': self.game.get().strip() or None}
        for name, data in [('colors.json', config), ('settings.json', settings)]:
            temp = build.DATA_ROOT / (name + '.tmp')
            temp.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
            temp.replace(build.DATA_ROOT / name)

    def save_clicked(self):
        try:
            self.save()
            self.status.set('Settings saved')
        except (OSError, ValueError) as exc:
            messagebox.showerror('Could not save settings', str(exc))

    def start(self, install):
        if self.busy:
            return
        try:
            resolve_retoc(build.RESOURCE_ROOT)
            if install:
                resolve_game(self.game.get().strip() or None)
            self.save()
        except (OSError, ValueError) as exc:
            messagebox.showerror('Check settings', str(exc))
            return
        self.busy = True
        for button in (self.save_button, self.build_button, self.install_button):
            button.set_enabled(False)
        self.status.set('Building and verifying…')
        if getattr(sys, 'frozen', False):
            command = [sys.executable, '--worker']
        else:
            command = [sys.executable, '-u', str(build.RESOURCE_ROOT / 'app.py'), '--worker']
        if install:
            command.append('--install')

        def work():
            try:
                with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                      text=True, encoding='utf-8', errors='replace',
                                      env={**__import__('os').environ, 'PYTHONIOENCODING': 'utf-8'},
                                      creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0) as process:
                    for line in process.stdout:
                        self.events.put(('log', line))
                    self.events.put(('done', process.wait()))
            except OSError as exc:
                self.events.put(('log', str(exc) + '\n'))
                self.events.put(('done', 1))
        threading.Thread(target=work, daemon=True).start()

    def poll(self):
        while not self.events.empty():
            kind, value = self.events.get()
            if kind == 'log':
                self.log.set_state('normal')
                self.log.insert('end', value)
                self.log.see('end')
                self.log.set_state('disabled')
            elif kind == 'done':
                self.busy = False
                for button in (self.save_button, self.build_button, self.install_button):
                    button.set_enabled(True)
                self.status.set('Finished — see output below' if value == 0 else 'Failed — see the error below')
            elif kind == 'detected':
                if len(value) == 1:
                    self.game.set(str(value[0]))
                    if not self.busy:
                        self.status.set('TXR found')
                elif not self.busy:
                    self.status.set('Multiple installations found — choose with Browse' if value else 'TXR not found — choose its folder with Browse')
            elif kind == 'detect-error' and not self.busy:
                self.status.set('Detection failed — choose the game folder with Browse')
        self.root.after(100, self.poll)

    def close(self):
        if self.busy:
            messagebox.showinfo('Build in progress', 'Please wait for the build to finish before closing.')
        else:
            self.root.destroy()


def main():
    root = tk.Tk()
    try:
        App(root)
    except (OSError, ValueError) as exc:
        messagebox.showerror('Could not open Colorful Rivals', str(exc))
        root.destroy()
        raise SystemExit(1)
    root.mainloop()


if __name__ == '__main__':
    main()
