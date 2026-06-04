import pygame
import sys
import json
import os
from ui_components import Button, InputBox, get_font, PROFILE_BG, BUTTON_BORDER, TEXT_COLOR, BUTTON_BASE, COLOR_ACTIVE

pygame.init()
screen = pygame.display.set_mode((1000, 700))
pygame.display.set_caption("Fake Player Config Editor")
clock = pygame.time.Clock()

CONFIG_FILE = "fake_players_config.json"

def load_data():
    default_data = {"simulation_enabled": True, "bots": []}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                d = json.load(f)
                return {
                    "simulation_enabled": d.get("simulation_enabled", True),
                    "bots": d.get("bots", [])
                }
        except: pass
    return default_data

def save_data(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)

app_data = load_data()
bots = app_data["bots"]
selected_idx = -1
scroll_y = 0

btn_add = Button("ADD BOT", 50, 600, 200, 50, font_size=20)
btn_save = Button("SAVE CONFIG", 300, 600, 200, 50, font_size=20)
btn_delete = Button("DELETE SELECTED", 750, 600, 200, 50, font_size=20)
btn_toggle_sim = Button("SIMULATION: ON", 700, 40, 250, 50, font_size=20)

inputs = {
    "id": InputBox(600, 200, 350, 40),
    "name": InputBox(600, 300, 350, 40),
    "pfp_path": InputBox(600, 400, 350, 40)
}

def update_sim_btn():
    btn_toggle_sim.set_text("SIMULATION: ON" if app_data["simulation_enabled"] else "SIMULATION: OFF")

update_sim_btn()

def load_selected():
    if 0 <= selected_idx < len(bots):
        b = bots[selected_idx]
        inputs["id"].text = str(b.get("id", ""))
        inputs["name"].text = str(b.get("name", ""))
        inputs["pfp_path"].text = str(b.get("pfp_path", ""))
        for i in inputs.values():
            i.txt_surface = i.font.render(i.text, True, i.color)

def apply_selected():
    if 0 <= selected_idx < len(bots):
        b = bots[selected_idx]
        b["id"] = inputs["id"].get_text()
        b["name"] = inputs["name"].get_text()
        b["pfp_path"] = inputs["pfp_path"].get_text()

while True:
    events = pygame.event.get()
    mouse_pos = pygame.mouse.get_pos()
    
    for event in events:
        if event.type == pygame.QUIT:
            sys.exit()
            
        for i in inputs.values():
            i.handle_event(event)
            
        if event.type == pygame.KEYDOWN:
            apply_selected()
            
        if event.type == pygame.MOUSEWHEEL:
            scroll_y = max(0, scroll_y - event.y * 20)
            
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if btn_toggle_sim.check_input(mouse_pos):
                app_data["simulation_enabled"] = not app_data["simulation_enabled"]
                update_sim_btn()
                
            if btn_add.check_input(mouse_pos):
                bots.append({"id": f"bot_{len(bots)}", "name": "New Bot", "pfp_path": ""})
                selected_idx = len(bots) - 1
                load_selected()
                
            if btn_save.check_input(mouse_pos):
                apply_selected()
                save_data(app_data)
                print("Saved!")
                
            if btn_delete.check_input(mouse_pos):
                if 0 <= selected_idx < len(bots):
                    bots.pop(selected_idx)
                    selected_idx = -1
                    for i in inputs.values():
                        i.text = ""; i.txt_surface = i.font.render("", True, i.color)
                        
            list_rect = pygame.Rect(50, 100, 400, 450)
            if list_rect.collidepoint(mouse_pos):
                rel_y = mouse_pos[1] - list_rect.y + scroll_y
                idx = int(rel_y // 60)
                if 0 <= idx < len(bots):
                    apply_selected()
                    selected_idx = idx
                    load_selected()
    
    screen.fill((20, 15, 20))
    screen.blit(get_font(40).render("FAKE PLAYER EDITOR", True, TEXT_COLOR), (50, 30))
    
    list_rect = pygame.Rect(50, 100, 400, 450)
    pygame.draw.rect(screen, PROFILE_BG, list_rect, border_radius=10)
    pygame.draw.rect(screen, BUTTON_BORDER, list_rect, 2, border_radius=10)
    
    screen.set_clip(list_rect)
    dy = list_rect.y - scroll_y
    for i, b in enumerate(bots):
        r = pygame.Rect(list_rect.x, dy, list_rect.width, 60)
        col = (60, 40, 60) if i == selected_idx else PROFILE_BG
        pygame.draw.rect(screen, col, r)
        pygame.draw.rect(screen, BUTTON_BORDER, r, 1)
        
        name = get_font(25).render(b.get("name", "Unknown"), True, TEXT_COLOR)
        screen.blit(name, (r.x + 20, r.y + 15))
        
        dy += 60
    screen.set_clip(None)
    
    if 0 <= selected_idx < len(bots):
        screen.blit(get_font(25).render("Bot ID:", True, (200, 200, 200)), (600, 160))
        inputs["id"].update(); inputs["id"].draw(screen)
        
        screen.blit(get_font(25).render("Display Name:", True, (200, 200, 200)), (600, 260))
        inputs["name"].update(); inputs["name"].draw(screen)
        
        screen.blit(get_font(25).render("PFP Path:", True, (200, 200, 200)), (600, 360))
        inputs["pfp_path"].update(); inputs["pfp_path"].draw(screen)
    else:
        empty = get_font(30).render("Select a bot to edit", True, (100, 100, 100))
        screen.blit(empty, (650, 300))
        
    btn_add.change_color(mouse_pos); btn_add.update(screen)
    btn_save.change_color(mouse_pos); btn_save.update(screen)
    btn_delete.change_color(mouse_pos); btn_delete.update(screen)
    btn_toggle_sim.change_color(mouse_pos); btn_toggle_sim.update(screen)
    
    pygame.display.update()
    clock.tick(60)
