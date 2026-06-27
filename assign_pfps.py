import os
import json
import random
import glob

PFP_DIR = "assets/pfps"
CONFIG_FILE = "fake_players_config.json"

def main():
    if not os.path.exists(PFP_DIR):
        print(f"Directory {PFP_DIR} does not exist. Created it.")
        os.makedirs(PFP_DIR, exist_ok=True)
        print("Please add some images to this directory and run the script again.")
        return

    if not os.path.exists(CONFIG_FILE):
        print(f"Config file {CONFIG_FILE} not found!")
        return

    with open(CONFIG_FILE, 'r') as f:
        data = json.load(f)

    # Get all available PFPs from the folder (excluding .webp since pygame might not support it)
    extensions = ('*.png', '*.jpg', '*.jpeg')
    available_pfps = []
    for ext in extensions:
        available_pfps.extend(glob.glob(os.path.join(PFP_DIR, ext)))

    # Convert paths to a uniform format for easy comparison
    available_pfps = [os.path.normpath(p) for p in available_pfps]

    # Find existing assigned PFPs
    assigned_pfps = set()
    bots = data.get("bots", [])
    
    for bot in bots:
        pfp = bot.get("pfp_path", "")
        if pfp and os.path.exists(pfp):
            norm_pfp = os.path.normpath(pfp)
            assigned_pfps.add(norm_pfp)

    # Filter out available PFPs that are already assigned
    unassigned_pfps = [p for p in available_pfps if p not in assigned_pfps]

    print("--- PFP ASSIGNMENT SCRIPT ---")
    print(f"Total Bots: {len(bots)}")
    print(f"Total Available PFPs in folder: {len(available_pfps)}")
    print(f"PFPs already assigned to a bot: {len(assigned_pfps)}")
    print(f"Unique PFPs left to assign: {len(unassigned_pfps)}")
    print("-----------------------------")

    random.shuffle(unassigned_pfps)

    new_assignments = 0

    for bot in bots:
        # Check if bot already has a valid PFP
        if bot.get("pfp_path") and os.path.exists(bot["pfp_path"]):
            continue
            
        # Bot needs a new PFP
        if unassigned_pfps:
            new_pfp = unassigned_pfps.pop()
            bot["pfp_path"] = new_pfp.replace("\\", "/") # Save with forward slashes
            new_assignments += 1
            print(f"[*] Assigned '{bot['pfp_path']}' to {bot.get('name', 'Unknown Bot')}")
        else:
            print(f"[-] Ran out of unique PFPs! Could not assign to {bot.get('name', 'Unknown Bot')}")
            # Ensure invalid path is cleared so it doesn't crash
            bot["pfp_path"] = "" 

    if new_assignments > 0:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(data, f, indent=4)
        print(f"\n[+] Successfully assigned {new_assignments} new unique PFPs!")
    else:
        print("\n[-] No new PFPs were assigned. Everyone either has a PFP or the pool is empty.")

if __name__ == "__main__":
    main()
