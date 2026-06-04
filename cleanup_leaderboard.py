import json
import os

LEADERBOARD_FILE = "leaderboard_data.json"

def main():
    if not os.path.exists(LEADERBOARD_FILE):
        return

    with open(LEADERBOARD_FILE, "r") as f:
        data = json.load(f)

    season_id = data.get("current_season")
    if not season_id or season_id not in data.get("seasons", {}):
        return

    players = data["seasons"][season_id].get("players", {})
    to_delete = []
    
    for pid, p in players.items():
        if pid not in ["Ember", "Guest"] and not pid.startswith("bot_"):
            to_delete.append(pid)
            
    for pid in to_delete:
        del players[pid]
        
    with open(LEADERBOARD_FILE, "w") as f:
        json.dump(data, f, indent=4)
        
    print(f"Purged {len(to_delete)} fake human profiles.")
    
    # Also cancel any existing matches using old schema
    state_file = "sim_state.json"
    if os.path.exists(state_file):
        with open(state_file, "r") as f:
            state = json.load(f)
        state["active_matches"] = []
        with open(state_file, "w") as f:
            json.dump(state, f, indent=4)

if __name__ == "__main__":
    main()
