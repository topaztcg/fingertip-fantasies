import pygame
import sys
import json
import os
from ui_components import Button, InputBox, get_font, PROFILE_BG, BUTTON_BORDER, TEXT_COLOR, BUTTON_BASE, COLOR_ACTIVE

pygame.init()
screen = pygame.display.set_mode((1000, 700))
pygame.display.set_caption("League System Editor")
clock = pygame.time.Clock()

CONFIG_FILE = "leagues_config.json"

def load_data():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except: pass
    return []

def save_data(data):
    # Sort by order before saving
    data.sort(key=lambda x: int(x.get("order", 0)))
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)

leagues = load_data()
selected_idx = -1

# UI State
scroll_y = 0

btn_add = Button("ADD LEAGUE", 50, 600, 200, 50, font_size=20)
btn_save = Button("SAVE CONFIG", 300, 600, 200, 50, font_size=20)
btn_delete = Button("DELETE SELECTED", 750, 600, 200, 50, font_size=20)

inputs = {
    "id": InputBox(600, 150, 350, 40),
    "name": InputBox(600, 250, 350, 40),
    "order": InputBox(600, 350, 350, 40),
    "min_pts": InputBox(600, 450, 150, 40),
    "max_pts": InputBox(800, 450, 150, 40)
}

def load_selected():
    if 0 <= selected_idx < len(leagues):
        lg = leagues[selected_idx]
        inputs["id"].text = str(lg.get("id", ""))
        inputs["name"].text = str(lg.get("name", ""))
        inputs["order"].text = str(lg.get("order", ""))
        inputs["min_pts"].text = str(lg.get("min_pts", ""))
        inputs["max_pts"].text = str(lg.get("max_pts", ""))
        for i in inputs.values():
            i.txt_surface = i.font.render(i.text, True, i.color)

def apply_selected():
    if 0 <= selected_idx < len(leagues):
        lg = leagues[selected_idx]
        lg["id"] = inputs["id"].get_text()
        lg["name"] = inputs["name"].get_text()
        try: lg["order"] = int(inputs["order"].get_text())
        except: lg["order"] = 99
        try: lg["min_pts"] = int(inputs["min_pts"].get_text())
        except: lg["min_pts"] = 0
        try: lg["max_pts"] = int(inputs["max_pts"].get_text())
        except: lg["max_pts"] = 9999

while True:
    events = pygame.event.get()
    mouse_pos = pygame.mouse.get_pos()
    
    for event in events:
        if event.type == pygame.QUIT:
            sys.exit()
            
        for i in inputs.values():
            i.handle_event(event)
            
        if event.type == pygame.KEYDOWN:
            # Apply edits instantly
            apply_selected()
            
        if event.type == pygame.MOUSEWHEEL:
            scroll_y = max(0, scroll_y - event.y * 20)
            
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if btn_add.check_input(mouse_pos):
                leagues.append({"id": "new_league", "name": "New League", "order": len(leagues)+1, "min_pts": 0, "max_pts": 100})
                selected_idx = len(leagues) - 1
                load_selected()
                
            if btn_save.check_input(mouse_pos):
                apply_selected()
                save_data(leagues)
                print("Saved!")
                
            if btn_delete.check_input(mouse_pos):
                if 0 <= selected_idx < len(leagues):
                    leagues.pop(selected_idx)
                    selected_idx = -1
                    for i in inputs.values():
                        i.text = ""; i.txt_surface = i.font.render("", True, i.color)
                        
            # List selection
            list_rect = pygame.Rect(50, 100, 400, 450)
            if list_rect.collidepoint(mouse_pos):
                rel_y = mouse_pos[1] - list_rect.y + scroll_y
                idx = int(rel_y // 60)
                if 0 <= idx < len(leagues):
                    apply_selected() # Save old
                    selected_idx = idx
                    load_selected() # Load new
    
    screen.fill((20, 15, 20))
    
    # Title
    screen.blit(get_font(40).render("LEAGUE CONFIG EDITOR", True, TEXT_COLOR), (50, 30))
    
    # Draw List
    list_rect = pygame.Rect(50, 100, 400, 450)
    pygame.draw.rect(screen, PROFILE_BG, list_rect, border_radius=10)
    pygame.draw.rect(screen, BUTTON_BORDER, list_rect, 2, border_radius=10)
    
    screen.set_clip(list_rect)
    dy = list_rect.y - scroll_y
    for i, lg in enumerate(leagues):
        r = pygame.Rect(list_rect.x, dy, list_rect.width, 60)
        col = (60, 40, 60) if i == selected_idx else PROFILE_BG
        pygame.draw.rect(screen, col, r)
        pygame.draw.rect(screen, BUTTON_BORDER, r, 1)
        
        name = get_font(25).render(f"{lg.get('order', 0)}. {lg.get('name', 'Unknown')}", True, TEXT_COLOR)
        screen.blit(name, (r.x + 20, r.y + 15))
        
        pts = get_font(18).render(f"{lg.get('min_pts', 0)} - {lg.get('max_pts', 0)} pts", True, (200, 150, 200))
        screen.blit(pts, (r.right - 150, r.y + 20))
        
        dy += 60
    screen.set_clip(None)
    
    # Draw Editor
    if 0 <= selected_idx < len(leagues):
        screen.blit(get_font(25).render("League ID:", True, (200, 200, 200)), (600, 110))
        inputs["id"].update(); inputs["id"].draw(screen)
        
        screen.blit(get_font(25).render("Display Name:", True, (200, 200, 200)), (600, 210))
        inputs["name"].update(); inputs["name"].draw(screen)
        
        screen.blit(get_font(25).render("Progression Order:", True, (200, 200, 200)), (600, 310))
        inputs["order"].update(); inputs["order"].draw(screen)
        
        screen.blit(get_font(25).render("Min Pts:", True, (200, 200, 200)), (600, 410))
        inputs["min_pts"].update(); inputs["min_pts"].draw(screen)
        
        screen.blit(get_font(25).render("Max Pts:", True, (200, 200, 200)), (800, 410))
        inputs["max_pts"].update(); inputs["max_pts"].draw(screen)
    else:
        empty = get_font(30).render("Select a league to edit", True, (100, 100, 100))
        screen.blit(empty, (650, 300))
        
    btn_add.change_color(mouse_pos); btn_add.update(screen)
    btn_save.change_color(mouse_pos); btn_save.update(screen)
    btn_delete.change_color(mouse_pos); btn_delete.update(screen)
    
    pygame.display.update()
    clock.tick(60)
