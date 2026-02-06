import pygame
import sys

from screens.main_menu import show_main_menu
from screens.login_screen import show_login_screen
from screens.profile_screen import show_profile_screen
from screens.collection_screen import show_collection_screen
from screens.deck_screen import show_deck_screen
from screens.gameplay_screen import show_gameplay_screen

# NO REPLAY IMPORTS HERE
from user_manager import UserManager
from card_manager import CardManager


# --- INITIAL SETUP ---
pygame.init()

SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Project TCG")


# --- GLOBAL STATE ---
GAME_STATE = {
    "current_user": "Guest",
    "avatar_surf": None
}


def main():
    current_scene = "MAIN_MENU"
    user_mgr = UserManager()
    card_mgr = CardManager()

    while True:
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

                    if result and isinstance(result, tuple) and result[0] == "UPDATE_USER":
                        new_name = result[1]
                        GAME_STATE["current_user"] = new_name
                        raw = user_mgr.get_avatar_image(new_name)
                        if raw:
                            GAME_STATE["avatar_surf"] = pygame.transform.scale(raw, (130, 130))
                        else:
                            GAME_STATE["avatar_surf"] = None

            elif choice == "COLLECTION":
                show_collection_screen(screen)

            elif choice == "CARD DECKS":
                if GAME_STATE["current_user"] == "Guest":
                    print("Must login to edit decks!")
                else:
                    show_deck_screen(screen, GAME_STATE["current_user"])

            # --- ACHIEVEMENTS PLACEHOLDER ---
            elif choice == "ACHIEVEMENTS":
                print("Achievements feature is currently disabled.")

            elif choice == "PLAY":
                if GAME_STATE["current_user"] == "Guest":
                    print("Must login to play!")
                else:
                    decks = user_mgr.get_user_decks(GAME_STATE["current_user"])
                    if not decks:
                        print("You have no decks! Go create one.")
                    else:
                        first_deck_name = list(decks.keys())[0]
                        deck_ids = decks[first_deck_name]

                        all_cards = card_mgr.get_all_cards()
                        player_deck_data = []
                        for cid in deck_ids:
                            found = next((c for c in all_cards if c["id"] == cid), None)
                            if found:
                                player_deck_data.append(found)

                        if len(player_deck_data) < 3:
                            print(f"Deck '{first_deck_name}' is invalid (Less than 3 cards).")
                        else:
                            show_gameplay_screen(screen, player_deck_data, GAME_STATE["current_user"])

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
