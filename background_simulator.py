import tkinter as tk
from tkinter import font as tkfont
import json
import random
import os
import time
import threading
import hashlib
from datetime import datetime, timezone
from leaderboard_manager import LeaderboardManager
import sys

CONFIG_FILE = "fake_players_config.json"
CARDS_FILE = "cards_data.json"
STATE_FILE = "sim_state.json"

lb_mgr = LeaderboardManager()

# --- THEME CONSTANTS ---
BG_COLOR = "#0f0f13"
PANEL_COLOR = "#1a1a24"
TEXT_COLOR = "#e0e0e0"
ACCENT_COLOR = "#ff66aa"
GREEN_COLOR = "#4ade80"
RED_COLOR = "#f87171"
MUTED_COLOR = "#6b7280"

class SimulatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Fingertip Fantasies - Background Simulator")
        self.root.geometry("850x650")
        self.root.configure(bg=BG_COLOR)
        
        try:
            self.title_font = tkfont.Font(family="Segoe UI", size=20, weight="bold")
            self.log_font = tkfont.Font(family="Consolas", size=11)
            self.btn_font = tkfont.Font(family="Segoe UI", size=10, weight="bold")
        except:
            self.title_font = ("Helvetica", 20, "bold")
            self.log_font = ("Courier", 11)
            self.btn_font = ("Helvetica", 10, "bold")
            
        self.setup_ui()
        self.running = True
        
        self.all_cards = self.load_cards()
        self.state = self.load_state()
        
        self.sim_thread = threading.Thread(target=self.simulation_loop, daemon=True)
        self.sim_thread.start()

    def load_state(self):
        default = {"active_matches": []}
        for _ in range(10):
            try:
                if os.path.exists(STATE_FILE):
                    with open(STATE_FILE, "r") as f:
                        return json.load(f)
                break
            except (PermissionError, json.JSONDecodeError):
                time.sleep(0.05)
            except Exception:
                break
        return default

    def save_state(self):
        for _ in range(10):
            try:
                with open(STATE_FILE, "w") as f:
                    json.dump(self.state, f)
                return
            except PermissionError:
                time.sleep(0.05)

    def load_cards(self):
        if os.path.exists(CARDS_FILE):
            try:
                with open(CARDS_FILE, "r") as f:
                    return json.load(f)
            except: pass
        return []

    def get_bots(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    d = json.load(f)
                    return d.get("simulation_enabled", True), d.get("bots", [])
            except: pass
        return True, []

    def setup_ui(self):
        header_frame = tk.Frame(self.root, bg=BG_COLOR)
        header_frame.pack(fill=tk.X, padx=20, pady=20)
        
        tk.Label(header_frame, text="BACKGROUND SIMULATOR", font=self.title_font, fg=TEXT_COLOR, bg=BG_COLOR).pack(side=tk.LEFT)
        
        self.status_lbl = tk.Label(header_frame, text="STATUS: INITIALIZING", font=self.btn_font, fg=MUTED_COLOR, bg=BG_COLOR)
        self.status_lbl.pack(side=tk.LEFT, padx=20)
        
        self.stats_lbl = tk.Label(header_frame, text="Active Matches: 0", font=self.btn_font, fg=ACCENT_COLOR, bg=BG_COLOR)
        self.stats_lbl.pack(side=tk.LEFT, padx=20)
        
        btn_clear = tk.Button(header_frame, text="CLEAR LOGS", font=self.btn_font, bg=PANEL_COLOR, fg=TEXT_COLOR,
                              activebackground=ACCENT_COLOR, activeforeground="#fff", bd=0, padx=15, pady=5,
                              cursor="hand2", command=self.clear_logs)
        btn_clear.pack(side=tk.RIGHT)
        
        btn_cancel_all = tk.Button(header_frame, text="CANCEL & EXIT", font=self.btn_font, bg=RED_COLOR, fg="#fff",
                               activebackground="#991b1b", activeforeground="#fff", bd=0, padx=15, pady=5,
                               cursor="hand2", command=self.cancel_matches)
        btn_cancel_all.pack(side=tk.RIGHT, padx=10)
        
        from tkinter import ttk
        
        # Main PanedWindow
        self.main_pane = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, bg=BG_COLOR, sashwidth=4)
        self.main_pane.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))
        
        # Left Frame for Logs
        self.log_frame = tk.Frame(self.main_pane, bg=PANEL_COLOR)
        self.log_text = tk.Text(self.log_frame, bg=PANEL_COLOR, fg=TEXT_COLOR, font=self.log_font, bd=0, 
                                highlightthickness=1, highlightbackground="#333", highlightcolor=ACCENT_COLOR,
                                padx=10, pady=10, state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.main_pane.add(self.log_frame, minsize=400)
        
        self.log_text.tag_configure("win", foreground=GREEN_COLOR)
        self.log_text.tag_configure("loss", foreground=RED_COLOR)
        self.log_text.tag_configure("system", foreground=ACCENT_COLOR)
        self.log_text.tag_configure("match", foreground="#a78bfa")
        self.log_text.tag_configure("warn", foreground="#fcd34d")
        
        # Right Frame for Bots List
        self.bot_frame = tk.Frame(self.main_pane, bg=PANEL_COLOR)
        
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", background=PANEL_COLOR, foreground=TEXT_COLOR, fieldbackground=PANEL_COLOR, borderwidth=0, rowheight=25)
        style.configure("Treeview.Heading", background="#333", foreground=TEXT_COLOR, font=self.btn_font)
        style.map('Treeview', background=[('selected', ACCENT_COLOR)])
        
        columns = ("name", "status")
        self.bot_tree = ttk.Treeview(self.bot_frame, columns=columns, show="headings")
        self.bot_tree.heading("name", text="Bot Name")
        self.bot_tree.heading("status", text="Status")
        self.bot_tree.column("name", width=120)
        self.bot_tree.column("status", width=100)
        
        tree_scroll = ttk.Scrollbar(self.bot_frame, orient=tk.VERTICAL, command=self.bot_tree.yview)
        self.bot_tree.configure(yscrollcommand=tree_scroll.set)
        
        self.bot_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.main_pane.add(self.bot_frame, minsize=200)

    def log(self, msg, tag=None):
        self.log_text.config(state=tk.NORMAL)
        if tag:
            self.log_text.insert(tk.END, msg + "\n", tag)
        else:
            self.log_text.insert(tk.END, msg + "\n")
            
        # Keep only last 500 lines to prevent memory issues
        lines = int(self.log_text.index('end-1c').split('.')[0])
        if lines > 500:
            self.log_text.delete("1.0", "2.0")
            
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def clear_logs(self):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.log("Logs cleared.", "system")

    def cancel_matches(self):
        self.state["active_matches"] = []
        self.save_state()
        self.running = False
        self.root.destroy()
        sys.exit(0)

    # --- SIMULATION LOGIC ---
    def evaluate_card(self, c):
        score = c.get("max_hp", 0) * 0.5
        moves = c.get("moves", {})
        score += int(moves.get("normal", {}).get("dmg", 0)) * 2
        score += int(moves.get("skill", {}).get("dmg", 0)) * 1.5
        score += int(moves.get("ult", {}).get("dmg", 0))
        return score

    def get_strong_deck(self):
        if not self.all_cards: return []
        sorted_cards = sorted(self.all_cards, key=self.evaluate_card, reverse=True)
        top_pool = sorted_cards[:min(10, len(sorted_cards))]
        return random.sample(top_pool, min(3, len(top_pool)))

    class HeadlessCard:
        def __init__(self, data):
            self.data = data
            self.max_hp = data.get("max_hp", 10)
            self.current_hp = self.max_hp
            self.energy = 0
            self.max_energy = 5
            self.is_dead = False
            self.damage_dealt = 0
            
        def take_damage(self, amount):
            if self.is_dead: return
            self.current_hp -= amount
            if self.current_hp <= 0:
                self.current_hp = 0
                self.is_dead = True
                
        def consume_energy(self, amount):
            if self.energy >= amount:
                self.energy -= amount
                return True
            return False

    def resolve_combat(self):
        deck1 = self.get_strong_deck()
        deck2 = self.get_strong_deck()
        
        team1 = [self.HeadlessCard(c) for c in deck1]
        team2 = [self.HeadlessCard(c) for c in deck2]
        
        if not team1 or not team2: return True, 0, 0 # Default T1 win if no cards
            
        dmg1, dmg2 = 0, 0
        round_num = 1
        
        while True:
            t1_alive = [c for c in team1 if not c.is_dead]
            t2_alive = [c for c in team2 if not c.is_dead]
            
            def get_mvps():
                m1 = max(team1, key=lambda c: c.damage_dealt).data.get("id") if team1 else None
                m2 = max(team2, key=lambda c: c.damage_dealt).data.get("id") if team2 else None
                return m1, m2
            
            if not t1_alive:
                m1, m2 = get_mvps()
                return False, dmg1, dmg2, m1, m2
            if not t2_alive:
                m1, m2 = get_mvps()
                return True, dmg1, dmg2, m1, m2
                
            # Team 1 Attack
            attacker = random.choice(t1_alive)
            target = random.choice(t2_alive)
            moves = attacker.data.get("moves", {})
            cost, dmg = 0, int(moves.get("normal", {}).get("dmg", 0))
            if attacker.energy >= int(moves.get("ult", {}).get("cost", 99)):
                cost, dmg = int(moves.get("ult", {}).get("cost", 0)), int(moves.get("ult", {}).get("dmg", 0))
            elif attacker.energy >= int(moves.get("skill", {}).get("cost", 99)):
                cost, dmg = int(moves.get("skill", {}).get("cost", 0)), int(moves.get("skill", {}).get("dmg", 0))
            
            if cost == 0: attacker.energy = min(5, attacker.energy + 1)
            else: attacker.consume_energy(cost)
            target.take_damage(dmg)
            attacker.damage_dealt += dmg
            dmg1 += dmg
            
            # Team 2 Attack
            t2_alive = [c for c in team2 if not c.is_dead]
            if t2_alive:
                attacker = random.choice(t2_alive)
                t1_alive = [c for c in team1 if not c.is_dead]
                if t1_alive:
                    target = random.choice(t1_alive)
                    moves = attacker.data.get("moves", {})
                    cost, dmg = 0, int(moves.get("normal", {}).get("dmg", 0))
                    if attacker.energy >= int(moves.get("ult", {}).get("cost", 99)):
                        cost, dmg = int(moves.get("ult", {}).get("cost", 0)), int(moves.get("ult", {}).get("dmg", 0))
                    elif attacker.energy >= int(moves.get("skill", {}).get("cost", 99)):
                        cost, dmg = int(moves.get("skill", {}).get("cost", 0)), int(moves.get("skill", {}).get("dmg", 0))
                    
                    if cost == 0: attacker.energy = min(5, attacker.energy + 1)
                    else: attacker.consume_energy(cost)
                    target.take_damage(dmg)
                    attacker.damage_dealt += dmg
                    dmg2 += dmg
                    
            round_num += 1
            if round_num > 50:
                m1, m2 = get_mvps()
                return random.choice([True, False]), dmg1, dmg2, m1, m2 # Coin toss on timeout

    def is_bot_online(self, bot_id, current_timestamp):
        # Consistent daily schedule hash
        dt = datetime.fromtimestamp(current_timestamp)
        day_str = dt.strftime("%Y-%m-%d")
        hash_input = f"{bot_id}_{day_str}".encode('utf-8')
        h = int(hashlib.md5(hash_input).hexdigest(), 16)
        
        start_hour = h % 24 # 0 to 23
        duration = 3 + (h % 3) # 3 to 5 hours
        end_hour = start_hour + duration
        
        # Check standard window or wrapped window
        if start_hour <= dt.hour < end_hour:
            return True
        if end_hour > 24 and dt.hour < (end_hour % 24):
            return True
        return False

    def simulation_loop(self):
        self.root.after(0, lambda: self.log("Simulation Engine Started. Processing Async Matches...", "system"))
        
        while self.running:
            sim_enabled, bots = self.get_bots()
            
            if not sim_enabled:
                self.root.after(0, lambda: self.status_lbl.config(text="STATUS: GLOBALLY DISABLED", fg=RED_COLOR))
                time.sleep(5)
                continue
                
            self.root.after(0, lambda: self.status_lbl.config(text="STATUS: RUNNING EVENT LOOP", fg=GREEN_COLOR))
            
            # Refresh leaderboard to get actual points for matchmaking
            lb_mgr.load_data()
            lb_mgr.check_season()
            all_lb = lb_mgr.get_leaderboard()
            points_map = {p["name"]: p["points"] for p in all_lb}
            league_map = {p["name"]: p["league"] for p in all_lb}
            
            curr_time = time.time()
            
            # --- 1. RESOLVE FINISHED MATCHES ---
            active = self.state.get("active_matches", [])
            ongoing = []
            
            for m in active:
                if curr_time >= m["end_time"]:
                    # Resolve Match
                    b1, b2 = m["bot1_id"], m["bot2_id"]
                    t1_wins, dmg1, dmg2, mvp1, mvp2 = self.resolve_combat()
                    
                    winner = b1 if t1_wins else b2
                    loser = b2 if t1_wins else b1
                    dmg_w = dmg1 if t1_wins else dmg2
                    dmg_l = dmg2 if t1_wins else dmg1
                    mvp_w = mvp1 if t1_wins else mvp2
                    mvp_l = mvp2 if t1_wins else mvp1
                    
                    lb_mgr.record_match(winner, True, dmg_w, m["bot2_name"] if t1_wins else m["bot1_name"], mvp_w)
                    lb_mgr.record_match(loser, False, dmg_l, m["bot1_name"] if t1_wins else m["bot2_name"], mvp_l)
                    
                    if "bot_cooldowns" not in self.state:
                        self.state["bot_cooldowns"] = {}
                    
                    gap_time_b1 = random.uniform(1.0, 5.0) * 60
                    gap_time_b2 = random.uniform(1.0, 5.0) * 60
                    
                    self.state["bot_cooldowns"][b1] = {
                        "next_available": curr_time + gap_time_b1,
                        "last_opponent": b2
                    }
                    self.state["bot_cooldowns"][b2] = {
                        "next_available": curr_time + gap_time_b2,
                        "last_opponent": b1
                    }
                    
                    msg = f"🏆 [RESOLVED] {m['bot1_name']} vs {m['bot2_name']} | Winner: {m['bot1_name'] if t1_wins else m['bot2_name']}"
                    self.root.after(0, lambda m=msg: self.log(m, "win"))
                else:
                    ongoing.append(m)
                    
            self.state["active_matches"] = ongoing
            if len(ongoing) != len(active):
                self.save_state()
            self.root.after(0, lambda: self.stats_lbl.config(text=f"Active Matches: {len(ongoing)}"))
            
            # --- UPDATE UI BOT LIST ---
            # Prepare bot status dictionary
            bot_status = {}
            for b in bots:
                b_name = b["name"]
                if self.is_bot_online(b["id"], curr_time):
                    bot_status[b_name] = "ONLINE (IDLE)"
                else:
                    bot_status[b_name] = "OFFLINE"
                    
            for m in ongoing:
                bot_status[m["bot1_name"]] = "IN MATCH"
                bot_status[m["bot2_name"]] = "IN MATCH"
                
            locked_bots = self.state.get("locked_bots", [])
            for lb in locked_bots:
                for b in bots:
                    if b["id"] == lb or b["name"] == lb:
                        bot_status[b["name"]] = "VS PLAYER"
                        break
                
            def update_tree():
                for item in self.bot_tree.get_children():
                    self.bot_tree.delete(item)
                for b_name in sorted(bot_status.keys()):
                    self.bot_tree.insert("", tk.END, values=(b_name, bot_status[b_name]))
            
            self.root.after(0, update_tree)
            
            # --- 2. MATCHMAKING ---
            # Find IDLE, ONLINE bots
            busy_bots = set()
            for m in ongoing:
                busy_bots.add(m["bot1_id"])
                busy_bots.add(m["bot2_id"])
                
            # Note: We must also consider if the real player is playing a bot, but 
            # LeaderboardManager doesn't track live player matches natively.
            # We will use sim_state.json "locked_bots" which the game can write to.
            locked_bots = self.state.get("locked_bots", [])
            for lb in locked_bots:
                for b in bots:
                    if b["id"] == lb or b["name"] == lb:
                        busy_bots.add(b["id"])
            
            cooldowns = self.state.get("bot_cooldowns", {})
            available_bots = []
            for b in bots:
                if b["id"] not in busy_bots and self.is_bot_online(b["id"], curr_time):
                    cd = cooldowns.get(b["id"], {})
                    if curr_time >= cd.get("next_available", 0):
                        available_bots.append({
                            "id": b["id"],
                            "name": b["name"],
                            "points": points_map.get(b["id"], 50),
                            "league": league_map.get(b["id"], "unranked"),
                            "last_opponent": cd.get("last_opponent", None)
                        })
                    
            # Sort by League, then Points
            available_bots.sort(key=lambda x: (x["league"], x["points"]))
            
            # Pair them up greedily (closest points match)
            new_matches_started = 0
            while len(available_bots) >= 2:
                b1 = available_bots.pop(0)
                
                # Try to find a match that isn't their previous opponent
                match_idx = -1
                for i, b2 in enumerate(available_bots):
                    if b1["last_opponent"] != b2["id"] and b2["last_opponent"] != b1["id"]:
                        match_idx = i
                        break
                        
                # Fallback to the closest match if all others were their last opponent
                if match_idx == -1:
                    match_idx = 0
                    
                b2 = available_bots.pop(match_idx)
                
                duration_mins = random.uniform(4.0, 5.0)
                end_time = curr_time + (duration_mins * 60)
                
                ongoing.append({
                    "bot1_id": b1["id"],
                    "bot1_name": b1["name"],
                    "bot2_id": b2["id"],
                    "bot2_name": b2["name"],
                    "end_time": end_time
                })
                
                msg = f"⚔️ [MATCH STARTED] {b1['name']} (Pts: {b1['points']}) vs {b2['name']} (Pts: {b2['points']})"
                self.root.after(0, lambda m=msg: self.log(m, "match"))
                new_matches_started += 1
                
            if new_matches_started > 0:
                self.state["active_matches"] = ongoing
                self.save_state()
                self.root.after(0, lambda: self.stats_lbl.config(text=f"Active Matches: {len(ongoing)}"))
            
            # Sleep 1 second for the event loop
            time.sleep(1.0)

def main():
    root = tk.Tk()
    app = SimulatorApp(root)
    
    def on_closing():
        app.running = False
        root.destroy()
        sys.exit()
        
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()
