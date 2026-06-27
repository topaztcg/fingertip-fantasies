import os
import json
import datetime
import random
import time
from card_manager import CardManager

LEAGUES_CONFIG_FILE = "leagues_config.json"
FAKE_PLAYERS_FILE = "fake_players_config.json"
LEADERBOARD_DATA_FILE = "leaderboard_data.json"

def safe_read_json(filepath, default=None):
    for _ in range(10):
        try:
            if os.path.exists(filepath):
                with open(filepath, "r") as f:
                    return json.load(f)
        except (PermissionError, json.JSONDecodeError):
            time.sleep(0.05)
        except Exception:
            break
    return default if default is not None else {}

def safe_write_json(filepath, data):
    for _ in range(10):
        try:
            with open(filepath, "w") as f:
                json.dump(data, f, indent=4)
            return True
        except PermissionError:
            time.sleep(0.05)
    return False

class LeaderboardManager:
    def __init__(self):
        self.leagues = []
        self.fake_players = {}
        self.simulation_enabled = True
        self.data_file = LEADERBOARD_DATA_FILE
        self.data = {
            "current_season": "",
            "seasons": {}
        }
        self.card_mgr = CardManager()
        self.load_configs()
        self.load_data()
        self.check_season()

    def load_configs(self):
        # Leagues
        self.leagues = safe_read_json(LEAGUES_CONFIG_FILE, [])
        self.leagues.sort(key=lambda x: x.get("order", 999))

        # Fake Players
        fp_data = safe_read_json(FAKE_PLAYERS_FILE, {})
        self.simulation_enabled = fp_data.get("simulation_enabled", True)
        for bot in fp_data.get("bots", []):
            self.fake_players[bot["id"]] = bot

    def save_configs(self):
        # We don't save leagues config here, the editor does.
        # But we might need to save fake players if we add them programmatically.
        pass

    def load_data(self):
        data = safe_read_json(self.data_file, None)
        if data is not None:
            self.data = data

    def save_data(self):
        safe_write_json(self.data_file, self.data)

    def check_season(self):
        now = datetime.datetime.now()
        current_month_str = now.strftime("%Y-%m")
        
        saved_season = self.data.get("current_season", "")
        
        if not saved_season:
            # First time running
            self.data["current_season"] = current_month_str
            self.data["seasons"][current_month_str] = {"players": {}}
            self._init_season(current_month_str)
            self.save_data()
        elif saved_season != current_month_str:
            # New month reached! Soft reset.
            print(f"[Leaderboard] Season {saved_season} ended. Starting {current_month_str}.")
            self.data["current_season"] = current_month_str
            self.data["seasons"][current_month_str] = {"players": {}}
            self._init_season(current_month_str)
            self.save_data()

    def _init_season(self, season_id):
        # Populate the season with fake players at base points
        base_league = self.leagues[0]["id"] if self.leagues else "unranked"
        players = self.data["seasons"][season_id]["players"]
        for bot_id, bot in self.fake_players.items():
            players[bot_id] = {
                "name": bot["name"],
                "is_bot": True,
                "league": base_league,
                "points": 50, # Starting points
                "total_damage": 0
            }

    def get_player_data(self, player_id):
        season_id = self.data["current_season"]
        players = self.data["seasons"].get(season_id, {}).get("players", {})
        
        if player_id not in players:
            # Init real player
            base_league = self.leagues[0]["id"] if self.leagues else "unranked"
            players[player_id] = {
                "name": player_id,
                "is_bot": False,
                "league": base_league,
                "points": 50,
                "total_damage": 0,
                "wins": 0,
                "losses": 0,
                "games_played": 0
            }
            self.save_data()
            
        return players[player_id]

    def _get_league_index(self, league_id):
        for i, l in enumerate(self.leagues):
            if l["id"] == league_id: return i
        return 0

    def check_promotion_demotion(self, player_data):
        if not self.leagues: return
        
        pts = player_data["points"]
        idx = self._get_league_index(player_data["league"])
        curr_league = self.leagues[idx]
        
        # Promotion check
        if pts > curr_league.get("max_pts", 9999):
            if idx < len(self.leagues) - 1:
                next_league = self.leagues[idx + 1]
                player_data["league"] = next_league["id"]
                # Soft reset points into new league
                player_data["points"] = next_league["min_pts"] + 10
                print(f"[Leaderboard] {player_data['name']} promoted to {next_league['name']}!")
        
        # Demotion check
        elif pts < curr_league.get("min_pts", 0):
            if idx > 0:
                prev_league = self.leagues[idx - 1]
                player_data["league"] = prev_league["id"]
                # Soft reset points into previous league
                player_data["points"] = prev_league["max_pts"] - 10
                print(f"[Leaderboard] {player_data['name']} demoted to {prev_league['name']}...")
            else:
                player_data["points"] = curr_league.get("min_pts", 0) # Bottomed out

    def record_match(self, player_id, is_win, damage_dealt, opponent_name="Unknown", mvp_card=None):
        p_data = self.get_player_data(player_id)
        
        # Original points logic
        old_points = p_data["points"]
        pts_change = 25 if is_win else -15
        p_data["points"] = max(0, p_data["points"] + pts_change)
        actual_change = p_data["points"] - old_points
        
        p_data["total_damage"] += damage_dealt
        
        p_data["games_played"] = p_data.get("games_played", 0) + 1
        if is_win:
            p_data["wins"] = p_data.get("wins", 0) + 1
        else:
            p_data["losses"] = p_data.get("losses", 0) + 1
            
        # Match History Tracking
        if "match_history" not in p_data:
            p_data["match_history"] = []
            
        p_data["match_history"].append({
            "opponent": opponent_name,
            "win": is_win,
            "points_change": actual_change,
            "mvp_card": mvp_card,
            "timestamp": time.time()
        })
        
        # Keep only the last 30 matches
        if len(p_data["match_history"]) > 30:
            p_data["match_history"] = p_data["match_history"][-30:]
        
        self.check_promotion_demotion(p_data)
        self.save_data()
        
        # We no longer instantly simulate AI matches here.
        # background_simulator.py handles the slow 5-minute pacing.

    def simulate_background_ai_matches(self, num_matches=3):
        season_id = self.data["current_season"]
        players = self.data["seasons"].get(season_id, {}).get("players", {})
        
        bot_ids = [pid for pid, p in players.items() if p.get("is_bot", False)]
        if len(bot_ids) < 2: return
        
        for _ in range(num_matches):
            b1, b2 = random.sample(bot_ids, 2)
            # Headless Auto-Resolve
            # Give random win based on slightly weighted coinflip (maybe higher league wins more?)
            p1 = players[b1]
            p2 = players[b2]
            
            l1_idx = self._get_league_index(p1["league"])
            l2_idx = self._get_league_index(p2["league"])
            
            # Base 50/50. Each league difference adds 10% chance
            win_chance = 0.5 + ((l1_idx - l2_idx) * 0.1)
            win_chance = max(0.1, min(0.9, win_chance))
            
            b1_wins = random.random() < win_chance
            
            # Random damage between 20 and 150
            dmg1 = random.randint(20, 150)
            dmg2 = random.randint(20, 150)
            
            p1["total_damage"] += dmg1
            p2["total_damage"] += dmg2
            
            p1["games_played"] = p1.get("games_played", 0) + 1
            p2["games_played"] = p2.get("games_played", 0) + 1
            
            if b1_wins:
                p1["wins"] = p1.get("wins", 0) + 1
                p2["losses"] = p2.get("losses", 0) + 1
                p1["points"] += 25
                p2["points"] = max(0, p2["points"] - 15)
            else:
                p2["wins"] = p2.get("wins", 0) + 1
                p1["losses"] = p1.get("losses", 0) + 1
                p2["points"] += 25
                p1["points"] = max(0, p1["points"] - 15)
                
            self.check_promotion_demotion(p1)
            self.check_promotion_demotion(p2)
            
        self.save_data()

    def get_leaderboard(self, season_id=None, league_id=None):
        """Returns sorted list of players. Sorts by Points, then Total Damage."""
        if not season_id:
            season_id = self.data["current_season"]
            
        players = self.data.get("seasons", {}).get(season_id, {}).get("players", {})
        
        filtered = []
        for pid, p in players.items():
            if league_id and p["league"] != league_id:
                continue
            
            # inject pfp path for bots
            pfp = None
            if p.get("is_bot"):
                bot_conf = self.fake_players.get(pid)
                if bot_conf: pfp = bot_conf.get("pfp_path")
                
            filtered.append({
                "id": pid,
                "name": p["name"],
                "league": p["league"],
                "points": p["points"],
                "total_damage": p["total_damage"],
                "is_bot": p.get("is_bot", False),
                "pfp_path": pfp
            })
            
        # Sort descending by points, then total_damage
        filtered.sort(key=lambda x: (x["points"], x["total_damage"]), reverse=True)
        
        # Assign ranks
        for i, f in enumerate(filtered):
            f["rank"] = i + 1
            
        return filtered

    def get_all_seasons(self):
        seasons = list(self.data.get("seasons", {}).keys())
        seasons.sort(reverse=True) # newest first
        return seasons

    # --- REAL TIME MATCHMAKING ---
    def find_match(self, player_id):
        """Finds an opponent for the given player based on points and league."""
        self.load_data()
        self.check_season()
        
        p_data = self.get_player_data(player_id)
        p_league = p_data["league"]
        p_points = p_data["points"]
        
        all_players = self.get_leaderboard()
        
        # Check active state locks
        locked_bots = []
        state_file = "sim_state.json"
        if os.path.exists(state_file):
            try:
                with open(state_file, "r") as f:
                    st = json.load(f)
                    locked_bots = st.get("locked_bots", [])
                    # also add bots currently in active_matches
                    for m in st.get("active_matches", []):
                        locked_bots.append(m["bot1"])
                        locked_bots.append(m["bot2"])
            except: pass
            
        candidates = []
        for opp in all_players:
            if opp["id"] == player_id: continue
            if opp["is_bot"] and opp["name"] in locked_bots: continue
            if opp["league"] == p_league:
                candidates.append(opp)
                
        # If no candidates in exact league, fallback to anyone close in points
        if not candidates:
            for opp in all_players:
                if opp["id"] == player_id: continue
                if opp["is_bot"] and opp["name"] in locked_bots: continue
                candidates.append(opp)
                
        if not candidates:
            return None # Literally no opponents
            
        # Find closest by points
        candidates.sort(key=lambda x: abs(x["points"] - p_points))
        return candidates[0]
        
    def get_player_rank(self, player_id):
        all_players = self.get_leaderboard()
        for i, p in enumerate(all_players):
            if p["id"] == player_id:
                # Rank 1, 2, 3...
                return str(i + 1)
        return "N/A"
        
    def get_player_league_rank(self, player_id, league_id):
        league_players = self.get_leaderboard(league_id=league_id)
        for i, p in enumerate(league_players):
            if p["id"] == player_id:
                return str(i + 1)
        return "N/A"
        
    def lock_bot(self, bot_name):
        state_file = "sim_state.json"
        st = safe_read_json(state_file, {})
            
        locked = st.get("locked_bots", [])
        if bot_name not in locked:
            locked.append(bot_name)
            st["locked_bots"] = locked
            safe_write_json(state_file, st)
            
    def unlock_bot(self, bot_name):
        state_file = "sim_state.json"
        st = safe_read_json(state_file, {})
            
        locked = st.get("locked_bots", [])
        if bot_name in locked:
            locked.remove(bot_name)
            st["locked_bots"] = locked
            safe_write_json(state_file, st)

