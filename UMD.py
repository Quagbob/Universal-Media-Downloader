import sys
import os
import json
import threading
import subprocess
import tkinter as tk
from tkinter import messagebox, ttk, filedialog
import shutil
import time
import re

import yt_dlp


CONFIG_FILE = "config.json"
PRESETS_FILE = "presets.json"

APP_DIR = os.path.dirname(os.path.abspath(__file__))
PROFILE_ROOT = os.path.join(APP_DIR, "UMD_Browser_Profiles")


LIGHT_THEME = {
    "bg": "#F5F5F5", "frame_bg": "#F5F5F5", "text": "#1A1A1A",
    "sub_text": "#555555", "entry_bg": "#FFFFFF", "entry_fg": "#1A1A1A",
    "cursor": "#000000", "menu_bg": "#FFFFFF", "menu_fg": "#1A1A1A",
    "menu_active_bg": "#E0E0E0", "btn_update": "#2196F3",
    "btn_download": "#4CAF50", "btn_fg": "#FFFFFF",
    "btn_dl_fg": "#FFFFFF", "status_idle": "#757575",
    "panel_bg": "#EEEEEE", "placeholder": "#888888"
}

DARK_THEME = {
    "bg": "#121212", "frame_bg": "#121212", "text": "#E0E0E0",
    "sub_text": "#A0A0A0", "entry_bg": "#1E1E1E", "entry_fg": "#FFFFFF",
    "cursor": "#FFFFFF", "menu_bg": "#1E1E1E", "menu_fg": "#E0E0E0",
    "menu_active_bg": "#333333", "btn_update": "#3700B3",
    "btn_download": "#03DAC6", "btn_fg": "#FFFFFF",
    "btn_dl_fg": "#000000", "status_idle": "#A0A0A0",
    "panel_bg": "#181818", "placeholder": "#888888"
}

BROWSERS = ["Chrome", "Edge", "Brave", "Opera", "Vivaldi", "Firefox"]
BROWSER_IDS = {
    "Chrome": "chrome", "Edge": "edge", "Brave": "brave",
    "Opera": "opera", "Vivaldi": "vivaldi", "Firefox": "firefox"
}

FORMAT_OPTIONS = [
    "Max Quality Available", "1080p", "720p",
    "480p", "Audio Only (MP3)"
]

CONVERSION_FORMATS = [
    "Keep Original", "MP4", "MKV", "WEBM", "MP3", "M4A", "WAV"
]

VIDEO_PRESETS = ["Default", "Fast", "Medium", "Slow", "Very Slow"]

def load_json(path, default):
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return default

def save_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        return True
    except Exception:
        return False

saved_config = load_json(CONFIG_FILE, {
    "format_choice": "Max Quality Available",
    "theme_choice": "Light",
    "save_location": "",
    "auth_method": "Independent Browser Profile",
    "browser": "Chrome",
    "cookie_file": ""
})
presets = load_json(PRESETS_FILE, {})

root = tk.Tk()
root.title("Universal Media Downloader")
CLOSED_WIDTH = 760
OPEN_WIDTH = 1120
WINDOW_HEIGHT = 760
root.geometry(f"{CLOSED_WIDTH}x{WINDOW_HEIGHT}")
root.minsize(700, 650)
root.resizable(True, True)

# ---------- logging ----------
log_lines = []

def log(message):
    stamp = time.strftime("%H:%M:%S")
    line = f"[{stamp}] {message}"
    log_lines.append(line)
    print(line)
    if len(log_lines) > 500:
        del log_lines[:-500]
    try:
        root.after(0, lambda: append_log(line))
    except Exception:
        pass

def append_log(line):
    log_text.configure(state="normal")
    log_text.insert("end", line + "\n")
    log_text.see("end")
    log_text.configure(state="disabled")

# ---------- helpers ----------
def clean_filename(name):
    invalid = '<>:"/\\|?*'
    for char in invalid:
        name = name.replace(char, "_")
    return name.strip().rstrip(".")

def parse_size(text):
    """Return bytes. A unit is required for clarity, e.g. 500 MB or 1.5 GB."""
    if not text or not text.strip():
        return None
    m = re.fullmatch(r"\s*([\d.]+)\s*(KB|MB|GB|TB)\s*", text, re.I)
    if not m:
        raise ValueError("Maximum file size must include a unit. Enter it like '500 MB' or '1.5 GB'.")
    value = float(m.group(1))
    if value <= 0:
        raise ValueError("Maximum file size must be greater than 0.")
    unit = m.group(2).upper()
    mult = {"KB": 1000, "MB": 1000**2, "GB": 1000**3, "TB": 1000**4}[unit]
    return int(value * mult)

def parse_bitrate(text):
    """Return kbps. A unit is required, e.g. 4000 kbps or 4 Mbps."""
    if not text or not text.strip():
        return None
    m = re.fullmatch(r"\s*([\d.]+)\s*(kbps|mbps)\s*", text, re.I)
    if not m:
        raise ValueError("Video bitrate must include a unit. Enter it like '4000 kbps' or '4 Mbps'.")
    value = float(m.group(1))
    if value <= 0:
        raise ValueError("Video bitrate must be greater than 0.")
    unit = m.group(2).lower()
    return int(value * (1000 if unit in ("m", "mbps") else 1))

def parse_crf(text):
    if not text or not text.strip():
        return None
    value = int(text.strip())
    if not 0 <= value <= 51:
        raise ValueError("CRF must be between 0 and 51. Around 18-28 is common for H.264.")
    return value

def get_ffmpeg():
    local = os.path.join(APP_DIR, "ffmpeg.exe")
    if os.path.isfile(local):
        return local
    return shutil.which("ffmpeg")

def get_ffprobe():
    local = os.path.join(APP_DIR, "ffprobe.exe")
    if os.path.isfile(local):
        return local
    return shutil.which("ffprobe")

def ffmpeg_exists():
    return bool(get_ffmpeg())

def load_settings():
    return saved_config

