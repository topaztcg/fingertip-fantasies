import flet as ft
import json
import os

# --- CONSTANTS ---
CARDS_DB_FILE = "cards_data.json"
DIALOGUE_DB_FILE = "card_dialogues.json"
BUFFS_FILE = "assets/buffs.json"

TRIGGERS = [
    "MATCH_START",
    "ROUND_START",
    "ATK_USED",
    "SKILL_USED",
    "ULT_USED",
    "ATK_BUFFED",
    "HEALED",
    "SHIELD_GAINED",
    "SHIELD_DAMAGED",
    "SHIELD_DESTROYED",
    "HEAVY_HIT_TAKEN",
    "HEAVY_HIT_DEALT",
    "ENERGY_FULL",
    "ENERGY_ALMOST",
    "KILL",
    "DEATH",
    "LOW_HP_ROUND_END",
    "MATCH_WON_3",
    "MATCH_WON_2",
    "MATCH_WON_1",
    "MATCH_LOST"
]

# Triggers that require a threshold value
THRESHOLD_TRIGGERS = [
    "ATK_BUFFED",
    "HEALED",
    "HEAVY_HIT_TAKEN",
    "HEAVY_HIT_DEALT",
    "LOW_HP_ROUND_END"
]

# Action Triggers that need Timing (Pre/Post Cast)
ACTION_TRIGGERS = [
    "ATK_USED",
    "SKILL_USED",
    "ULT_USED"
]

def load_json(path):
    if not os.path.exists(path): return {}
    try:
        with open(path, "r") as f:
            return json.load(f)
    except:
        return {}

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=4)