# --- INIT DEFAULT CONFIGS IF MISSING ---
def create_default_configs():
    if not os.path.exists(LEAGUES_CONFIG_FILE):
        default_leagues = [
            { "id": "finger_girl_1", "name": "Finger Girl I", "order": 1, "min_pts": 0, "max_pts": 99 },
            { "id": "finger_girl_2", "name": "Finger Girl II", "order": 2, "min_pts": 100, "max_pts": 249 },
            { "id": "finger_girl_3", "name": "Finger Girl III", "order": 3, "min_pts": 250, "max_pts": 499 },
            { "id": "dildo_girl_1", "name": "Dildo Girl I", "order": 4, "min_pts": 500, "max_pts": 9999 }
        ]
        with open(LEAGUES_CONFIG_FILE, "w") as f:
            json.dump(default_leagues, f, indent=4)
            
    if not os.path.exists(FAKE_PLAYERS_FILE):
        default_bots = {
            "simulation_enabled": True,
            "bots": [
                { "id": "bot_yuki", "name": "Yuki", "pfp_path": "" },
                { "id": "bot_akali", "name": "Akali", "pfp_path": "" },
                { "id": "bot_sam", "name": "Sam", "pfp_path": "" }
            ]
        }
        with open(FAKE_PLAYERS_FILE, "w") as f:
            json.dump(default_bots, f, indent=4)

create_default_configs()
