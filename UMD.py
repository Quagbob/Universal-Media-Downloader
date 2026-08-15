import sys, os, json, threading, subprocess
import tkinter as tk
from tkinter import messagebox, ttk
import yt_dlp

CONFIG_FILE = "config.json"
LIGHT_THEME = {
    "bg": "#F5F5F5", "frame_bg": "#F5F5F5", "text": "#1A1A1A", "sub_text": "#555555",
    "entry_bg": "#FFFFFF", "entry_fg": "#1A1A1A", "cursor": "#000000", "menu_bg": "#FFFFFF",
    "menu_fg": "#1A1A1A", "menu_active_bg": "#E0E0E0", "btn_update": "#2196F3",
    "btn_download": "#4CAF50", "btn_fg": "#FFFFFF", "btn_dl_fg": "#FFFFFF", "status_idle": "#757575"
}
DARK_THEME = {
    "bg": "#121212", "frame_bg": "#121212", "text": "#E0E0E0", "sub_text": "#A0A0A0",
    "entry_bg": "#1E1E1E", "entry_fg": "#FFFFFF", "cursor": "#FFFFFF", "menu_bg": "#1E1E1E",
    "menu_fg": "#E0E0E0", "menu_active_bg": "#333333", "btn_update": "#3700B3",
    "btn_download": "#03DAC6", "btn_fg": "#FFFFFF", "btn_dl_fg": "#000000", "status_idle": "#A0A0A0"
}

def load_settings():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f: return json.load(f)
        except: pass
    return {"format_choice": "Max Quality Available", "theme_choice": "Light"}

root = tk.Tk()
root.title("Universal Media Downloader")
root.geometry("540x440")
root.resizable(False, False)
saved_config = load_settings()

title_label = tk.Label(root, text="Universal Media Downloader Settings", font=("Arial", 15, "bold"))
title_label.pack(pady=10)

input_frame = tk.Frame(root)
input_frame.pack(fill="x", padx=20, pady=2)
url_label = tk.Label(input_frame, text="Paste Website Video Link:")
url_label.pack(anchor="w")
url_entry = tk.Entry(input_frame, font=("Arial", 13), width=50, borderwidth=1, relief="solid")
url_entry.pack(fill="x", pady=4)
url_entry.focus()

format_frame = tk.Frame(root)
format_frame.pack(fill="x", padx=20, pady=5)
format_label = tk.Label(format_frame, text="Select Output Quality / Resolution:")
format_label.pack(anchor="w")
format_options = ["Max Quality Available", "1080p (If available)", "720p", "480p", "Audio Only (MP3)"]
format_var = tk.StringVar(value=saved_config.get("format_choice", "Max Quality Available"))
format_menu = tk.OptionMenu(format_frame, format_var, *format_options)
format_menu.configure(bd=1, relief="solid", highlightthickness=0, anchor="w", font=("Arial", 12))
format_menu.pack(fill="x", pady=4)

trim_frame = tk.Frame(root)
trim_frame.pack(fill="x", padx=20, pady=5)
trim_label = tk.Label(trim_frame, text="Trim Video Chunk (Optional - Leave blank for full file):")
trim_label.pack(anchor="w")
grid_frame = tk.Frame(trim_frame)
grid_frame.pack(fill="x", pady=4)
start_label = tk.Label(grid_frame, text="Start (HH:MM:SS):")
start_label.pack(side="left", padx=(0, 5))
start_entry = tk.Entry(grid_frame, font=("Arial", 12), width=10, borderwidth=1, relief="solid")
start_entry.pack(side="left", padx=(0, 20))
end_label = tk.Label(grid_frame, text="End (HH:MM:SS):")
end_label.pack(side="left", padx=(0, 5))
end_entry = tk.Entry(grid_frame, font=("Arial", 12), width=10, borderwidth=1, relief="solid")
end_entry.pack(side="left")

theme_frame = tk.Frame(root)
theme_frame.pack(fill="x", padx=20, pady=5)
theme_label = tk.Label(theme_frame, text="Application Theme Mode:")
theme_label.pack(anchor="w")
theme_var = tk.StringVar(value=saved_config.get("theme_choice", "Light"))
theme_light_radio = None
theme_dark_radio = None

progress_bar = ttk.Progressbar(root, orient="horizontal", mode="indeterminate")
progress_bar.pack(fill="x", padx=20, pady=8)
status_label = tk.Label(root, text="Status: Ready", font=("Arial", 12, "italic"))
status_label.pack(pady=2)

button_frame = tk.Frame(root)
button_frame.pack(fill="x", padx=20, pady=10)
update_button = tk.Button(button_frame, text="Update Engine", font=("Arial", 12), bd=0, padx=10, pady=5)
update_button.pack(side="left", padx=5)
download_button = tk.Button(button_frame, text="Download Media", font=("Arial", 13, "bold"), bd=0, width=22, pady=4)
download_button.pack(side="right", padx=5)

def check_ffmpeg():
    if os.path.exists("ffmpeg.exe") or os.path.exists("ffmpeg"): return True
    try:
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return True
    except: return False

