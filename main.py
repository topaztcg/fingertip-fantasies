import pygame
import sys
import subprocess
import atexit
import os


from screens.main_menu import show_main_menu
from screens.login_screen import show_login_screen
from screens.profile_screen import show_profile_screen
from screens.collection_screen import show_collection_screen
from screens.deck_screen import show_deck_screen
from screens.gameplay_screen import show_gameplay_screen
from screens.leaderboard_screen import show_leaderboard_screen
from ui_components import update_animations
from leaderboard_manager import LeaderboardManager

# NO REPLAY IMPORTS HERE
from user_manager import UserManager
from card_manager import CardManager


# --- INITIAL SETUP ---
pygame.init()



screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
pygame.display.set_caption("Fingertip Fantasies")
clock = pygame.time.Clock()


# --- GLOBAL STATE ---
GAME_STATE = {
    "current_user": "Guest",
    "avatar_surf": None
}


def main():
    sim_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "background_simulator.py")
    try:
        sim_proc = subprocess.Popen([sys.executable, sim_path])
        atexit.register(lambda: sim_proc.terminate() if sim_proc.poll() is None else None)
    except Exception as e:
        print("Failed to start simulator:", e)

    current_scene = "MAIN_MENU"
    user_mgr = UserManager()
    card_mgr = CardManager()

    while True:
        dt = clock.tick(60) / 1000.0  # Delta time in seconds
        update_animations(dt)
        
        # --- SCENE CONTROLLER ---
        if current_scene == "MAIN_MENU":
            choice = show_main_menu(screen, GAME_STATE["current_user"], GAME_STATE["avatar_surf"])

            if choice == "QUIT":
                pygame.quit()
                sys.exit()

            elif choice == "LOGIN_ACTION":
                if GAME_STATE["current_user"] == "Guest":
                    current_scene = "LOGIN_SCREEN"
                else:
                    # LOGOUT
                    GAME_STATE["current_user"] = "Guest"
                    GAME_STATE["avatar_surf"] = None
                    print("Logged out.")

            elif choice == "OPEN_PROFILE":
                if GAME_STATE["current_user"] != "Guest":
                    result = show_profile_screen(screen, GAME_STATE["current_user"])

                    if result and isinstance(result, tuple):
                        if result[0] == "UPDATE_USER":
                            new_name = result[1]
                            GAME_STATE["current_user"] = new_name
                            raw = user_mgr.get_avatar_image(new_name)
                            if raw:
                                GAME_STATE["avatar_surf"] = pygame.transform.scale(raw, (130, 130))
                            else:
                                GAME_STATE["avatar_surf"] = None
                        elif result[0] == "OPEN_LEADERBOARD":
                            current_scene = "LEADERBOARD_DIRECT"
                            GAME_STATE["target_league"] = result[1]

            elif choice == "COLLECTION":
                show_collection_screen(screen)

            elif choice == "CARD DECKS":
                if GAME_STATE["current_user"] == "Guest":
                    print("Must login to edit decks!")
                else:
                    show_deck_screen(screen, GAME_STATE["current_user"])

            # --- ACHIEVEMENTS / LEADERBOARD ---
            elif choice == "LEADERBOARD" or current_scene == "LEADERBOARD_DIRECT":
                current_target_league = GAME_STATE.pop("target_league", None)
                if current_scene == "LEADERBOARD_DIRECT":
                    current_scene = "MAIN_MENU" # reset state so we don't get stuck
                
                while True:
                    lb_res = show_leaderboard_screen(screen, GAME_STATE["current_user"], initial_league=current_target_league)
                    if isinstance(lb_res, tuple) and lb_res[0] == "OPEN_PROFILE":
                        target_user = lb_res[1]
                        # We pass the target user. If it's a bot, profile screen handles it gracefully.
                        res = show_profile_screen(screen, target_user)
                        
                        if res and isinstance(res, tuple):
                            if res[0] == "UPDATE_USER":
                                # Only update current_user if the user edited their own profile
                                if target_user == GAME_STATE["current_user"]:
                                    new_name = res[1]
                                    GAME_STATE["current_user"] = new_name
                                    raw = user_mgr.get_avatar_image(new_name)
                                    if raw:
                                        GAME_STATE["avatar_surf"] = pygame.transform.scale(raw, (130, 130))
                                    else:
                                        GAME_STATE["avatar_surf"] = None
                                current_target_league = None # Default reload
                            elif res[0] == "OPEN_LEADERBOARD":
                                current_target_league = res[1]
                        else:
                            # User closed profile via Back button, keep current_target_league unchanged to return to same screen
                            pass
                    else:
                        break # Back button on Leaderboard returns to Main Menu

            elif choice == "PLAY":
                if GAME_STATE["current_user"] == "Guest":
                    print("Must login to play!")
                else:
                    decks = user_mgr.get_user_decks(GAME_STATE["current_user"])
                    active_name = user_mgr.get_active_deck_name(GAME_STATE["current_user"])
                    
                    if not decks:
                        print("You have no decks! Go create one.")
                    elif not active_name or active_name not in decks:
                        print("No active deck selected! Go to Card Decks to equip one.")
                    else:
                        deck_ids = decks[active_name]
                        
                        all_cards = card_mgr.get_all_cards()
                        player_deck_data = []
                        for cid in deck_ids:
                            found = next((c for c in all_cards if c["id"] == cid), None)
                            if found:
                                player_deck_data.append(found)

                        if len(player_deck_data) < 3:
                            print(f"Deck '{active_name}' is invalid (Less than 3 cards).")
                        else:
                            lb_mgr = LeaderboardManager()
                            opp = lb_mgr.find_match(GAME_STATE["current_user"])
                            
                            if opp and opp.get("is_bot"):
                                lb_mgr.lock_bot(opp["name"])
                                
                            show_gameplay_screen(screen, player_deck_data, GAME_STATE["current_user"], opp)
                            
                            if opp and opp.get("is_bot"):
                                lb_mgr.unlock_bot(opp["name"])

        elif current_scene == "LOGIN_SCREEN":
            result, data = show_login_screen(screen)

            if result == "BACK":
                current_scene = "MAIN_MENU"

            elif result == "LOGIN_SUCCESS":
                GAME_STATE["current_user"] = data
                raw_avatar = user_mgr.get_avatar_image(data)
                if raw_avatar:
                    GAME_STATE["avatar_surf"] = pygame.transform.scale(raw_avatar, (130, 130))
                else:
                    GAME_STATE["avatar_surf"] = None
                current_scene = "MAIN_MENU"


if __name__ == "__main__":
    main()