# ---------- main variables ----------
url_var = tk.StringVar()
format_var = tk.StringVar(value=saved_config.get("format_choice", FORMAT_OPTIONS[0]))
start_var = tk.StringVar()
end_var = tk.StringVar()
output_var = tk.StringVar(value=saved_config.get("save_location", ""))
theme_var = tk.StringVar(value=saved_config.get("theme_choice", "Light"))
auth_method_var = tk.StringVar(value=saved_config.get("auth_method", "Independent Browser Profile"))
browser_var = tk.StringVar(value=saved_config.get("browser", "Chrome"))
cookie_var = tk.StringVar(value=saved_config.get("cookie_file", ""))

# Advanced variables
conversion_var = tk.StringVar(value="Keep Original")
crf_var = tk.StringVar()
bitrate_var = tk.StringVar()
max_size_var = tk.StringVar()
encoder_preset_var = tk.StringVar(value="Default")
two_pass_var = tk.BooleanVar(value=False)

def save_settings():
    data = {
        "format_choice": format_var.get(),
        "theme_choice": theme_var.get(),
        "save_location": output_var.get(),
        "auth_method": auth_method_var.get(),
        "browser": browser_var.get(),
        "cookie_file": cookie_var.get()
    }
    save_json(CONFIG_FILE, data)

def save_preset():
    name = preset_name_var.get().strip()
    if not name:
        messagebox.showerror("Preset Name", "Enter a name for the preset first.")
        return
    presets[name] = get_advanced_values()
    if save_json(PRESETS_FILE, presets):
        refresh_presets()
        preset_var.set(name)
        log(f"Saved advanced preset: {name}")
        messagebox.showinfo("Preset Saved", f"Preset '{name}' was saved.")
    else:
        messagebox.showerror("Preset Error", "Could not save presets.json.")

def load_preset():
    name = preset_var.get()
    if not name or name not in presets:
        return
    values = presets[name]
    conversion_var.set(values.get("conversion", "Keep Original"))
    set_placeholder_value(crf_entry, values.get("crf", ""))
    set_placeholder_value(bitrate_entry, values.get("bitrate", ""))
    set_placeholder_value(max_size_entry, values.get("max_size", ""))
    encoder_preset_var.set(values.get("preset", "Default"))
    two_pass_var.set(values.get("two_pass", False))
    log(f"Loaded advanced preset: {name}")

def delete_preset():
    name = preset_var.get()
    if not name or name not in presets:
        return
    if messagebox.askyesno("Delete Preset", f"Delete preset '{name}'?"):
        del presets[name]
        save_json(PRESETS_FILE, presets)
        refresh_presets()
        log(f"Deleted advanced preset: {name}")

def refresh_presets():
    preset_menu_saved["menu"].delete(0, "end")
    for name in sorted(presets.keys()):
        preset_menu_saved["menu"].add_command(label=name, command=lambda n=name: preset_var.set(n))
    preset_var.set("")

def get_advanced_values():
    return {
        "conversion": conversion_var.get(),
        "crf": get_entry_value(crf_entry),
        "bitrate": get_entry_value(bitrate_entry),
        "max_size": get_entry_value(max_size_entry),
        "preset": encoder_preset_var.get(),
        "two_pass": two_pass_var.get()
    }

# ---------- placeholder entry ----------
class TimeEntry(tk.Entry):
    """Fixed HH:MM:SS field. Digits can be replaced, while colons stay fixed."""
    def __init__(self, master, initial="00:00:00", **kwargs):
        self._updating = False
        super().__init__(master, **kwargs)
        self.insert(0, initial)
        self.icursor(0)
        self.bind("<KeyPress>", self._key_press)
        self.bind("<Button-1>", self._mouse_click)

    def _mouse_click(self, event):
        self.after(1, self._normalize_cursor)

    def _normalize_cursor(self):
        pos = self.index(tk.INSERT)
        if pos in (2, 5):
            self.icursor(pos + 1)

    def _key_press(self, event):
        if event.keysym in ("Left", "Right", "Home", "End", "Tab", "Shift_L", "Shift_R"):
            return

        pos = self.index(tk.INSERT)

        if event.keysym in ("BackSpace", "Delete"):
            if event.keysym == "BackSpace":
                pos -= 1
            if pos in (2, 5):
                pos -= 1 if event.keysym == "BackSpace" else 0
            if 0 <= pos < 8 and pos not in (2, 5):
                chars = list(self.get())
                chars[pos] = "0"
                self.delete(0, "end")
                self.insert(0, "".join(chars))
                self.icursor(max(0, pos if event.keysym == "Delete" else pos))
            return "break"

        if event.char and event.char.isdigit():
            if pos >= 8:
                return "break"
            if pos in (2, 5):
                pos += 1
            if pos >= 8:
                return "break"
            chars = list(self.get())
            chars[pos] = event.char
            self.delete(0, "end")
            self.insert(0, "".join(chars))
            self.icursor(pos + 1)
            return "break"

        return "break"

    def set_value(self, value="00:00:00"):
        value = value if re.fullmatch(r"\d{2}:\d{2}:\d{2}", value or "") else "00:00:00"
        self.delete(0, "end")
        self.insert(0, value)

class PlaceholderEntry(tk.Entry):
    def __init__(self, master, placeholder="", **kwargs):
        self.placeholder = placeholder
        self.placeholder_active = False
        super().__init__(master, **kwargs)
        self.bind("<FocusIn>", self._focus_in)
        self.bind("<FocusOut>", self._focus_out)
        self._show_placeholder()

    def _show_placeholder(self):
        if not self.get():
            self.placeholder_active = True
            self.configure(fg=active_theme()["placeholder"])
            self.insert(0, self.placeholder)

    def _focus_in(self, _=None):
        if self.placeholder_active:
            self.delete(0, "end")
            self.placeholder_active = False
            self.configure(fg=active_theme()["entry_fg"])

    def _focus_out(self, _=None):
        if not self.get():
            self._show_placeholder()

    def value(self):
        return "" if self.placeholder_active else self.get().strip()

    def set_value(self, value):
        self.delete(0, "end")
        self.placeholder_active = False
        if value:
            self.insert(0, value)
            self.configure(fg=active_theme()["entry_fg"])
        else:
            self._show_placeholder()

def set_placeholder_value(entry, value):
    entry.set_value(value)

def get_entry_value(entry):
    return entry.value()