def save_settings():
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump({"format_choice": format_var.get(), "theme_choice": theme_var.get()}, f)
    except: pass

def apply_theme():
    p = DARK_THEME if theme_var.get() == "Dark" else LIGHT_THEME
    root.configure(bg=p["bg"])
    for f in [input_frame, format_frame, trim_frame, grid_frame, theme_frame, button_frame]: f.configure(bg=p["frame_bg"])
    for l in [title_label, url_label, format_label, trim_label, theme_label]: l.configure(bg=p["bg"], fg=p["text"], font=("Arial", 15, "bold") if l == title_label else ("Arial", 12))
    for l in [start_label, end_label]: l.configure(bg=p["bg"], fg=p["text"], font=("Arial", 11))
    status_label.configure(bg=p["bg"], fg=p["status_idle"])
    for e in [url_entry, start_entry, end_entry]: e.configure(bg=p["entry_bg"], fg=p["entry_fg"], insertbackground=p["cursor"])
    format_menu.configure(bg=p["menu_bg"], fg=p["menu_fg"], activebackground=p["menu_active_bg"], activeforeground=p["menu_fg"])
    format_menu["menu"].configure(bg=p["menu_bg"], fg=p["menu_fg"], activebackground=p["menu_active_bg"], activeforeground=p["menu_fg"], font=("Arial", 12))
    s = ttk.Style()
    s.theme_use("default")
    s.configure("TProgressbar", thickness=12, background="#BB86FC" if theme_var.get() == "Dark" else "#0D47A1", troughcolor=p["entry_bg"])
    if theme_light_radio and theme_dark_radio:
        for r in [theme_light_radio, theme_dark_radio]: r.configure(bg=p["bg"], fg=p["text"], selectcolor=p["entry_bg"], activebackground=p["bg"], activeforeground=p["text"], font=("Arial", 11))
    update_button.configure(bg=p["btn_update"], fg=p["btn_fg"])
    download_button.configure(bg=p["btn_download"], fg=p["btn_dl_fg"])
    save_settings()

def update_engine():
    status_label.config(text="Status: Checking for engine updates...")
    update_button.config(state="disabled")
    def run_pip():
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "-U", "yt-dlp[default]", "yt-dlp-ejs"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            root.after(0, lambda: status_label.config(text="Status: Engine updated successfully!"))
        except:
            root.after(0, lambda: status_label.config(text="Status: Update failed."))
        finally:
            root.after(0, lambda: update_button.config(state="normal"))
    threading.Thread(target=run_pip, daemon=True).start()

def run_download():
    if not check_ffmpeg():
        root.after(0, lambda: [progress_bar.stop(), download_button.config(state="normal"), status_label.config(text="Status: Missing FFmpeg!")])
        messagebox.showerror("Critical Error", "FFmpeg utilities not detected!\n\nPlease place 'ffmpeg.exe' in this folder.")
        return
    url = url_entry.get().strip()
    choice = format_var.get()
    start_time, end_time = start_entry.get().strip(), end_entry.get().strip()
    if not url:
        messagebox.showerror("Error", "Please paste a URL first!")
        return
    save_settings()
    status_label.config(text="Status: Extracting media...")
    download_button.config(state="disabled")
    progress_bar.start(10)
    ydl_opts = {'ignoreerrors': True}
    if start_time or end_time:
        actual_start = start_time if start_time else "00:00:00"
        actual_end = end_time if end_time else None
        ydl_opts['download_ranges'] = yt_dlp.utils.download_range_func(None, [{'start_time': yt_dlp.utils.timestr_to_secs(actual_start), 'end_time': yt_dlp.utils.timestr_to_secs(actual_end) if actual_end else None}])
        ydl_opts['force_keyframes_at_cuts'] = True
    if choice == "Audio Only (MP3)":
        ydl_opts.update({'format': 'bestaudio/best', 'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}]})
    else:
        ydl_opts['format'] = 'bestvideo[height<=1080]+bestaudio/best' if "1080p" in choice else 'bestvideo[height<=720]+bestaudio/best' if "720p" in choice else 'bestvideo[height<=480]+bestaudio/best' if "480p" in choice else 'bestvideo+bestaudio/best'
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl: ydl.download([url])
        status_label.config(text="Status: Download Complete!")
        messagebox.showinfo("Success", "Media downloaded successfully!")
    except Exception as e:
        status_label.config(text="Status: Download Failed")
        messagebox.showerror("Error", f"An error occurred:\n{str(e)}")
    finally:
        root.after(0, lambda: [progress_bar.stop(), download_button.config(state="normal")])

theme_light_radio = tk.Radiobutton(theme_frame, text="Light Mode", variable=theme_var, value="Light", command=apply_theme, font=("Arial", 11))
theme_light_radio.pack(side="left", padx=5, pady=2)
theme_dark_radio = tk.Radiobutton(theme_frame, text="Dark Mode", variable=theme_var, value="Dark", command=apply_theme, font=("Arial", 11))
theme_dark_radio.pack(side="left", padx=20, pady=2)
update_button.config(command=update_engine)
download_button.config(command=lambda: threading.Thread(target=run_download, daemon=True).start())
apply_theme()
root.mainloop()
