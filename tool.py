#!/usr/bin/env python3
"""
Dark Sector PS3 Tool
Made by: dortkoldantaciz | Version: 1
"""
import os, sys, traceback, threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox


class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget; self.text = text; self.tw = None
        widget.bind('<Enter>', self._show); widget.bind('<Leave>', self._hide)
    def _show(self, e=None):
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 2
        self.tw = tk.Toplevel(self.widget); self.tw.wm_overrideredirect(True)
        self.tw.wm_geometry(f"+{x}+{y}")
        tk.Label(self.tw, text=self.text, background='#ffffe0', relief='solid',
                 borderwidth=1, font=('Segoe UI', 8), padx=4, pady=2).pack()
    def _hide(self, e=None):
        if self.tw: self.tw.destroy(); self.tw = None


class DarkSectorTool:
    APP_TITLE = "Dark Sector Tools"
    VERSION = "1"

    def __init__(self, root):
        self.root = root
        self.root.title(f"{self.APP_TITLE} v{self.VERSION}")
        self.root.geometry("640x600")
        self.root.minsize(580, 540)
        self.root.configure(bg='#ffffff')
        # Center on screen
        self.root.update_idletasks()
        w = 640; h = 600
        x = (self.root.winfo_screenwidth() // 2) - (w // 2)
        y = (self.root.winfo_screenheight() // 2) - (h // 2)
        self.root.geometry(f"{w}x{h}+{x}+{y}")
        self._setup_styles()
        self._build_ui()

    def _setup_styles(self):
        s = ttk.Style(); s.theme_use('clam')
        bg = '#ffffff'
        s.configure('TFrame', background=bg)
        s.configure('TLabel', background=bg, foreground='#222', font=('Segoe UI', 9))
        s.configure('Title.TLabel', background=bg, foreground='#222', font=('Segoe UI', 12, 'bold'))
        s.configure('Credit.TLabel', background=bg, foreground='#999', font=('Segoe UI', 8))
        s.configure('Section.TLabel', background=bg, foreground='#333', font=('Segoe UI', 9, 'bold'))
        s.configure('Status.TLabel', background=bg, foreground='#228B22', font=('Segoe UI', 9))
        s.configure('Error.TLabel', background=bg, foreground='#cc0000', font=('Segoe UI', 9))
        s.configure('TButton', font=('Segoe UI', 9), padding=(12, 4), focuscolor='none')
        s.configure('Browse.TButton', font=('Segoe UI', 8), padding=(8, 3), focuscolor='none')
        s.configure('TNotebook', background=bg)
        s.configure('TNotebook.Tab', font=('Segoe UI', 9, 'bold'), padding=(16, 4), focuscolor='none')
        s.configure('TCheckbutton', background=bg, font=('Segoe UI', 9), focuscolor='none')
        s.configure('TRadiobutton', background=bg, font=('Segoe UI', 9), focuscolor='none')
        s.configure('Horizontal.TProgressbar', thickness=6)
        # Remove focus dotted lines
        s.map('TButton', focuscolor=[('!focus', 'none')])
        s.map('TCheckbutton', focuscolor=[('!focus', 'none')])
        s.map('TRadiobutton', focuscolor=[('!focus', 'none')])

    def _build_ui(self):
        main = ttk.Frame(self.root, padding=12); main.pack(fill='both', expand=True)
        hdr = ttk.Frame(main); hdr.pack(fill='x', pady=(0, 8))
        ttk.Label(hdr, text=self.APP_TITLE, style='Title.TLabel').pack(side='left')
        ttk.Label(hdr, text=f"v{self.VERSION}  —  dortkoldantaciz", style='Credit.TLabel').pack(side='right', pady=(4,0))

        nb = ttk.Notebook(main); nb.pack(fill='both', expand=True, pady=(0, 6))
        font_tab = ttk.Frame(nb, padding=8); nb.add(font_tab, text='  Font  ')
        cache_tab = ttk.Frame(nb, padding=8); nb.add(cache_tab, text='  Cache  ')
        self._build_font_tab(font_tab)
        self._build_cache_tab(cache_tab)

        self.status_var = tk.StringVar(value="Ready")
        bot = ttk.Frame(main); bot.pack(fill='x', pady=(4, 0))
        self.status_label = ttk.Label(bot, textvariable=self.status_var, style='Status.TLabel')
        self.status_label.pack(side='left')
        self.progress_var = tk.DoubleVar(value=0)
        ttk.Progressbar(main, variable=self.progress_var, maximum=100).pack(fill='x', pady=(4, 0))

    def _row(self, parent, label, var, browse_cmd, tip=None):
        ttk.Label(parent, text=label, style='Section.TLabel').pack(anchor='w')
        r = ttk.Frame(parent); r.pack(fill='x', pady=(2, 6))
        ttk.Entry(r, textvariable=var, font=('Segoe UI', 9)).pack(side='left', fill='x', expand=True, padx=(0, 6))
        btn = ttk.Button(r, text="Browse...", style='Browse.TButton', command=browse_cmd)
        btn.pack(side='right')
        if tip: ToolTip(btn, tip)

    def _log(self, w, msg):
        w.insert('end', msg + "\n"); w.see('end'); w.update_idletasks()

    def _set_status(self, msg, err=False):
        self.status_var.set(msg)
        self.status_label.configure(style='Error.TLabel' if err else 'Status.TLabel')

    def _browse_file(self, var, ft):
        p = filedialog.askopenfilename(filetypes=ft)
        if p: var.set(p)
    def _browse_dir(self, var):
        p = filedialog.askdirectory()
        if p: var.set(p)
    def _browse_save(self, var, ext, ft):
        p = filedialog.asksaveasfilename(defaultextension=ext, filetypes=ft)
        if p: var.set(p)

    # ── Font Tab ─────────────────────────────────────────────────
    def _build_font_tab(self, parent):
        sub = ttk.Notebook(parent); sub.pack(fill='both', expand=True)
        ext = ttk.Frame(sub, padding=10); sub.add(ext, text=' Extract ')
        rep = ttk.Frame(sub, padding=10); sub.add(rep, text=' Repack ')
        self._build_font_extract(ext)
        self._build_font_repack(rep)

    def _build_font_extract(self, p):
        self.tex_ext_mode = tk.StringVar(value='file')
        rf = ttk.Frame(p); rf.pack(anchor='w', pady=(0, 4))
        r1 = ttk.Radiobutton(rf, text="Single File", variable=self.tex_ext_mode, value='file')
        r1.pack(side='left', padx=(0, 12)); ToolTip(r1, "Extract a single .tga.1 file to PNG")
        r2 = ttk.Radiobutton(rf, text="Batch Folder", variable=self.tex_ext_mode, value='folder')
        r2.pack(side='left'); ToolTip(r2, "Extract all .tga.1 files in a folder")

        self.tex_ext_recursive = tk.BooleanVar(value=False)
        cb = ttk.Checkbutton(p, text="Include subfolders", variable=self.tex_ext_recursive)
        cb.pack(anchor='w', pady=(0, 4)); ToolTip(cb, "Also scan subfolders for .tga.1 files")

        self.tex_ext_input = tk.StringVar()
        self._row(p, "Input (.tga.1)", self.tex_ext_input, self._browse_tex_ext_input, "Select .tga.1 file or folder")
        self.tex_ext_output = tk.StringVar()
        self._row(p, "Output Directory", self.tex_ext_output, lambda: self._browse_dir(self.tex_ext_output), "Where to save PNG files")

        btn = ttk.Button(p, text="Extract to PNG", command=self._do_tex_extract)
        btn.pack(pady=(4, 0)); ToolTip(btn, "Convert .tga.1 textures to editable PNG images")
        self.tex_ext_log = tk.Text(p, height=5, bg='#fafafa', fg='#222', font=('Consolas', 9), relief='solid', bd=1, wrap='word')
        self.tex_ext_log.pack(fill='both', expand=True, pady=(6, 0))

    def _build_font_repack(self, p):
        self.tex_rep_mode = tk.StringVar(value='file')
        rf = ttk.Frame(p); rf.pack(anchor='w', pady=(0, 4))
        r1 = ttk.Radiobutton(rf, text="Single File", variable=self.tex_rep_mode, value='file')
        r1.pack(side='left', padx=(0, 12)); ToolTip(r1, "Repack a single PNG to .tga.1")
        r2 = ttk.Radiobutton(rf, text="Batch Folder", variable=self.tex_rep_mode, value='folder')
        r2.pack(side='left'); ToolTip(r2, "Repack all PNGs in a folder to .tga.1")

        self.tex_rep_recursive = tk.BooleanVar(value=False)
        cb = ttk.Checkbutton(p, text="Include subfolders", variable=self.tex_rep_recursive)
        cb.pack(anchor='w', pady=(0, 4)); ToolTip(cb, "Also scan subfolders for PNG files")

        self.tex_rep_png = tk.StringVar()
        self._row(p, "Edited PNG", self.tex_rep_png, self._browse_tex_rep_png, "Select the edited PNG file or folder")
        self.tex_rep_orig = tk.StringVar()
        self._row(p, "Original .tga.1 (format ref)", self.tex_rep_orig, self._browse_tex_rep_orig, "Select original .tga.1 to detect format/size")
        self.tex_rep_output = tk.StringVar()
        self._row(p, "Output", self.tex_rep_output, self._browse_tex_rep_output, "Where to save the repacked .tga.1")

        btn = ttk.Button(p, text="Repack to .tga.1", command=self._do_tex_repack)
        btn.pack(pady=(4, 0)); ToolTip(btn, "Convert edited PNG back to .tga.1 texture format")
        self.tex_rep_log = tk.Text(p, height=4, bg='#fafafa', fg='#222', font=('Consolas', 9), relief='solid', bd=1, wrap='word')
        self.tex_rep_log.pack(fill='both', expand=True, pady=(6, 0))

    # ── Cache Tab ────────────────────────────────────────────────
    def _build_cache_tab(self, parent):
        sub = ttk.Notebook(parent); sub.pack(fill='both', expand=True)
        ext = ttk.Frame(sub, padding=10); sub.add(ext, text=' Extract ')
        rep = ttk.Frame(sub, padding=10); sub.add(rep, text=' Repack ')
        self._build_cache_extract(ext)
        self._build_cache_repack(rep)

    def _build_cache_extract(self, p):
        self.cache_ext_file = tk.StringVar()
        self._row(p, "Cache File (.cache)", self.cache_ext_file,
                  lambda: self._browse_file(self.cache_ext_file, [("Cache", "*.cache"), ("All", "*.*")]), "Select .cache archive")
        self.cache_ext_output = tk.StringVar()
        self._row(p, "Output Directory", self.cache_ext_output,
                  lambda: self._browse_dir(self.cache_ext_output), "Where to extract files")
        btn = ttk.Button(p, text="Extract Files", command=self._do_cache_extract)
        btn.pack(pady=(4, 0)); ToolTip(btn, "Extract all files from the .cache archive")
        self.cache_ext_log = tk.Text(p, height=8, bg='#fafafa', fg='#222', font=('Consolas', 9), relief='solid', bd=1, wrap='word')
        self.cache_ext_log.pack(fill='both', expand=True, pady=(6, 0))

    def _build_cache_repack(self, p):
        self.cache_rep_orig = tk.StringVar()
        self._row(p, "Original Cache File (.cache)", self.cache_rep_orig,
                  lambda: self._browse_file(self.cache_rep_orig, [("Cache", "*.cache"), ("All", "*.*")]), "Original cache for structure reference")
        self.cache_rep_input = tk.StringVar()
        self._row(p, "Input Directory (modified files)", self.cache_rep_input,
                  lambda: self._browse_dir(self.cache_rep_input), "Folder with modified files")
        self.cache_rep_output = tk.StringVar()
        self._row(p, "Output Cache File (.cache)", self.cache_rep_output,
                  lambda: self._browse_save(self.cache_rep_output, ".cache", [("Cache", "*.cache"), ("All", "*.*")]), "Save repacked cache")
        btn = ttk.Button(p, text="Repack Cache", command=self._do_cache_repack)
        btn.pack(pady=(4, 0)); ToolTip(btn, "Repack modified files into .cache archive")
        self.cache_rep_log = tk.Text(p, height=8, bg='#fafafa', fg='#222', font=('Consolas', 9), relief='solid', bd=1, wrap='word')
        self.cache_rep_log.pack(fill='both', expand=True, pady=(6, 0))

    # ── Browse (Font) ────────────────────────────────────────────
    def _browse_tex_ext_input(self):
        if self.tex_ext_mode.get() == 'file':
            self._browse_file(self.tex_ext_input, [("TGA.1", "*.tga.1"), ("All", "*.*")])
        else: self._browse_dir(self.tex_ext_input)
    def _browse_tex_rep_png(self):
        if self.tex_rep_mode.get() == 'file':
            self._browse_file(self.tex_rep_png, [("PNG", "*.png"), ("All", "*.*")])
        else: self._browse_dir(self.tex_rep_png)
    def _browse_tex_rep_orig(self):
        if self.tex_rep_mode.get() == 'file':
            self._browse_file(self.tex_rep_orig, [("TGA.1", "*.tga.1"), ("All", "*.*")])
        else: self._browse_dir(self.tex_rep_orig)
    def _browse_tex_rep_output(self):
        if self.tex_rep_mode.get() == 'file':
            self._browse_save(self.tex_rep_output, ".tga.1", [("TGA.1", "*.tga.1"), ("All", "*.*")])
        else: self._browse_dir(self.tex_rep_output)

    # ── Actions ──────────────────────────────────────────────────
    def _do_tex_extract(self):
        inp = self.tex_ext_input.get().strip()
        out = self.tex_ext_output.get().strip()
        if not inp: messagebox.showerror("Error", "Select input."); return
        if not out: messagebox.showerror("Error", "Select output."); return
        self.tex_ext_log.delete('1.0', 'end'); self._set_status("Extracting..."); self.progress_var.set(0)
        mode = self.tex_ext_mode.get(); rec = self.tex_ext_recursive.get()
        def run():
            try:
                from modules.texture import extract_texture, extract_texture_batch
                if mode == 'file':
                    png, info = extract_texture(inp, out)
                    self.root.after(0, lambda: self._log(self.tex_ext_log, f"OK: {os.path.basename(png)} ({info})"))
                    self.root.after(0, lambda: self.progress_var.set(100))
                    self.root.after(0, lambda: self._set_status("Done"))
                else:
                    def prog(c, t, n):
                        self.root.after(0, lambda: self.progress_var.set(c/t*100))
                        self.root.after(0, lambda: self._log(self.tex_ext_log, f"[{c}/{t}] {n}"))
                    ext, tot, errs = extract_texture_batch(inp, out, prog, recursive=rec)
                    self.root.after(0, lambda: self.progress_var.set(100))
                    self.root.after(0, lambda: self._log(self.tex_ext_log, f"\nDone: {ext}/{tot}"))
                    for e in errs: self.root.after(0, lambda x=e: self._log(self.tex_ext_log, f"! {x}"))
                    self.root.after(0, lambda: self._set_status(f"Extracted {ext}/{tot}", bool(errs)))
            except Exception as e:
                self.root.after(0, lambda: self._log(self.tex_ext_log, f"Error: {e}\n{traceback.format_exc()}"))
                self.root.after(0, lambda: self._set_status(str(e), True))
        threading.Thread(target=run, daemon=True).start()

    def _do_tex_repack(self):
        png = self.tex_rep_png.get().strip(); orig = self.tex_rep_orig.get().strip(); out = self.tex_rep_output.get().strip()
        if not png or not orig or not out: messagebox.showerror("Error", "Fill all fields."); return
        self.tex_rep_log.delete('1.0', 'end'); self._set_status("Repacking..."); self.progress_var.set(0)
        mode = self.tex_rep_mode.get(); rec = self.tex_rep_recursive.get()
        def run():
            try:
                from modules.texture import repack_texture, repack_texture_batch, detect_texture_format
                if mode == 'file':
                    det = detect_texture_format(orig)
                    if not det: self.root.after(0, lambda: self._set_status("Format detection failed", True)); return
                    fmt, w, h = det
                    info = repack_texture(png, out, fmt, w, h)
                    self.root.after(0, lambda: self._log(self.tex_rep_log, f"OK: {info}"))
                    self.root.after(0, lambda: self.progress_var.set(100))
                    self.root.after(0, lambda: self._set_status("Done"))
                else:
                    def prog(c, t, n):
                        self.root.after(0, lambda: self.progress_var.set(c/t*100))
                        self.root.after(0, lambda: self._log(self.tex_rep_log, f"[{c}/{t}] {n}"))
                    rep, tot, errs = repack_texture_batch(png, orig, out, prog, recursive=rec)
                    self.root.after(0, lambda: self.progress_var.set(100))
                    self.root.after(0, lambda: self._log(self.tex_rep_log, f"\nDone: {rep}/{tot}"))
                    for e in errs: self.root.after(0, lambda x=e: self._log(self.tex_rep_log, f"! {x}"))
                    self.root.after(0, lambda: self._set_status(f"Repacked {rep}/{tot}", bool(errs)))
            except Exception as e:
                self.root.after(0, lambda: self._log(self.tex_rep_log, f"Error: {e}\n{traceback.format_exc()}"))
                self.root.after(0, lambda: self._set_status(str(e), True))
        threading.Thread(target=run, daemon=True).start()

    def _do_cache_extract(self):
        cache = self.cache_ext_file.get().strip(); out = self.cache_ext_output.get().strip()
        if not cache or not os.path.isfile(cache): messagebox.showerror("Error", "Select cache file."); return
        if not out: messagebox.showerror("Error", "Select output."); return
        self.cache_ext_log.delete('1.0', 'end'); self._set_status("Extracting..."); self.progress_var.set(0)
        def run():
            try:
                from modules.cache import extract_cache
                def prog(c, t, n):
                    self.root.after(0, lambda: self.progress_var.set(c/t*100))
                    if c % 200 == 0 or c == t:
                        self.root.after(0, lambda: self._log(self.cache_ext_log, f"[{c}/{t}] {n}"))
                ext, tot, errs = extract_cache(cache, out, prog)
                self.root.after(0, lambda: self.progress_var.set(100))
                self.root.after(0, lambda: self._log(self.cache_ext_log, f"\nDone: {ext}/{tot}"))
                for e in errs: self.root.after(0, lambda x=e: self._log(self.cache_ext_log, f"! {x}"))
                self.root.after(0, lambda: self._set_status(f"Extracted {ext}", bool(errs)))
            except Exception as e:
                self.root.after(0, lambda: self._log(self.cache_ext_log, f"Error: {e}\n{traceback.format_exc()}"))
                self.root.after(0, lambda: self._set_status(str(e), True))
        threading.Thread(target=run, daemon=True).start()

    def _do_cache_repack(self):
        orig = self.cache_rep_orig.get().strip(); inp = self.cache_rep_input.get().strip(); out = self.cache_rep_output.get().strip()
        if not orig or not os.path.isfile(orig): messagebox.showerror("Error", "Select original cache."); return
        if not inp or not os.path.isdir(inp): messagebox.showerror("Error", "Select input directory."); return
        if not out: messagebox.showerror("Error", "Select output file."); return
        self.cache_rep_log.delete('1.0', 'end'); self._set_status("Repacking..."); self.progress_var.set(0)
        def run():
            try:
                from modules.cache import repack_cache
                def prog(c, t, n):
                    self.root.after(0, lambda: self.progress_var.set(c/t*100))
                    if c % 200 == 0 or c == t:
                        self.root.after(0, lambda: self._log(self.cache_rep_log, f"[{c}/{t}] {n}"))
                pk, tot, errs = repack_cache(orig, inp, out, prog)
                sz = os.path.getsize(out)
                self.root.after(0, lambda: self.progress_var.set(100))
                self.root.after(0, lambda: self._log(self.cache_rep_log, f"\nDone: {pk}/{tot} ({sz:,} bytes)"))
                for e in errs: self.root.after(0, lambda x=e: self._log(self.cache_rep_log, f"! {x}"))
                self.root.after(0, lambda: self._set_status(f"Packed {pk}", bool(errs)))
            except Exception as e:
                self.root.after(0, lambda: self._log(self.cache_rep_log, f"Error: {e}\n{traceback.format_exc()}"))
                self.root.after(0, lambda: self._set_status(str(e), True))
        threading.Thread(target=run, daemon=True).start()


def launch_gui():
    root = tk.Tk()
    DarkSectorTool(root)
    root.mainloop()

if __name__ == '__main__':
    launch_gui()