def make_dropdown(parent, variable, values, font=("Arial", 11), width=None):
    """Consistent themed OptionMenu used everywhere in the application."""
    menu = tk.OptionMenu(parent, variable, *values)
    menu.configure(
        bd=0,
        highlightthickness=0,
        relief="flat",
        font=font,
        anchor="w"
    )
    if width:
        menu.configure(width=width)
    return menu


# ---------- layout ----------
left = tk.Frame(root)
left.pack(side="left", fill="both", expand=True)

right = tk.Frame(root, width=470)
right.pack_propagate(False)
# The entire advanced panel is kept in this single container and is
# packed/unpacked as a unit. Its children are never individually hidden.

title_label = tk.Label(left, text="Universal Media Downloader", font=("Arial", 15, "bold"))
title_label.pack(pady=10)

input_frame = tk.Frame(left)
input_frame.pack(fill="x", padx=20, pady=2)
tk.Label(input_frame, text="Paste Website Video Link:").pack(anchor="w")
url_entry = tk.Entry(input_frame, textvariable=url_var, font=("Arial", 13), borderwidth=0, highlightthickness=0, relief="flat")
url_entry.pack(fill="x", pady=4, ipady=4)
url_entry.focus()

format_frame = tk.Frame(left)
format_frame.pack(fill="x", padx=20, pady=5)
tk.Label(format_frame, text="Select Output Quality / Resolution:").pack(anchor="w")
format_menu = make_dropdown(format_frame, format_var, FORMAT_OPTIONS, font=("Arial", 12))
format_menu.pack(fill="x", pady=4)

trim_frame = tk.Frame(left)
trim_frame.pack(fill="x", padx=20, pady=5)
tk.Label(trim_frame, text="Trim Video Chunk (Optional - Leave blank for full file):").pack(anchor="w")
trim_grid = tk.Frame(trim_frame)
trim_grid.pack(fill="x", pady=4)
tk.Label(trim_grid, text="Start (HH:MM:SS):").pack(side="left", padx=(0, 5))
start_entry = TimeEntry(trim_grid, initial="00:00:00", font=("Arial", 12), width=10,
                         borderwidth=0, highlightthickness=0, relief="flat")
start_entry.pack(side="left", padx=(0, 20), ipady=3)

tk.Label(trim_grid, text="End (HH:MM:SS):").pack(side="left", padx=(0, 5))
end_entry = TimeEntry(trim_grid, initial="00:00:00", font=("Arial", 12), width=10,
                       borderwidth=0, highlightthickness=0, relief="flat")
end_entry.pack(side="left", ipady=3)

output_frame = tk.Frame(left)
output_frame.pack(fill="x", padx=20, pady=5)
tk.Label(output_frame, text="Save Location (blank = application folder):").pack(anchor="w")
output_grid = tk.Frame(output_frame)
output_grid.pack(fill="x", pady=4)
output_entry = tk.Entry(output_grid, textvariable=output_var, font=("Arial", 11), borderwidth=0, highlightthickness=0, relief="flat")
output_entry.pack(side="left", fill="x", expand=True, ipady=4)

def browse_save_location():
    folder = filedialog.askdirectory(title="Select Download Folder")
    if folder:
        output_var.set(folder)
        save_settings()

browse_button = tk.Button(output_grid, text="Browse...", command=browse_save_location, bd=0, padx=10, pady=3)
browse_button.pack(side="right", padx=(8, 0))

tk.Label(output_frame, text="File Name (blank = website's default name):").pack(anchor="w", pady=(5, 0))
filename_entry = tk.Entry(output_frame, font=("Arial", 11), borderwidth=0, highlightthickness=0, relief="flat")
filename_entry.pack(fill="x", pady=4, ipady=4)

auth_frame = tk.Frame(left)
auth_frame.pack(fill="x", padx=20, pady=6)
tk.Label(auth_frame, text="Authentication:").pack(anchor="w")

auth_profile_radio = tk.Radiobutton(auth_frame, text="Independent Browser Profile", variable=auth_method_var,
                                    value="Independent Browser Profile", command=lambda: update_auth_ui())
auth_profile_radio.pack(anchor="w", pady=(3, 0))
auth_cookie_radio = tk.Radiobutton(auth_frame, text="cookies.txt File", variable=auth_method_var,
                                   value="cookies.txt File", command=lambda: update_auth_ui())
auth_cookie_radio.pack(anchor="w")

profile_frame = tk.Frame(auth_frame)
tk.Label(profile_frame, text="Browser:").pack(side="left", padx=(20, 5))
browser_menu = make_dropdown(profile_frame, browser_var, BROWSERS, font=("Arial", 10))
browser_menu.pack(side="left")

def get_profile_path():
    return os.path.join(PROFILE_ROOT, browser_var.get())

def find_browser_executable(browser):
    local = os.environ.get("LOCALAPPDATA", "")
    pf = os.environ.get("PROGRAMFILES", "")
    pfx = os.environ.get("PROGRAMFILES(X86)", "")
    candidates = []
    if browser == "Chrome":
        candidates = [os.path.join(local, "Google", "Chrome", "Application", "chrome.exe"),
                      os.path.join(pf, "Google", "Chrome", "Application", "chrome.exe"),
                      os.path.join(pfx, "Google", "Chrome", "Application", "chrome.exe")]
    elif browser == "Edge":
        candidates = [os.path.join(pfx, "Microsoft", "Edge", "Application", "msedge.exe"),
                      os.path.join(pf, "Microsoft", "Edge", "Application", "msedge.exe"),
                      os.path.join(local, "Microsoft", "Edge", "Application", "msedge.exe")]
    elif browser == "Brave":
        candidates = [os.path.join(pf, "BraveSoftware", "Brave-Browser", "Application", "brave.exe"),
                      os.path.join(pfx, "BraveSoftware", "Brave-Browser", "Application", "brave.exe"),
                      os.path.join(local, "BraveSoftware", "Brave-Browser", "Application", "brave.exe")]
    elif browser == "Opera":
        candidates = [os.path.join(local, "Programs", "Opera", "launcher.exe"),
                      os.path.join(pf, "Opera", "launcher.exe")]
    elif browser == "Vivaldi":
        candidates = [os.path.join(local, "Vivaldi", "Application", "vivaldi.exe"),
                      os.path.join(pf, "Vivaldi", "Application", "vivaldi.exe")]
    elif browser == "Firefox":
        candidates = [os.path.join(pf, "Mozilla Firefox", "firefox.exe"),
                      os.path.join(pfx, "Mozilla Firefox", "firefox.exe"),
                      os.path.join(local, "Mozilla Firefox", "firefox.exe")]
    for p in candidates:
        if p and os.path.isfile(p):
            return p
    return None

