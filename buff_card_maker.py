import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import json
import os
import shutil

# --- CONFIG ---
BUFF_FILE = "assets/buffs.json"
IMG_DIR = "assets/buff_images"

# Ensure directories exist
os.makedirs(os.path.dirname(BUFF_FILE), exist_ok=True)
os.makedirs(IMG_DIR, exist_ok=True)


def load_buffs():
    if not os.path.exists(BUFF_FILE):
        return []
    try:
        with open(BUFF_FILE, "r") as f:
            return json.load(f)
    except:
        return []


def save_buffs_to_json(buff_list):
    with open(BUFF_FILE, "w") as f:
        json.dump(buff_list, f, indent=4)


def browse_image():
    file_path = filedialog.askopenfilename(
        title="Select Buff Image",
        filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.bmp")]
    )
    if file_path:
        entry_img.delete(0, tk.END)
        entry_img.insert(0, file_path)


def save_buff():
    # 1. Gather Input
    name = entry_name.get().strip()
    b_type = combo_type.get()
    desc = entry_desc.get("1.0", tk.END).strip()
    src_img_path = entry_img.get().strip()

    # Validation
    if not name:
        messagebox.showerror("Error", "Buff Name is required!")
        return

    # Image is optional, but recommended
    dest_path = ""
    if src_img_path:
        if not os.path.exists(src_img_path):
            messagebox.showerror("Error", "Image file not found!")
            return

        # Copy image to game assets
        filename = os.path.basename(src_img_path)
        dest_path = os.path.join(IMG_DIR, filename)
        try:
            shutil.copy(src_img_path, dest_path)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to copy image: {e}")
            return

    try:
        val = int(entry_val.get())
    except ValueError:
        val = 1  # Default

    try:
        duration = int(entry_dur.get())
    except ValueError:
        duration = 0  # Instant

    # 2. Auto-Determine Category & Color
    # Buffs help allies, Debuffs hurt enemies
    category = "BUFF" if b_type in ["HEAL", "BUFF_ATK", "BUFF_DEF"] else "DEBUFF"

    # Preset colors for UI borders
    colors = {
        "HEAL": [100, 255, 100],  # Green
        "BUFF_ATK": [255, 100, 100],  # Red
        "BUFF_DEF": [100, 100, 255],  # Blue
        "DEBUFF_FREEZE": [100, 255, 255],  # Cyan
        "DEBUFF_DOT": [200, 0, 200]  # Purple
    }
    color = colors.get(b_type, [200, 200, 200])

    # 3. Construct Data Object
    b_id = name.lower().replace(" ", "_")

    new_buff = {
        "id": b_id,
        "name": name,
        "type": b_type,
        "category": category,
        "val": val,
        "duration": duration,
        "desc": desc,
        "color": color,
        "image_path": dest_path
    }

    # 4. Save
    buffs = load_buffs()
    # Remove existing if overwriting (same ID)
    buffs = [b for b in buffs if b["id"] != b_id]
    buffs.append(new_buff)

    save_buffs_to_json(buffs)

    messagebox.showinfo("Success", f"Buff Card '{name}' Saved!")

    # Reset fields for next card
    entry_name.delete(0, tk.END)
    entry_desc.delete("1.0", tk.END)
    entry_img.delete(0, tk.END)


# --- GUI SETUP ---
root = tk.Tk()
root.title("Project TCG - Buff Card Creator")
root.geometry("500x700")

# Main Container
frame = tk.Frame(root, padx=20, pady=20)
frame.pack(fill=tk.BOTH, expand=True)

tk.Label(frame, text="CREATE BUFF CARD", font=("Arial", 16, "bold")).pack(pady=10)

# Name
tk.Label(frame, text="Buff Name:", anchor="w").pack(fill=tk.X)
entry_name = tk.Entry(frame)
entry_name.pack(fill=tk.X, pady=5)

# Type Dropdown
tk.Label(frame, text="Effect Type:", anchor="w").pack(fill=tk.X)
types = ["HEAL", "BUFF_ATK", "BUFF_DEF", "DEBUFF_FREEZE", "DEBUFF_DOT"]
combo_type = ttk.Combobox(frame, values=types, state="readonly")
combo_type.current(0)
combo_type.pack(fill=tk.X, pady=5)

# Stats Container
stats_frame = tk.Frame(frame)
stats_frame.pack(fill=tk.X, pady=5)

# Value
tk.Label(stats_frame, text="Value (Power):").pack(side=tk.LEFT)
entry_val = tk.Entry(stats_frame, width=10)
entry_val.insert(0, "3")
entry_val.pack(side=tk.LEFT, padx=10)

# Duration
tk.Label(stats_frame, text="Duration (Turns):").pack(side=tk.LEFT)
entry_dur = tk.Entry(stats_frame, width=10)
entry_dur.insert(0, "0")
entry_dur.pack(side=tk.LEFT, padx=10)

# Helper Text
tk.Label(frame, text="(Duration 0 = Instant use. Duration > 0 = Status Effect)",
         font=("Arial", 8), fg="gray").pack(anchor="w")

# Description
tk.Label(frame, text="Description:", anchor="w").pack(fill=tk.X, pady=(10, 0))
entry_desc = tk.Text(frame, height=3, width=40)
entry_desc.pack(fill=tk.X, pady=5)

# Image Picker
tk.Label(frame, text="Card Image:", anchor="w").pack(fill=tk.X)
img_frame = tk.Frame(frame)
img_frame.pack(fill=tk.X, pady=5)

entry_img = tk.Entry(img_frame)
entry_img.pack(side=tk.LEFT, expand=True, fill=tk.X)
btn_browse = tk.Button(img_frame, text="Browse", command=browse_image)
btn_browse.pack(side=tk.RIGHT, padx=5)

# Save Button
tk.Button(frame, text="SAVE BUFF", bg="green", fg="white",
          font=("Arial", 12, "bold"), height=2, command=save_buff).pack(pady=30, fill=tk.X)

root.mainloop()