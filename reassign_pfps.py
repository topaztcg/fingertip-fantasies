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

    # Get all available PFPs from the folder
    extensions = ('*.png', '*.jpg', '*.jpeg')
    available_pfps = []
    for ext in extensions:
        available_pfps.extend(glob.glob(os.path.join(PFP_DIR, ext)))

    # Convert paths to a uniform format
    available_pfps = [os.path.normpath(p) for p in available_pfps]

    bots = data.get("bots", [])
    
    print("--- FULL PFP REASSIGNMENT SCRIPT ---")
    print(f"Total Bots to Assign: {len(bots)}")
    print(f"Total Available PFPs in folder: {len(available_pfps)}")
    print("------------------------------------")

    # Shuffle the pool so everyone gets a random new PFP
    random.shuffle(available_pfps)

    assignments = 0

    for bot in bots:
        if available_pfps:
            new_pfp = available_pfps.pop()
            bot["pfp_path"] = new_pfp.replace("\\", "/") # Save with forward slashes
            assignments += 1
            print(f"[*] Reassigned '{bot['pfp_path']}' to {bot.get('name', 'Unknown Bot')}")
        else:
            print(f"[-] Ran out of unique PFPs! {bot.get('name', 'Unknown Bot')} will not have a PFP.")
            bot["pfp_path"] = "" 

    with open(CONFIG_FILE, 'w') as f:
        json.dump(data, f, indent=4)
        
    print(f"\n[+] Successfully reassigned {assignments} PFPs!")

if __name__ == "__main__":
    main()