def open_authentication_browser():
    browser = browser_var.get()
    executable = find_browser_executable(browser)
    if not executable:
        messagebox.showerror("Browser Not Found", f"Could not find {browser} on this computer.")
        return
    profile_path = get_profile_path()
    os.makedirs(profile_path, exist_ok=True)
    try:
        if browser == "Firefox":
            command = [executable, "-no-remote", "-profile", profile_path, "https://www.youtube.com/"]
        else:
            command = [executable, f"--user-data-dir={profile_path}", "--profile-directory=Default",
                       "--no-first-run", "--no-default-browser-check", "https://www.youtube.com/"]
        subprocess.Popen(command)
        auth_status_label.configure(text=f"Opened dedicated {browser} profile. Sign in, then close the browser.")
        log(f"Opened independent {browser} authentication browser.")
    except Exception as e:
        messagebox.showerror("Could Not Open Browser", str(e))

open_profile_button = tk.Button(profile_frame, text="Open Authentication Browser",
                                command=open_authentication_browser, bd=0, padx=8, pady=3)
open_profile_button.pack(side="left", padx=(15, 0))
profile_frame.pack(fill="x", pady=3)

cookie_frame = tk.Frame(auth_frame)
cookie_entry = tk.Entry(cookie_frame, textvariable=cookie_var, font=("Arial", 10), borderwidth=0, highlightthickness=0, relief="flat")
cookie_entry.pack(side="left", padx=(20, 5), fill="x", expand=True)

def browse_cookie_file():
    filename = filedialog.askopenfilename(title="Select cookies.txt",
                                          filetypes=[("Cookie files", "*.txt"), ("All files", "*.*")])
    if filename:
        cookie_var.set(filename)
        save_settings()

cookie_button = tk.Button(cookie_frame, text="Browse...", command=browse_cookie_file, bd=0, padx=10, pady=3)
cookie_button.pack(side="right")

auth_status_label = tk.Label(auth_frame, text="", font=("Arial", 9, "italic"))
auth_status_label.pack(fill="x", pady=(3, 0))

def profile_is_ready():
    p = get_profile_path()
    return os.path.isdir(p) and any(os.scandir(p))

def update_auth_ui():
    if auth_method_var.get() == "Independent Browser Profile":
        cookie_frame.pack_forget()
        profile_frame.pack(fill="x", pady=3)
        if profile_is_ready():
            auth_status_label.configure(text=f"Independent {browser_var.get()} profile exists.")
        else:
            auth_status_label.configure(text="No independent browser profile created yet.")
    else:
        profile_frame.pack_forget()
        cookie_frame.pack(fill="x", pady=3)
        auth_status_label.configure(text="Using selected cookies.txt file." if cookie_var.get() else "No cookies.txt file selected.")
    save_settings()

theme_frame = tk.Frame(left)
theme_frame.pack(fill="x", padx=20, pady=5)
tk.Label(theme_frame, text="Application Theme Mode:").pack(anchor="w")

def active_theme():
    return DARK_THEME if theme_var.get() == "Dark" else LIGHT_THEME

theme_light_radio = tk.Radiobutton(theme_frame, text="Light Mode", variable=theme_var, value="Light", command=lambda: apply_theme())
theme_light_radio.pack(side="left", padx=5)
theme_dark_radio = tk.Radiobutton(theme_frame, text="Dark Mode", variable=theme_var, value="Dark", command=lambda: apply_theme())
theme_dark_radio.pack(side="left", padx=20)

# ---------- advanced panel ----------
# The right side is one coherent panel. It starts completely hidden.
advanced_visible = False


def toggle_advanced():
    global advanced_visible
    advanced_visible = not advanced_visible

    if advanced_visible:
        right.pack(side="right", fill="both", padx=(0, 10), pady=10)
        advanced_toggle.configure(text="Advanced Settings  −")
        root.update_idletasks()
        width = max(OPEN_WIDTH, root.winfo_width() + right.winfo_reqwidth())
        root.geometry(f"{width}x{root.winfo_height()}")
    else:
        right.pack_forget()
        advanced_toggle.configure(text="Advanced Settings  +")
        root.update_idletasks()
        root.geometry(f"{CLOSED_WIDTH}x{root.winfo_height()}")


# The toggle belongs to the left/main side.
advanced_toggle = tk.Button(
    left,
    text="Advanced Settings  +",
    font=("Arial", 12, "bold"),
    bd=0,
    width=22,
    padx=10,
    pady=4,
    anchor="center",
    command=toggle_advanced
)
advanced_toggle.pack(anchor="e", padx=25, pady=(2, 6))

advanced_title = advanced_toggle


def add_labeled(parent, text, widget, help_text=None):
    tk.Label(parent, text=text, anchor="w").pack(fill="x", padx=15, pady=(4, 1))
    widget.pack(fill="x", padx=15, pady=(0, 1), ipady=4)
    if help_text:
        tk.Label(parent, text=help_text, anchor="w", justify="left", wraplength=420,
                 font=("Arial", 9, "italic")).pack(fill="x", padx=15, pady=(0, 3))

# Saved presets are placed first so they can be selected before conversion settings.
tk.Label(right, text="Presets", font=("Arial", 11, "bold")).pack(anchor="w", padx=15, pady=(10, 3))
preset_row2 = tk.Frame(right)
preset_var = tk.StringVar()
preset_menu_saved = make_dropdown(preset_row2, preset_var, [""], font=("Arial", 10))
preset_menu_saved.pack(side="left", fill="x", expand=True)
tk.Button(preset_row2, text="Load", command=load_preset, bd=0, padx=8).pack(side="left", padx=4)
tk.Button(preset_row2, text="Delete", command=delete_preset, bd=0, padx=8).pack(side="left")
preset_row2.pack(fill="x", padx=15, pady=3)

