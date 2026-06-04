import json
import os

LEADERBOARD_FILE = "leaderboard_data.json"
LEAGUES_FILE = "leagues_config.json"

def main():
    if not os.path.exists(LEADERBOARD_FILE):
        print("No leaderboard file found.")
        return

    with open(LEADERBOARD_FILE, "r") as f:
        data = json.load(f)

    leagues = []
    if os.path.exists(LEAGUES_FILE):
        with open(LEAGUES_FILE, "r") as f:
            leagues = json.load(f)

    if not leagues:
        print("No leagues config found, using fallback base league.")
        base_league = "finger_girl_1"
        base_points = 50
    else:
        # Assuming leagues are ordered, grab the one with order 1 or first in list
        leagues.sort(key=lambda x: x.get("order", 999))
        base_league = leagues[0]["id"]
        base_points = leagues[0].get("min_pts", 0) + 50  # Give 50 starting points

    season_id = data.get("current_season")
    if not season_id or season_id not in data.get("seasons", {}):
        print("No active season found.")
        return

    players = data["seasons"][season_id].get("players", {})
    reset_count = 0
    for pid, p in players.items():
        p["points"] = base_points
        p["total_damage"] = 0
        p["wins"] = 0
        p["losses"] = 0
        p["games_played"] = 0
        p["league"] = base_league
        reset_count += 1

    with open(LEADERBOARD_FILE, "w") as f:
        json.dump(data, f, indent=4)

    print(f"Successfully reset {reset_count} players to {base_league} with {base_points} points and 0 wins/losses.")

    # Also clear active matches in sim_state so there are no lingering matches distributing points
    state_file = "sim_state.json"
    if os.path.exists(state_file):
        with open(state_file, "r") as f:
            state = json.load(f)
        state["active_matches"] = []
        with open(state_file, "w") as f:
            json.dump(state, f, indent=4)
        print("Cleared active simulated matches.")

if __name__ == "__main__":
    main()
