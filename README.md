# Universal Media Downloader

[![Latest Release](https://shields.io)](https://github.com)

***

## 🚀 Quick Start Guide

To ensure the downloader works perfectly without any errors, please follow these simple rules:

### 1. Do Not Separate the Files (Easiest Method)
The application requires `ffmpeg.exe` and `ffprobe.exe` to live in the **exact same folder** as the downloader executable. 
> ⚠️ **Important:** If you move `UMD.exe` out by itself, it will fail and show a **"Missing FFmpeg"** error.

### 2. How to Create a Desktop Shortcut
If you want a clean icon on your desktop without breaking the app:
* **Right-click** `UMD.exe`.
* Select **Send to** ➡️ **Desktop (create shortcut)**.
* You can now move that new desktop shortcut anywhere you want, while leaving the original engine files safe inside this folder!

### 3. Hit an Access Block?
If a website updates its code and your download fails, simply click the **"Update Engine"** button inside the app to automatically download the latest fixes.

***

## 🛠️ Advanced: Make Windows Find FFmpeg Automatically

If you want to move `UMD.exe` completely by itself anywhere on your PC without keeping the extra FFmpeg files in the same folder, you must install FFmpeg globally to your Windows System PATH.

1. **Move the folder:** Place this entire unzipped folder in a permanent spot on your PC.
   * *Example:* `C:\Program Files\Universal Media Downloader`
2. **Open Settings:** Click your Windows Start Menu, type `env`, and select **Edit the system environment variables**.
3. **Environment Variables:** Click the **Environment Variables...** button at the bottom right of the window.
4. **Edit Path:** Under the **User variables** box (the top box), find the variable named `Path` and click **Edit...**.
5. **Add New Path:** Click **New** on the right side, and paste the exact path to the folder where your `ffmpeg.exe` is stored.
   * *Example:* `C:\Program Files\Universal Media Downloader`
6. **Save & Restart:** Click **OK** on all windows to save your changes. Restart the app or any open terminal windows.

*Windows will now find FFmpeg automatically on your machine from any folder location!*