preset_row3 = tk.Frame(right)
preset_name_var = tk.StringVar()
preset_name_entry = tk.Entry(preset_row3, textvariable=preset_name_var, borderwidth=0, highlightthickness=0, relief="flat")
preset_name_entry.pack(side="left", fill="x", expand=True, ipady=4)
tk.Button(preset_row3, text="Save Preset", command=save_preset, bd=0, padx=10).pack(side="right", padx=(5, 0))
preset_row3.pack(fill="x", padx=15, pady=3)

conv_menu = make_dropdown(right, conversion_var, CONVERSION_FORMATS, font=("Arial", 11))
add_labeled(right, "Convert After Download:", conv_menu,
            "Choose a final container. 'Keep Original' skips conversion.")

crf_entry = PlaceholderEntry(right, "e.g. 23  (lower = higher quality)")
add_labeled(right, "CRF / Quality:", crf_entry,
            "H.264/H.265-style quality control. 18-28 is a common range; leave blank to use the encoder default.")

bitrate_entry = PlaceholderEntry(right, "e.g. 4000 kbps")
add_labeled(right, "Video Bitrate:", bitrate_entry,
            "Optional target video bitrate. Examples: 2500k, 4000k, 6M. Leave blank to use CRF/default quality.")

max_size_entry = PlaceholderEntry(right, "e.g. 500 MB")
add_labeled(right, "Maximum File Size (number + unit):", max_size_entry,
            "Enter BOTH a number and unit — for example: 500 MB or 1.5 GB. Do not enter just 500.")

preset_row = tk.Frame(right)
tk.Label(preset_row, text="Encoder Speed:").pack(side="left")
preset_menu = make_dropdown(preset_row, encoder_preset_var, VIDEO_PRESETS, font=("Arial", 10))
preset_menu.pack(side="left", padx=8)
preset_row.pack(fill="x", padx=15, pady=5)

two_pass_check = tk.Checkbutton(right, text="Use two-pass encoding when bitrate is specified",
                                variable=two_pass_var)
two_pass_check.pack(anchor="w", padx=15, pady=3)

refresh_presets()

# All advanced controls remain packed inside `right`.
# Visibility is controlled only by packing/unpacking the entire right panel.

# ---------- lower right log ----------
log_frame = tk.Frame(right)
log_frame.pack(fill="both", expand=True, padx=15, pady=(10, 10))
tk.Label(log_frame, text="Activity / Debug Log", font=("Arial", 11, "bold")).pack(anchor="w")
log_text = tk.Text(log_frame, height=15, wrap="word", state="disabled",
                   borderwidth=0, highlightthickness=0, relief="flat")
log_scroll = tk.Scrollbar(log_frame, command=log_text.yview)
log_text.configure(yscrollcommand=log_scroll.set)
log_scroll.pack(side="right", fill="y")
log_text.pack(side="left", fill="both", expand=True)
tk.Button(log_frame, text="Clear Log", command=lambda: clear_log(), bd=0, padx=8).pack(anchor="e", pady=(4, 0))

def clear_log():
    log_text.configure(state="normal")
    log_text.delete("1.0", "end")
    log_text.configure(state="disabled")

# ---------- bottom controls ----------
progress_bar = ttk.Progressbar(left, orient="horizontal", mode="indeterminate")
progress_bar.pack(fill="x", padx=20, pady=8)
status_label = tk.Label(left, text="Status: Ready", font=("Arial", 12, "italic"))
status_label.pack(pady=2)

button_frame = tk.Frame(left)
button_frame.pack(fill="x", padx=20, pady=10)

update_button = tk.Button(button_frame, text="Update Engine", font=("Arial", 12), bd=0, padx=10, pady=5)
update_button.pack(side="left", padx=5)

download_button = tk.Button(button_frame, text="Download Media", font=("Arial", 13, "bold"), bd=0, width=22, pady=4)
download_button.pack(side="right", padx=5)

# ---------- theme ----------
def apply_theme():
    p = active_theme()
    root.configure(bg=p["bg"])
    for widget in [left, right, input_frame, format_frame, trim_frame, trim_grid, output_frame,
                   output_grid, auth_frame, profile_frame, cookie_frame, theme_frame,
                   button_frame, preset_row, preset_row2, preset_row3, log_frame]:
        widget.configure(bg=p["frame_bg"])
    for widget in [title_label, advanced_title, status_label, auth_status_label]:
        widget.configure(bg=p["bg"], fg=p["text"] if widget != status_label else p["status_idle"])
    for parent in [input_frame, format_frame, trim_frame, output_frame, auth_frame, theme_frame, right]:
        for child in parent.winfo_children():
            if isinstance(child, tk.Label):
                child.configure(bg=p["frame_bg"], fg=p["text"])
    for widget in [url_entry, start_entry, end_entry, output_entry, filename_entry, cookie_entry,
                   preset_name_entry, log_text]:
        widget.configure(bg=p["entry_bg"], fg=p["entry_fg"], insertbackground=p["cursor"])
    for widget in [crf_entry, bitrate_entry, max_size_entry]:
        widget.configure(bg=p["entry_bg"], insertbackground=p["cursor"])
        if not widget.focus_get():
            widget.configure(fg=p["placeholder"] if widget.placeholder_active else p["entry_fg"])
    for menu in [format_menu, browser_menu, conv_menu, preset_menu, preset_menu_saved]:
        menu.configure(bg=p["menu_bg"], fg=p["menu_fg"], activebackground=p["menu_active_bg"], activeforeground=p["menu_fg"])
        menu["menu"].configure(bg=p["menu_bg"], fg=p["menu_fg"], activebackground=p["menu_active_bg"], activeforeground=p["menu_fg"])
    for radio in [auth_profile_radio, auth_cookie_radio, theme_light_radio, theme_dark_radio]:
        radio.configure(bg=p["bg"], fg=p["text"], selectcolor=p["entry_bg"], activebackground=p["bg"], activeforeground=p["text"])
    two_pass_check.configure(bg=p["frame_bg"], fg=p["text"], selectcolor=p["entry_bg"], activebackground=p["frame_bg"], activeforeground=p["text"])
    style = ttk.Style()
    style.theme_use("default")
    style.configure("TProgressbar", thickness=12, background="#BB86FC" if theme_var.get() == "Dark" else "#0D47A1", troughcolor=p["entry_bg"])
    style.configure("TCombobox", fieldbackground=p["entry_bg"], background=p["entry_bg"], foreground=p["entry_fg"])
    advanced_toggle.configure(bg=p["btn_update"], fg=p["btn_fg"], activebackground=p["btn_update"], activeforeground=p["btn_fg"])
    for b in [update_button, browse_button, cookie_button, open_profile_button]:
        b.configure(bg=p["btn_update"], fg=p["btn_fg"], activebackground=p["btn_update"])
    download_button.configure(bg=p["btn_download"], fg=p["btn_dl_fg"], activebackground=p["btn_download"])
    save_settings()