def main(page: ft.Page):
    page.title = "Fingertip Fantasies - Dialogue Editor"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 20
    page.window_width = 1000
    page.window_height = 800

    # --- DATA LOADING ---
    cards_data = load_json(CARDS_DB_FILE) # List of dicts
    if isinstance(cards_data, dict): cards_data = [] # Handle error case
    
    dialogues_data = load_json(DIALOGUE_DB_FILE)
    buffs_data = load_json(BUFFS_FILE)

    # Helper: Get Buff Types
    buff_types = sorted(list(set(b.get("type", "UNKNOWN") for b in buffs_data)))
    
    # Generate Dynamic Triggers for Buffs
    dynamic_triggers = list(TRIGGERS)
    for bt in buff_types:
        dynamic_triggers.append(f"BUFF_USED_{bt}")
    
    current_card_id = None
    current_trigger = dynamic_triggers[0]

    # --- UI ELEMENTS ---
    
    # 1. Card Selector
    def on_card_change(e):
        nonlocal current_card_id
        current_card_id = card_dropdown.value
        refresh_editor()

    card_options = [ft.dropdown.Option(c["id"], f"{c['name']} ({c['id']})") for c in cards_data]
    card_dropdown = ft.Dropdown(
        label="Select Card",
        options=card_options,
        width=400
    )
    card_dropdown.on_change = on_card_change

    # 2. Trigger Selector (Sidebar)
    def on_trigger_select(e):
        nonlocal current_trigger
        current_trigger = e.control.data
        # Update UI highlight
        for ctrl in trigger_list_col.controls:
            ctrl.bgcolor = "transparent" if ctrl.data != current_trigger else "primaryContainer"
        trigger_list_col.update()
        refresh_editor()

    trigger_list_col = ft.Column(scroll=ft.ScrollMode.AUTO, height=650)
    for t in dynamic_triggers:
        btn = ft.Container(
            content=ft.Text(t, size=12),
            padding=10,
            border_radius=5,
            data=t,
            on_click=on_trigger_select,
            bgcolor="transparent"
        )
        trigger_list_col.controls.append(btn)

    # 3. Editor Area
    lines_container = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)

    def add_line(e):
        if not current_card_id: return
        
        # Structure for new line
        new_entry = {"text": ""}
        
        # Add extra fields if needed
        if current_trigger in THRESHOLD_TRIGGERS:
            new_entry["threshold"] = 0
        
        if current_trigger in ACTION_TRIGGERS:
            new_entry["timing"] = "PRE" # Default to PRE-cast

        # Init card in DB if missing
        if current_card_id not in dialogues_data:
            dialogues_data[current_card_id] = {}
        if current_trigger not in dialogues_data[current_card_id]:
            dialogues_data[current_card_id][current_trigger] = []
        
        dialogues_data[current_card_id][current_trigger].append(new_entry)
        save_json(DIALOGUE_DB_FILE, dialogues_data)
        refresh_editor()

    def update_entry(entry, field, value):
        entry[field] = value
        save_json(DIALOGUE_DB_FILE, dialogues_data)

    def delete_entry(entry):
        dialogues_data[current_card_id][current_trigger].remove(entry)
        save_json(DIALOGUE_DB_FILE, dialogues_data)
        refresh_editor()

    def refresh_editor():
        lines_container.controls.clear()
        
        if not current_card_id:
            lines_container.controls.append(ft.Text("Please select a card first.", color="grey"))
            page.update()
            return

        # Get existing lines
        entries = dialogues_data.get(current_card_id, {}).get(current_trigger, [])
        
        # Header
        header_text = f"Editing: {current_trigger}"
        if current_trigger in THRESHOLD_TRIGGERS: header_text += " (Supports Threshold)"
        if current_trigger in ACTION_TRIGGERS: header_text += " (Supports Timing)"
        
        lines_container.controls.append(ft.Text(header_text, size=20, weight=ft.FontWeight.BOLD))
        lines_container.controls.append(ft.Divider())

        for entry in entries:
            # Handle string vs dict (migration support)
            if isinstance(entry, str):
                # Auto-convert old string format to dict
                idx = entries.index(entry)
                entries[idx] = {"text": entry}
                entry = entries[idx]

            row_controls = []
            
            # TEXT INPUT
            txt = ft.TextField(
                value=entry.get("text", ""), 
                label="Dialogue Text", 
                expand=True,
                multiline=True,
                on_change=lambda e, ent=entry: update_entry(ent, "text", e.control.value)
            )
            row_controls.append(txt)

            # THRESHOLD INPUT
            if current_trigger in THRESHOLD_TRIGGERS:
                thresh = ft.TextField(
                    value=str(entry.get("threshold", 0)),
                    label="Threshold",
                    width=100,
                    keyboard_type=ft.KeyboardType.NUMBER,
                    on_change=lambda e, ent=entry: update_entry(ent, "threshold", int(e.control.value) if e.control.value.isdigit() else 0)
                )
                row_controls.append(thresh)

            # TIMING INPUT
            if current_trigger in ACTION_TRIGGERS:
                timing = ft.Dropdown(
                    value=entry.get("timing", "PRE"),
                    label="Timing",
                    width=120,
                    options=[ft.dropdown.Option("PRE", "Before Video"), ft.dropdown.Option("POST", "After Video")]
                )
                timing.on_change = lambda e, ent=entry: update_entry(ent, "timing", e.control.value)
                row_controls.append(timing)

            # DELETE BUTTON
            del_btn = ft.IconButton(
                icon=ft.Icons.DELETE,
                icon_color="red400",
                on_click=lambda e, ent=entry: delete_entry(ent)
            )
            row_controls.append(del_btn)

            card_panel = ft.Container(
                content=ft.Row(controls=row_controls, alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.START),
                padding=10,
                border=ft.Border.all(1, "outline"),
                border_radius=10,
                bgcolor="surfaceVariant"
            )
            lines_container.controls.append(card_panel)

        # Add "Add Line" button at bottom
        add_btn = ft.ElevatedButton("Add New Line", on_click=add_line, icon=ft.Icons.ADD)
        lines_container.controls.append(ft.Container(height=20))
        lines_container.controls.append(add_btn)
        
        page.update()

    # --- LAYOUT ---
    layout = ft.Row(
        expand=True,
        controls=[
            # Sidebar
            ft.Container(
                width=250,
                bgcolor="surface",
                padding=10,
                border_radius=10,
                content=ft.Column(
                    controls=[
                        ft.Text("Triggers", size=16, weight=ft.FontWeight.BOLD),
                        ft.Divider(),
                        trigger_list_col
                    ]
                )
            ),
            # Main Content
            ft.Container(
                expand=True,
                padding=20,
                content=ft.Column(
                    controls=[
                        card_dropdown,
                        ft.Divider(),
                        lines_container
                    ]
                )
            )
        ]
    )

    page.add(layout)
    
    # Init Editor State
    if cards_data:
        card_dropdown.value = cards_data[0]["id"]
        current_card_id = cards_data[0]["id"]
        refresh_editor()

ft.run(main)
