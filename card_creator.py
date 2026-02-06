import tkinter as tk
from tkinter import filedialog, messagebox
from card_manager import CardManager


# Helper to select file
def pick_file(entry_widget, file_type):
    if file_type == "image":
        ftypes = [("Images", "*.png;*.jpg;*.jpeg")]
    else:
        ftypes = [("Videos", "*.mp4;*.avi;*.mov;*.mpg")]

    path = filedialog.askopenfilename(filetypes=ftypes)
    if path:
        entry_widget.delete(0, tk.END)
        entry_widget.insert(0, path)


def save_card():
    # Gather Data
    data = {
        "name": entry_name.get(),
        "desc": text_desc.get("1.0", tk.END).strip(),
        "hp": entry_hp.get(),
        "energy_max": entry_en.get(),
        "moves": {
            "normal": {
                "name": entry_n_name.get(),
                "dmg": entry_n_dmg.get(),
                "desc": entry_n_desc.get()
            },
            "skill": {
                "name": entry_s_name.get(),
                "dmg": entry_s_dmg.get(),
                "cost": entry_s_cost.get(),
                "desc": entry_s_desc.get()
            },
            "ult": {
                "name": entry_u_name.get(),
                "dmg": entry_u_dmg.get(),
                "cost": entry_u_cost.get(),
                "desc": entry_u_desc.get()
            }
        }
    }

    # Get File Paths
    img = entry_img.get()
    vid_n = entry_vid_n.get()
    vid_s = entry_vid_s.get()
    vid_u = entry_vid_u.get()

    if not data["name"] or not img:
        messagebox.showerror("Error", "Name and Image are required!")
        return

    # Save
    mgr = CardManager()
    mgr.add_card(data, img, vid_n, vid_s, vid_u)
    messagebox.showinfo("Success", f"Card '{data['name']}' created!")
    root.destroy()  # Close tool


# --- GUI SETUP ---
root = tk.Tk()
root.title("Project TCG - Card Creator Tool")
root.geometry("600x800")

# Scrollable Canvas (in case screen small)
main_frame = tk.Frame(root)
main_frame.pack(fill=tk.BOTH, expand=1)
canvas = tk.Canvas(main_frame)
canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)
scrollbar = tk.Scrollbar(main_frame, orient=tk.VERTICAL, command=canvas.yview)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
canvas.configure(yscrollcommand=scrollbar.set)
canvas.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
frame = tk.Frame(canvas)
canvas.create_window((0, 0), window=frame, anchor="nw")

# --- FIELDS ---
tk.Label(frame, text="--- BASIC INFO ---", font=("Arial", 12, "bold")).pack(pady=10)
tk.Label(frame, text="Card Name:").pack()
entry_name = tk.Entry(frame, width=40)
entry_name.pack()

tk.Label(frame, text="Description:").pack()
text_desc = tk.Text(frame, height=3, width=40)
text_desc.pack()

tk.Label(frame, text="Max HP:").pack()
entry_hp = tk.Entry(frame)
entry_hp.pack()

tk.Label(frame, text="Max Energy (Ult Cost):").pack()
entry_en = tk.Entry(frame)
entry_en.pack()

# --- FILES ---
tk.Label(frame, text="--- MEDIA FILES ---", font=("Arial", 12, "bold")).pack(pady=10)


def make_file_picker(label_text, mode):
    f = tk.Frame(frame)
    f.pack(pady=2)
    tk.Label(f, text=label_text).pack(side=tk.LEFT)
    e = tk.Entry(f, width=30)
    e.pack(side=tk.LEFT, padx=5)
    tk.Button(f, text="Browse", command=lambda: pick_file(e, mode)).pack(side=tk.LEFT)
    return e


entry_img = make_file_picker("Card Image:", "image")
entry_vid_n = make_file_picker("Normal Atk Video:", "video")
entry_vid_s = make_file_picker("Skill Atk Video:", "video")
entry_vid_u = make_file_picker("Ult Atk Video:", "video")

# --- MOVES ---
tk.Label(frame, text="--- ATTACKS ---", font=("Arial", 12, "bold")).pack(pady=10)

# Normal
tk.Label(frame, text="[Normal Attack]", fg="blue").pack()
tk.Label(frame, text="Name / Dmg / Desc").pack()
entry_n_name = tk.Entry(frame);
entry_n_name.pack()
entry_n_dmg = tk.Entry(frame);
entry_n_dmg.pack()
entry_n_desc = tk.Entry(frame, width=40);
entry_n_desc.pack()

# Skill
tk.Label(frame, text="[Elemental Skill]", fg="green").pack(pady=5)
tk.Label(frame, text="Name / Dmg / Cost / Desc").pack()
entry_s_name = tk.Entry(frame);
entry_s_name.pack()
entry_s_dmg = tk.Entry(frame);
entry_s_dmg.pack()
entry_s_cost = tk.Entry(frame);
entry_s_cost.pack()
entry_s_desc = tk.Entry(frame, width=40);
entry_s_desc.pack()

# Ult
tk.Label(frame, text="[Elemental Burst]", fg="red").pack(pady=5)
tk.Label(frame, text="Name / Dmg / Cost / Desc").pack()
entry_u_name = tk.Entry(frame);
entry_u_name.pack()
entry_u_dmg = tk.Entry(frame);
entry_u_dmg.pack()
entry_u_cost = tk.Entry(frame);
entry_u_cost.pack()
entry_u_desc = tk.Entry(frame, width=40);
entry_u_desc.pack()

# SAVE
tk.Button(frame, text="CREATE CARD", bg="green", fg="white", font=("Arial", 14), command=save_card).pack(pady=20)

root.mainloop()