# ---------- download ----------
def find_media_result(folder, before_snapshot, expected_base=None, started_at=0):
    """Find the media yt-dlp created OR overwrote, including a previously existing filename."""
    media_exts = {".mp4", ".mkv", ".webm", ".mov", ".avi", ".m4v", ".mp3", ".m4a", ".wav", ".opus"}
    candidates = []
    try:
        for name in os.listdir(folder):
            path = os.path.join(folder, name)
            if not os.path.isfile(path):
                continue
            if os.path.splitext(name)[1].lower() not in media_exts:
                continue

            # Prefer the expected basename when one is known.
            base = os.path.splitext(name)[0]
            if expected_base and base == expected_base:
                candidates.append((3, os.path.getmtime(path), path))
                continue

            old_mtime = before_snapshot.get(name)
            mtime = os.path.getmtime(path)
            if old_mtime is None:
                candidates.append((2, mtime, path))
            elif mtime > old_mtime + 0.2:
                candidates.append((1, mtime, path))
            elif mtime >= started_at:
                candidates.append((0, mtime, path))
    except Exception:
        pass

    if not candidates:
        return None
    candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return candidates[0][2]

def build_options(output_template, choice, start, end):
    options = {
        "outtmpl": output_template,
        "merge_output_format": "mp4",
        "windowsfilenames": True,
        "noplaylist": True,
        "quiet": False
    }
    if choice == "Audio Only (MP3)":
        options["format"] = "bestaudio/best"
        options["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192"
        }]
    elif "1080p" in choice:
        options["format"] = "bestvideo[height<=1080]+bestaudio/best"
    elif "720p" in choice:
        options["format"] = "bestvideo[height<=720]+bestaudio/best"
    elif "480p" in choice:
        options["format"] = "bestvideo[height<=480]+bestaudio/best"
    else:
        options["format"] = "bestvideo+bestaudio/best"
    if start or end:
        actual_start = start or "00:00:00"
        actual_end = end or None
        options["download_ranges"] = yt_dlp.utils.download_range_func(
            None, [{
                "start_time": yt_dlp.utils.timestr_to_secs(actual_start),
                "end_time": yt_dlp.utils.timestr_to_secs(actual_end) if actual_end else None
            }]
        )
        options["force_keyframes_at_cuts"] = True
    return options

def get_video_duration(path):
    probe = get_ffprobe()
    if not probe:
        return None
    try:
        result = subprocess.run([probe, "-v", "error", "-show_entries", "format=duration",
                                 "-of", "default=noprint_wrappers=1:nokey=1", path],
                                capture_output=True, text=True, check=True)
        return float(result.stdout.strip())
    except Exception:
        return None

def ffmpeg_progress_reader(process, total_duration=None, stage="Converting"):
    """Read FFmpeg's machine-readable progress and keep the GUI informed."""
    last_percent = -1
    for raw_line in process.stderr:
        line = raw_line.strip()
        if not line:
            continue

        log(f"FFmpeg: {line}")

        # -progress pipe:2 emits newline-delimited out_time_ms values, which
        # are reliable to consume from a background thread.
        elapsed = None
        match_ms = re.search(r"^out_time_ms=(\d+)$", line)
        if match_ms:
            elapsed = int(match_ms.group(1)) / 1_000_000.0
        else:
            match_time = re.search(r"^out_time=(\d+):(\d+):(\d+(?:\.\d+)?)$", line)
            if match_time:
                hours, minutes, seconds = match_time.groups()
                elapsed = int(hours) * 3600 + int(minutes) * 60 + float(seconds)

        if elapsed is not None and total_duration:
            percent = max(0, min(100, int((elapsed / total_duration) * 100)))
            if percent != last_percent:
                last_percent = percent
                root.after(
                    0,
                    lambda p=percent, st=stage:
                        update_progress(p, f"Status: {st}... {p}%")
                )

    return process.wait()

def run_ffmpeg_with_progress(cmd, source, stage="Converting"):
    """Run FFmpeg without hiding its progress from the GUI."""
    duration = get_video_duration(source)
    root.after(0, lambda: start_determinate_progress(stage))

    # Ask FFmpeg for newline-delimited machine-readable progress so the
    # background worker can update Tkinter without relying on carriage-return
    # console output.
    progress_cmd = list(cmd) + ["-progress", "pipe:2", "-nostats"]
    process = subprocess.Popen(
        progress_cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1
    )

    returncode = ffmpeg_progress_reader(process, duration, stage)
    if returncode != 0:
        raise RuntimeError(f"FFmpeg failed with exit code {returncode}.")


def update_progress(percent, message=None):
    progress_bar["value"] = percent
    if message:
        status_label.configure(text=message)


def start_determinate_progress(stage="Working"):
    progress_bar.stop()
    progress_bar.configure(mode="determinate", maximum=100, value=0)
    status_label.configure(text=f"Status: {stage}... 0%")


def start_indeterminate_progress(message="Working..."):
    progress_bar.configure(mode="indeterminate")
    progress_bar.start(10)
    status_label.configure(text=f"Status: {message}")


def finish_progress():
    progress_bar.stop()
    progress_bar.configure(mode="determinate", maximum=100, value=100)


def convert_media(source, advanced, output_dir, base_name):
    fmt = advanced["conversion"]
    if fmt == "Keep Original":
        return source

    ffmpeg = get_ffmpeg()
    if not ffmpeg:
        raise RuntimeError("FFmpeg is required for Advanced conversion.")

    crf = parse_crf(advanced["crf"])
    bitrate = parse_bitrate(advanced["bitrate"])
    max_bytes = parse_size(advanced["max_size"])
    speed = advanced["preset"]
    two_pass = advanced["two_pass"]

    ext = fmt.lower()
    target = os.path.join(output_dir, clean_filename(base_name) + "." + ext)

    # Avoid overwriting a source that already has the target extension.
    if os.path.abspath(source) == os.path.abspath(target):
        return source

    if fmt in ("MP3", "M4A", "WAV"):
        cmd = [ffmpeg, "-y", "-i", source]
        if fmt == "MP3":
            cmd += ["-vn", "-c:a", "libmp3lame", "-b:a", "192k"]
        elif fmt == "M4A":
            cmd += ["-vn", "-c:a", "aac", "-b:a", "192k"]
        else:
            cmd += ["-vn", "-c:a", "pcm_s16le"]
        cmd += [target]
    elif fmt == "WEBM":
        cmd = [ffmpeg, "-y", "-i", source, "-c:v", "libvpx-vp9"]
        if crf is not None:
            cmd += ["-crf", str(crf)]
        if bitrate is not None:
            cmd += ["-b:v", f"{bitrate}k"]
        else:
            cmd += ["-b:v", "0"]
        cmd += ["-c:a", "libopus", "-b:a", "128k"]
        if speed != "Default":
            cmd += ["-deadline", speed.lower().replace(" ", "")]
        cmd += [target]
    else:
        # MP4/MKV: H.264 + AAC. CRF is preferred if no explicit bitrate.
        cmd = [ffmpeg, "-y", "-i", source, "-c:v", "libx264"]
        if crf is not None:
            cmd += ["-crf", str(crf)]
        if bitrate is not None:
            cmd += ["-b:v", f"{bitrate}k"]
        if speed != "Default":
            cmd += ["-preset", speed.lower().replace(" ", "")]
        cmd += ["-c:a", "aac", "-b:a", "192k", target]

    # Two-pass encoding is intentionally only used for explicit bitrate.
    # It is not used for the simple CRF path.
    if two_pass and bitrate is not None and fmt in ("MP4", "MKV"):
        duration = get_video_duration(source)
        if duration and duration > 0:
            passlog = os.path.join(output_dir, ".umd_2pass")
            first = [ffmpeg, "-y", "-i", source, "-c:v", "libx264", "-b:v", f"{bitrate}k",
                     "-pass", "1", "-passlogfile", passlog, "-an", "-f", "null", "NUL"]
            if speed != "Default":
                first[9:9] = ["-preset", speed.lower().replace(" ", "")]
            second = [ffmpeg, "-y", "-i", source, "-c:v", "libx264", "-b:v", f"{bitrate}k",
                      "-pass", "2", "-passlogfile", passlog, "-c:a", "aac", "-b:a", "192k", target]
            run_ffmpeg_with_progress(first, source, "Encoding pass 1 of 2")
            run_ffmpeg_with_progress(second, source, "Encoding pass 2 of 2")
            for suffix in ("-0.log", "-0.log.mbtree"):
                try:
                    os.remove(passlog + suffix)
                except OSError:
                    pass
        else:
            run_ffmpeg_with_progress(cmd, source, "Converting")
    else:
        # Keep the GUI progress/status live for the normal one-pass path too.
        run_ffmpeg_with_progress(cmd, source, "Converting")

    # Optional max-size refinement. We estimate a video bitrate from the target size
    # and re-encode once if the first conversion exceeds the requested size.
    if max_bytes and os.path.isfile(target) and os.path.getsize(target) > max_bytes and fmt in ("MP4", "MKV", "WEBM"):
        duration = get_video_duration(source)
        if duration and duration > 0:
            audio_kbps = 128
            total_kbps = max(100, int((max_bytes * 8 / duration) / 1000 * 0.92))
            video_kbps = max(100, total_kbps - audio_kbps)
            if fmt == "WEBM":
                retry = [ffmpeg, "-y", "-i", source, "-c:v", "libvpx-vp9", "-b:v", f"{video_kbps}k",
                         "-c:a", "libopus", "-b:a", f"{audio_kbps}k", target]
            else:
                retry = [ffmpeg, "-y", "-i", source, "-c:v", "libx264", "-b:v", f"{video_kbps}k",
                         "-c:a", "aac", "-b:a", f"{audio_kbps}k", target]
            run_ffmpeg_with_progress(retry, source, "Adjusting to target size")

    if os.path.isfile(target):
        if os.path.abspath(source) != os.path.abspath(target):
            try:
                os.remove(source)
            except OSError:
                pass
        return target
    return source

def download_worker(params):
    url, save_location, filename, choice, start, end, auth_method, browser, cookie_file, advanced = params
    before_snapshot = {}
    for _name in os.listdir(save_location):
        _path = os.path.join(save_location, _name)
        if os.path.isfile(_path):
            try:
                before_snapshot[_name] = os.path.getmtime(_path)
            except OSError:
                pass
    download_started_at = time.time()
    template_name = clean_filename(filename) if filename else "%(title)s"
    output_template = os.path.join(save_location, template_name + ".%(ext)s")
    log("--------------------------------------------------")
    log("Starting new download.")
    log(f"URL: {url}")
    log(f"Save location: {save_location}")
    log(f"Output template: {output_template}")
    log(f"Quality: {choice}")
    log(f"Authentication: {auth_method} / {browser if auth_method == 'Independent Browser Profile' else 'cookies.txt'}")

    def yt_progress_hook(data):
        status = data.get("status")
        if status == "downloading":
            total = data.get("total_bytes") or data.get("total_bytes_estimate")
            downloaded = data.get("downloaded_bytes", 0)
            if total:
                percent = max(0, min(100, int((downloaded / total) * 100)))
                speed = data.get("_speed_str", "").strip()
                eta = data.get("_eta_str", "").strip()
                root.after(
                    0,
                    lambda p=percent, sp=speed, et=eta:
                        update_progress(
                            p,
                            f"Status: Downloading... {p}%"
                            + (f" • {sp}" if sp else "")
                            + (f" • ETA {et}" if et else "")
                        )
                )
        elif status == "finished":
            root.after(0, lambda: update_progress(100, "Status: Download finished. Processing..."))

    options = build_options(output_template, choice, start, end)
    options["progress_hooks"] = [yt_progress_hook]

    if auth_method == "cookies.txt File":
        if not cookie_file or not os.path.isfile(cookie_file):
            raise RuntimeError("The selected cookies.txt file does not exist.")
        options["cookiefile"] = os.path.abspath(cookie_file)
        log("Using cookies.txt.")
    else:
        profile_path = os.path.join(PROFILE_ROOT, browser)
        if not profile_is_ready():
            raise RuntimeError(f"The independent {browser} profile is not ready. Open it, sign in, then close it.")
        options["cookiesfrombrowser"] = (BROWSER_IDS[browser], profile_path)
        log(f"Using independent {browser} profile: {profile_path}")

    root.after(0, lambda: status_label.configure(text="Status: Extracting media information..."))
    log("Extracting media information...")
    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=True)
        result = 0
        expected_base = clean_filename(filename) if filename else None
        if not expected_base and info:
            try:
                prepared = ydl.prepare_filename(info)
                expected_base = os.path.splitext(os.path.basename(prepared))[0]
            except Exception:
                expected_base = None
    log(f"yt-dlp returned: {result}")

    time.sleep(0.5)
    source = find_media_result(
        save_location,
        before_snapshot,
        expected_base=expected_base,
        started_at=download_started_at
    )
    if not source:
        recent = []
        for name in os.listdir(save_location):
            path = os.path.join(save_location, name)
            if os.path.isfile(path):
                try:
                    recent.append((os.path.getmtime(path), name))
                except OSError:
                    pass
        recent.sort(reverse=True)
        log("No output file identified. Most recent files in save folder:")
        for _, name in recent[:8]:
            log(f"  {name}")
        raise RuntimeError(
            "yt-dlp finished, but UMD could not identify the resulting media file. "
            "The most recent files in the save folder were listed in the Activity / Debug Log."
        )

    log(f"Downloaded file identified: {source}")
    final_file = source

    if advanced["conversion"] != "Keep Original":
        root.after(0, lambda: status_label.configure(text=f"Status: Converting to {advanced['conversion']}..."))
        log(f"Starting FFmpeg conversion: {advanced['conversion']}")
        base = clean_filename(filename) if filename else os.path.splitext(os.path.basename(source))[0]
        final_file = convert_media(source, advanced, save_location, base)
        log(f"Conversion complete: {final_file}")

    return final_file

def download_success(path):
    finish_progress()
    download_button.configure(state="normal")
    filename = os.path.basename(path)
    status_label.configure(text="Status: Download Complete!")
    log(f"SUCCESS: {filename}")
    messagebox.showinfo("Download Complete",
                        "Media downloaded successfully!\n\n"
                        f"File Name:\n{filename}\n\n"
                        f"Saved To:\n{os.path.abspath(path)}")

def download_failed(error):
    progress_bar.stop()
    progress_bar.configure(value=0)
    download_button.configure(state="normal")
    status_label.configure(text="Status: Download Failed")
    log(f"ERROR: {error}")
    messagebox.showerror("Download Failed", "The download failed.\n\nDetails:\n\n" + str(error))

def start_download():
    if not ffmpeg_exists():
        messagebox.showerror("FFmpeg Missing", "FFmpeg was not found. Place ffmpeg.exe beside UMD.py or add FFmpeg to PATH.")
        log("FFmpeg not found.")
        return
    url = url_var.get().strip()
    if not url:
        messagebox.showerror("Missing URL", "Please paste a URL first.")
        return
    save_location = output_var.get().strip() or APP_DIR
    save_location = os.path.abspath(save_location)
    if not os.path.isdir(save_location):
        messagebox.showerror("Invalid Folder", f"The selected save folder does not exist:\n\n{save_location}")
        return

    filename = filename_entry.get().strip()
    choice = format_var.get()
    start = start_var.get().strip()
    end = end_var.get().strip()
    auth_method = auth_method_var.get()
    browser = browser_var.get()
    cookie_file = cookie_var.get().strip()
    advanced = get_advanced_values()

    # Validate advanced fields before starting the thread.
    try:
        parse_crf(advanced["crf"])
        parse_bitrate(advanced["bitrate"])
        parse_size(advanced["max_size"])
    except ValueError as e:
        messagebox.showerror("Advanced Settings", str(e))
        return

    save_settings()
    download_button.configure(state="disabled")
    start_determinate_progress("Preparing download")
    params = (url, save_location, filename, choice, start, end, auth_method, browser, cookie_file, advanced)
    log("Download queued.")

    def worker():
        try:
            path = download_worker(params)
            root.after(0, lambda p=path: download_success(p))
        except Exception as e:
            root.after(0, lambda err=str(e): download_failed(err))

    threading.Thread(target=worker, daemon=True).start()

# ---------- update engine ----------
def update_engine():
    status_label.configure(text="Status: Updating yt-dlp...")
    update_button.configure(state="disabled")
    log("Updating yt-dlp and yt-dlp-ejs...")
    def worker():
        try:
            result = subprocess.run([sys.executable, "-m", "pip", "install", "-U", "yt-dlp", "yt-dlp-ejs"],
                                    text=True, capture_output=True)
            if result.returncode != 0:
                raise RuntimeError(result.stderr or "pip update failed.")
            log("Engine update completed.")
            root.after(0, lambda: status_label.configure(text="Status: Engine updated successfully!"))
        except Exception as e:
            log(f"Engine update failed: {e}")
            root.after(0, lambda err=str(e): messagebox.showerror("Update Failed", err))
        finally:
            root.after(0, lambda: update_button.configure(state="normal"))
    threading.Thread(target=worker, daemon=True).start()

update_button.configure(command=update_engine)
download_button.configure(command=start_download)

# ---------- traces / initialization ----------
browser_var.trace_add("write", lambda *_: update_auth_ui())
cookie_var.trace_add("write", lambda *_: update_auth_ui())
update_auth_ui()
apply_theme()
log("Universal Media Downloader started.")
log(f"Application directory: {APP_DIR}")
ff = get_ffmpeg()
if ff:
    log(f"FFmpeg detected: {ff}")
else:
    log("WARNING: FFmpeg not detected.")

root.mainloop()
