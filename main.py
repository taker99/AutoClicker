import customtkinter as ctk
import json
import os
import threading
import time
from pynput import mouse, keyboard
import sys
try:
    import pystray
    from PIL import Image, ImageDraw
except ImportError:
    pystray = None
icon_path = os.path.join(os.path.dirname(__file__), "EGLogo.ico")
SETTINGS_FILE = "settings.json"

class AutoClickerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.language = ctk.StringVar(value="en")
        self.translations = {
            "en": {
                "title": "Speed Auto Clicker by taker",
                "cps": "Clicks per Second:",
                "mouse_button": "Mouse Button:",
                "hotkey": "Hotkey:",
                "change_hotkey": "Change Hotkey",
                "mode": "Mode:",
                "toggle": "Toggle",
                "hold": "Hold",
                "save": "Save",
                "exit": "Exit",
                "ready": "Ready",
                "active": "AutoClicker active",
                "active_hold": "AutoClicker (Hold)",
                "error": "Error",
                "not_allowed": "Not allowed in the selected program!",
                "choose_hotkey": "Choose hotkey...",
                "settings": "Settings",
                "theme": "Theme:",
                "dark_mode": "Dark Mode",
                "minimize_tray": "Minimize to tray on close",
                "failsafe_key": "Failsafe key:",
                "failsafe_hint": "Key that always stops the clicker immediately (e.g. ESC, F12, F10, Q ...)",
                "only_active": "Only active in this application:",
                "select_app": "Select an application where the AutoClicker is allowed to run. 'All applications' = everywhere.",
                "all_apps": "All applications",
                "load_procs": "Loading processes...",
                "tray_open": "Open",
                "tray_exit": "Exit",
                "failsafe_active": "Failsafe active",
                "failsafe_active_s": "Failsafe active ({secs}s)",
                "fehler": "Error",
                "toggle_tooltip": "Toggle: On/Off, Hold: While pressed",
                "mouse_tooltip": "Which mouse button should be clicked?",
                "hotkey_tooltip": "Key/Mouse to start/stop",
                "hotkey_btn_tooltip": "Set new hotkey",
                "language": "Language:",
            },
            "de": {
                "title": "Speed Auto Clicker von taker",
                "cps": "Klicks pro Sekunde:",
                "mouse_button": "Maustaste:",
                "hotkey": "Hotkey:",
                "change_hotkey": "Hotkey ändern",
                "mode": "Modus:",
                "toggle": "Umschalten",
                "hold": "Halten",
                "save": "Speichern",
                "exit": "Beenden",
                "ready": "Bereit",
                "active": "AutoClicker aktiv",
                "active_hold": "AutoClicker (Halten)",
                "error": "Fehler",
                "not_allowed": "Nicht im gewählten Programm!",
                "choose_hotkey": "Hotkey wählen...",
                "settings": "Einstellungen",
                "theme": "Thema:",
                "dark_mode": "Dunkler Modus",
                "minimize_tray": "Beim Schließen ins Tray minimieren",
                "failsafe_key": "Failsafe-Taste:",
                "failsafe_hint": "Taste, die den Clicker sofort stoppt (z.B. ESC, F12, F10, Q ...)",
                "only_active": "Nur in dieser Anwendung aktiv:",
                "select_app": "Wähle eine Anwendung, in der der AutoClicker laufen darf. 'Alle Anwendungen' = überall.",
                "all_apps": "Alle Anwendungen",
                "load_procs": "Lade Prozesse...",
                "tray_open": "Öffnen",
                "tray_exit": "Beenden",
                "failsafe_active": "Failsafe aktiv",
                "failsafe_active_s": "Failsafe aktiv ({secs}s)",
                "fehler": "Fehler",
                "toggle_tooltip": "Umschalten: An/Aus, Halten: Solange gedrückt",
                "mouse_tooltip": "Welche Maustaste soll geklickt werden?",
                "hotkey_tooltip": "Taste/Maus zum Starten/Stoppen",
                "hotkey_btn_tooltip": "Neuen Hotkey setzen",
                "language": "Sprache:",
            }
        }
        self.title(self.t("title"))
        self.geometry("400x700")
        self.resizable(False, False)
        ctk.set_default_color_theme("green")
        self.kps = ctk.IntVar(value=10)
        # Button mapping: 0=left, 1=right, 2=middle
        self.button_map = {0: "left", 1: "right", 2: "middle"}
        self.button_names = {
            "en": ["Left", "Right", "Middle"],
            "de": ["Links", "Rechts", "Mitte"]
        }
        self.button_choice = ctk.IntVar(value=1)  # default: right
        self.button_name_to_idx = {
            "Left": 0, "Right": 1, "Middle": 2,
            "Links": 0, "Rechts": 1, "Mitte": 2
        }
        self.hotkey = ctk.StringVar(value="F6")
        self.mode = ctk.StringVar(value="Hold")
        self.theme_mode = ctk.StringVar(value="Dark")
        self.minimize_to_tray_var = ctk.BooleanVar(value=False)
        self.failsafe_key = ctk.StringVar(value="F9")
        self.clicking = False
        self.listener_thread = None
        self.click_thread = None
        self.pynput_keyboard_listener = None
        self.pynput_mouse_listener = None
        self.controller_hotkey = None
        self.setting_hotkey = False
        self.failsafe_active = False
        self.failsafe_time = 0
        try:
            from PIL import Image, ImageDraw
            self.iconbitmap(icon_path)
        except Exception:
            pass
        self.create_widgets()
        self.load_settings()
        self.after(100, self.start_hotkey_listener)

    def t(self, key):
        lang = self.language.get()
        val = self.translations.get(lang, self.translations["en"]).get(key, key)
        return val if val is not None else str(key)

    def update_language(self, *_):
        self.title(self.t("title"))
        # Update all widgets' text
        for w, key in getattr(self, '_lang_widgets', []):
            w.configure(text=self.t(key))
        # Update tooltips
        for tip, key in getattr(self, '_tooltips', []):
            tip.configure(text=self.t(key))
        # Update mouse button menu
        if hasattr(self, 'mouse_menu'):
            names = self.button_names[self.language.get()]
            self.mouse_menu.configure(values=names)
            idx = self.button_choice.get()
            self.mouse_menu.set(names[idx])
        # Update settings window if open
        if hasattr(self, 'settings_window') and self.settings_window.winfo_exists():
            self.update_settings_language()

    def update_settings_language(self):
        # Update settings window texts
        for w, key in getattr(self, '_settings_lang_widgets', []):
            if isinstance(w, ctk.CTkOptionMenu):
                continue
            else:
                w.configure(text=self.t(key))
        for tip, key in getattr(self, '_settings_tooltips', []):
            tip.configure(text=self.t(key))
        # Update process dropdown menu values and selection
        if hasattr(self, 'process_menu') and hasattr(self, 'selected_process'):
            # Rebuild display names
            process_list = self.get_user_processes()
            process_ids = ["all_apps"]
            for pid, name in process_list:
                process_ids.append(name)
            display_names = [self.t("all_apps") if pid == "all_apps" else pid for pid in process_ids]
            self.process_menu.configure(values=display_names)
            # Update selected value if needed
            current = self.selected_process.get()
            if current == "all_apps" or current in ["All applications", "Alle Anwendungen"]:
                self.selected_process.set(self.t("all_apps"))

    def create_widgets(self):
        self._lang_widgets = []
        self._tooltips = []
        # CPS
        cps_label = ctk.CTkLabel(self, text=self.t("cps"), font=("Arial", 13))
        cps_label.pack(pady=(15, 0))
        self._lang_widgets.append((cps_label, "cps"))
        ctk.CTkSlider(self, from_=1, to=100, variable=self.kps, number_of_steps=99, width=250).pack(pady=5)
        ctk.CTkLabel(self, textvariable=self.kps, font=("Arial", 12, "bold")).pack()
        # Mouse Button
        mouse_label = ctk.CTkLabel(self, text=self.t("mouse_button"), font=("Arial", 13))
        mouse_label.pack(pady=(15, 0))
        self._lang_widgets.append((mouse_label, "mouse_button"))
        def on_mouse_menu_select(choice):
            idx = self.button_name_to_idx.get(choice, 1)
            self.button_choice.set(idx)
            self.save_settings()
        mouse_menu = ctk.CTkOptionMenu(self, variable=ctk.StringVar(value=self.button_names[self.language.get()][self.button_choice.get()]),
                                       values=self.button_names[self.language.get()],
                                       command=on_mouse_menu_select)
        mouse_menu.pack(pady=5)
        self.mouse_menu = mouse_menu
        self.mouse_menu_var = mouse_menu.cget("variable")
        # Hotkey
        hotkey_label = ctk.CTkLabel(self, text=self.t("hotkey"), font=("Arial", 13))
        hotkey_label.pack(pady=(15, 0))
        self._lang_widgets.append((hotkey_label, "hotkey"))
        hotkey_entry = ctk.CTkEntry(self, textvariable=self.hotkey, width=100, state="readonly")
        hotkey_entry.pack(pady=5)
        hotkey_btn = ctk.CTkButton(self, text=self.t("change_hotkey"), command=self.change_hotkey)
        hotkey_btn.pack(pady=5)
        self._lang_widgets.append((hotkey_btn, "change_hotkey"))
        # Mode
        mode_label = ctk.CTkLabel(self, text=self.t("mode"), font=("Arial", 13))
        mode_label.pack(pady=(15, 0))
        self._lang_widgets.append((mode_label, "mode"))
        def on_mode_menu_select(choice):
            self.mode.set(choice)
            self.save_settings()
        mode_menu = ctk.CTkOptionMenu(self, variable=self.mode, values=[self.t("toggle"), self.t("hold")], command=on_mode_menu_select)
        mode_menu.pack(pady=5)
        # Save/Exit
    # Remove save button, autosave will be used
        exit_btn = ctk.CTkButton(self, text=self.t("exit"), command=self.destroy)
        exit_btn.pack(pady=5)
        self._lang_widgets.append((exit_btn, "exit"))
        # Status
        self.status_frame = ctk.CTkFrame(self, fg_color="#4cce84", border_width=2, border_color="#8fe68f")
        self.status_frame.pack(pady=(20, 0), padx=10, fill="x")
        self.status_label = ctk.CTkLabel(self.status_frame, text=self.t("ready"), text_color="#000000", font=("Arial", 13, "bold"))
        self.status_label.pack(pady=(8, 0))
        self._lang_widgets.append((self.status_label, "ready"))
        self.error_label = ctk.CTkLabel(self.status_frame, text="", text_color="#000000", font=("Arial", 11))
        self.error_label.pack(pady=(2, 8))
        # Tooltips
        def add_tooltip(widget, key):
            def get_bg():
                return "#222222" if ctk.get_appearance_mode() == "Dark" else "#f4f4f4"
            tooltip = ctk.CTkLabel(self, text=self.t(key), font=("Arial", 10), text_color="#888", bg_color=get_bg(), wraplength=250, justify="left")
            self._tooltips.append((tooltip, key))
            def show(event):
                tooltip.configure(bg_color=get_bg())
                x = widget.winfo_rootx() - self.winfo_rootx() + 10
                y = widget.winfo_rooty() - self.winfo_rooty() + widget.winfo_height() + 2
                self.update_idletasks()
                tooltip.update_idletasks()
                tw = tooltip.winfo_reqwidth()
                win_w = self.winfo_width()
                if x + tw > win_w:
                    x = max(0, win_w - tw - 10)
                tooltip.place(x=x, y=y)
            def hide(event):
                tooltip.place_forget()
            widget.bind("<Enter>", show)
            widget.bind("<Leave>", hide)
        add_tooltip(mouse_menu, "mouse_tooltip")
        add_tooltip(hotkey_entry, "hotkey_tooltip")
        add_tooltip(hotkey_btn, "hotkey_btn_tooltip")
        add_tooltip(mode_menu, "toggle_tooltip")
        # Settings icon
        try:
            from PIL import Image
            gear_img = Image.open(os.path.join(os.path.dirname(__file__), "gear.png"))
            self.settings_icon_img = ctk.CTkImage(light_image=gear_img, dark_image=gear_img, size=(24, 24))
            self.settings_icon = ctk.CTkButton(self, text="", width=32, height=32, image=self.settings_icon_img, command=self.open_settings, fg_color="transparent")
        except Exception:
            self.settings_icon = ctk.CTkButton(self, text="⚙", width=32, height=32, command=self.open_settings, fg_color="transparent")
        self.settings_icon.place(x=360, y=10)
        # Update language on startup
        self.language.trace_add('write', self.update_language)
        # Removed self.update_language() to prevent recursion

    def open_settings(self):
        if hasattr(self, 'settings_window') and self.settings_window.winfo_exists():
            self.settings_window.lift()
            return
        self.settings_window = ctk.CTkToplevel(self)
        self.settings_window.title(self.t("settings"))
        self.settings_window.resizable(False, False)
        # Position settings window smartly
        try:
            self.update_idletasks()
            main_x = self.winfo_x()
            main_y = self.winfo_y()
            main_w = self.winfo_width()
            main_h = self.winfo_height()
            settings_w = 320
            settings_h = 380
            # Get screen width
            screen_w = self.winfo_screenwidth()
            # Try to open to the right
            right_x = main_x + main_w
            left_x = main_x - settings_w
            # If enough space to the right, open there
            if right_x + settings_w < screen_w:
                pos_x = right_x
            # Else, if enough space to the left, open there
            elif left_x > 0:
                pos_x = left_x
            # Else, overlap main window
            else:
                pos_x = main_x + 40
            pos_y = main_y
            self.settings_window.geometry(f"{settings_w}x{settings_h}+{pos_x}+{pos_y}")
        except Exception:
            self.settings_window.geometry("320x380")
        self._settings_lang_widgets = []
        self._settings_tooltips = []
        lang_label = ctk.CTkLabel(self.settings_window, text=self.t("language"), font=("Arial", 13))
        lang_label.pack(pady=(15, 0))
        self._settings_lang_widgets.append((lang_label, "language"))
        def on_lang_menu_select(choice):
            self.language.set(choice)
            self.save_settings()
        lang_menu = ctk.CTkOptionMenu(self.settings_window, variable=self.language, values=["en", "de"], command=on_lang_menu_select)
        lang_menu.pack(pady=5)
        self._settings_lang_widgets.append((lang_menu, "language"))
        theme_label = ctk.CTkLabel(self.settings_window, text=self.t("theme"), font=("Arial", 13))
        theme_label.pack(pady=(15, 0))
        self._settings_lang_widgets.append((theme_label, "theme"))
        def on_theme_switch():
            self.toggle_theme()
            self.save_settings()
        theme_switch = ctk.CTkSwitch(self.settings_window, text=self.t("dark_mode"), variable=self.theme_mode, onvalue="Dark", offvalue="Light", command=on_theme_switch)
        theme_switch.pack(pady=5)
        self._settings_lang_widgets.append((theme_switch, "dark_mode"))
        def on_tray_check():
            self.save_settings()
        tray_check = ctk.CTkCheckBox(self.settings_window, text=self.t("minimize_tray"), variable=self.minimize_to_tray_var, command=on_tray_check)
        tray_check.pack(anchor="w", pady=(15, 0), padx=20)
        self._settings_lang_widgets.append((tray_check, "minimize_tray"))
        failsafe_label = ctk.CTkLabel(self.settings_window, text=self.t("failsafe_key"))
        failsafe_label.pack(anchor="w", padx=20, pady=(15, 0))
        self._settings_lang_widgets.append((failsafe_label, "failsafe_key"))
        failsafe_entry = ctk.CTkEntry(self.settings_window, textvariable=self.failsafe_key, width=100)
        failsafe_entry.pack(anchor="w", padx=20, pady=(0, 5))
        only_active_label = ctk.CTkLabel(self.settings_window, text=self.t("only_active"))
        only_active_label.pack(anchor="w", padx=20, pady=(15, 0))
        self._settings_lang_widgets.append((only_active_label, "only_active"))

        if not hasattr(self, 'selected_process'):
            self.selected_process = ctk.StringVar(value="all_apps")
        def on_process_menu_select(choice):
            self.selected_process.set(choice)
            self.save_settings()
        self.process_menu = ctk.CTkOptionMenu(self.settings_window, variable=self.selected_process, values=[self.t("load_procs")], command=on_process_menu_select)
        # --- AUTOSAVE BINDINGS ---
        # Main window autosave
        self.kps.trace_add('write', lambda *_: self.save_settings())
        self.button_choice.trace_add('write', lambda *_: self.save_settings())
        self.hotkey.trace_add('write', lambda *_: self.save_settings())
        self.mode.trace_add('write', lambda *_: self.save_settings())
        self.theme_mode.trace_add('write', lambda *_: self.save_settings())
        self.minimize_to_tray_var.trace_add('write', lambda *_: self.save_settings())
        self.failsafe_key.trace_add('write', lambda *_: self.save_settings())
        self.language.trace_add('write', lambda *_: self.save_settings())
        # Settings window autosave
        if hasattr(self, 'selected_process'):
            self.selected_process.trace_add('write', lambda *_: self.save_settings())
        # Settings window widgets autosave
        if 'lang_menu' in locals():
            lang_menu.configure(command=lambda *_: self.save_settings())
        if 'theme_switch' in locals():
            theme_switch.configure(command=lambda *_: (self.toggle_theme(), self.save_settings()))
        if 'tray_check' in locals():
            tray_check.configure(command=lambda *_: self.save_settings())
        if 'failsafe_entry' in locals():
            failsafe_entry.bind('<KeyRelease>', lambda e: self.save_settings())
        if 'only_active_label' in locals() and hasattr(self, 'selected_process'):
            self.selected_process.trace_add('write', lambda *_: self.save_settings())
        self.process_menu.pack(anchor="w", padx=20, pady=(0, 5))
        self.process_menu.configure(state="disabled")
        def fill_process_menu():
            process_list = self.get_user_processes()
            process_ids = ["all_apps"]
            for pid, name in process_list:
                process_ids.append(name)
            # Translate for display
            display_names = [self.t("all_apps") if pid == "all_apps" else pid for pid in process_ids]
            def update_menu():
                self.process_menu.configure(values=display_names, state="normal")
                # Set correct display value
                current = self.selected_process.get()
                if current == "all_apps":
                    self.selected_process.set(self.t("all_apps"))
            self.settings_window.after(0, update_menu)
        import threading
        threading.Thread(target=fill_process_menu, daemon=True).start()
        def add_tooltip_settings(widget, key):
            def get_bg():
                return "#222222" if ctk.get_appearance_mode() == "Dark" else "#f4f4f4"
            tooltip = ctk.CTkLabel(self.settings_window, text=self.t(key), font=("Arial", 10), text_color="#888", bg_color=get_bg(), wraplength=250, justify="left")
            self._settings_tooltips.append((tooltip, key))
            def show(event):
                tooltip.configure(bg_color=get_bg())
                x = widget.winfo_rootx() - self.settings_window.winfo_rootx() + 10
                y = widget.winfo_rooty() - self.settings_window.winfo_rooty() + widget.winfo_height() + 2
                self.settings_window.update_idletasks()
                tooltip.update_idletasks()
                tw = tooltip.winfo_reqwidth()
                win_w = self.settings_window.winfo_width()
                if x + tw > win_w:
                    x = max(0, win_w - tw - 10)
                tooltip.place(x=x, y=y)
            def hide(event):
                tooltip.place_forget()
            widget.bind("<Enter>", show)
            widget.bind("<Leave>", hide)
        add_tooltip_settings(failsafe_entry, "failsafe_hint")
        add_tooltip_settings(self.process_menu, "select_app")
        def on_close():
            self.settings_window.destroy()
        self.settings_window.protocol("WM_DELETE_WINDOW", on_close)

    def save_settings(self):
        x = self.winfo_x()
        y = self.winfo_y()
        selected_process = self.selected_process.get() if hasattr(self, 'selected_process') else "all_apps"
        if selected_process == self.t("all_apps"):
            selected_process = "all_apps"
        # Store button as int (0=left, 1=right, 2=middle)
        data = {
            "kps": self.kps.get(),
            "button": self.button_choice.get(),
            "hotkey": self.hotkey.get(),
            "mode": self.mode.get(),
            "window_x": x,
            "window_y": y,
            "theme": self.theme_mode.get(),
            "minimize_to_tray": bool(self.minimize_to_tray_var.get()),
            "failsafe_key": self.failsafe_key.get(),
            "selected_process": selected_process,
            "language": self.language.get()
        }
        import json
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving settings: {e}")

    def load_settings(self):
        import json
        import os
        defaults = {
            "kps": 10,
            "button": 1,  # right
            "hotkey": "F6",
            "mode": "Hold",
            "window_x": 760,
            "window_y": 197,
            "theme": "Dark",
            "minimize_to_tray": False,
            "failsafe_key": "F9",
            "selected_process": "all_apps",
            "language": "en"
        }
        def recursive_update(d, defaults):
            for k, v in defaults.items():
                if k not in d:
                    d[k] = v
                elif isinstance(v, dict) and isinstance(d[k], dict):
                    recursive_update(d[k], v)
            return d
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                data = recursive_update(data, defaults)
                # Convert old string button values to int
                if isinstance(data["button"], str):
                    data["button"] = self.button_name_to_idx.get(data["button"], 1)
                if data.get("selected_process") not in ["all_apps"]:
                    if data["selected_process"] in [self.t("all_apps"), self.t("load_procs")]:
                        data["selected_process"] = "all_apps"
                self.kps.set(data["kps"])
                self.button_choice.set(data["button"])
                self.hotkey.set(data["hotkey"])
                self.mode.set(data["mode"])
                self.theme_mode.set(data["theme"])
                self.minimize_to_tray_var.set(bool(data["minimize_to_tray"]))
                self.failsafe_key.set(data["failsafe_key"])
                if not hasattr(self, 'selected_process'):
                    self.selected_process = ctk.StringVar()
                if data["selected_process"] == "all_apps":
                    self.selected_process.set(self.t("all_apps"))
                else:
                    self.selected_process.set(data["selected_process"])
                self.language.set(data["language"])
                try:
                    self.geometry(f"400x700+{data['window_x']}+{data['window_y']}")
                except Exception:
                    pass
                self.save_settings()
            except Exception as e:
                print(f"Error loading settings: {e}")
                self.save_settings()
        else:
            self.save_settings()

    def start_hotkey_listener(self):
        if self.pynput_keyboard_listener is None:
            self.pynput_keyboard_listener = keyboard.Listener(on_press=self.on_key_press, on_release=self.on_key_release)
            self.pynput_keyboard_listener.start()
        if self.pynput_mouse_listener is None:
            self.pynput_mouse_listener = mouse.Listener(on_click=self.on_mouse_click)
            self.pynput_mouse_listener.start()

    def on_key_press(self, key):
        try:
            pressed = None
            if hasattr(key, 'char') and key.char:
                pressed = key.char.upper()
            elif hasattr(key, 'name'):
                pressed = key.name.upper()
            elif hasattr(key, 'vk'):
                # F-Tasten
                if 112 <= key.vk <= 135:
                    pressed = f"F{key.vk-111}"
                elif key.vk == 27:
                    pressed = "ESC"
            if pressed and pressed == self.failsafe_key.get().upper():
                self.failsafe_trigger()
                return
            if self.failsafe_active or self.setting_hotkey:
                return
            if pressed and pressed == self.hotkey.get().upper():
                if self.mode.get() == "Hold":
                    self.toggle_clicking()
        except Exception as e:
            self.set_status(f"Key error: {e}", color="red", is_error=True)

    def on_key_release(self, key):
        try:
            if self.failsafe_active or self.setting_hotkey:
                return
            if hasattr(key, 'char') and key.char:
                released = key.char.upper()
            else:
                released = key.name.upper() if hasattr(key, 'name') else str(key).upper()
            if released == self.hotkey.get().upper() and self.mode.get() == "Hold":
                self.clicking = False
                self.set_status("Ready", color="green")
        except Exception as e:
            self.set_status(f"Key error: {e}", color="red", is_error=True)

    def on_mouse_click(self, x, y, button, pressed):
        try:
            if self.failsafe_active or self.setting_hotkey:
                return
            btn_name = button.name.lower() if hasattr(button, 'name') else str(button).lower()
            if pressed and btn_name == self.hotkey.get().lower():
                if self.mode.get() == "Toggle":
                    self.toggle_clicking()
                elif self.mode.get() == "Hold":
                    self.toggle_clicking()
            if not pressed and btn_name == self.hotkey.get().lower() and self.mode.get() == "Hold":
                self.clicking = False
                self.set_status("Ready", color="green")
        except Exception as e:
            self.set_status(f"Mouse error: {e}", color="red", is_error=True)

    def get_foreground_process_name(self):
        try:
            import ctypes
            import psutil
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32
            hwnd = user32.GetForegroundWindow()
            pid = ctypes.c_ulong()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            process = psutil.Process(pid.value)
            return process.name(), pid.value
        except Exception:
            return None, None

    def is_clicker_allowed(self):
        
        fg_name, fg_pid = self.get_foreground_process_name()
        if fg_pid is None:
            return False
        if fg_name is None:
            return False
        own_names = [os.path.basename(sys.executable), "python.exe", "pythonw.exe"]
        if fg_name.lower() in own_names:
            return False
        
        if hasattr(self, 'settings_window') and self.settings_window.winfo_exists():
            try:
                import ctypes
                user32 = ctypes.windll.user32
                hwnd = user32.GetForegroundWindow()
                title = ctypes.create_unicode_buffer(512)
                user32.GetWindowTextW(hwnd, title, 512)
                if "Settings" in title.value:
                    return False
            except Exception:
                pass
        if not hasattr(self, 'selected_process') or self.selected_process.get() == "All applications":
            return True
        sel = self.selected_process.get()
        if sel.startswith("Alle "):
            return True
        fg_name, fg_pid = self.get_foreground_process_name()
        if sel.endswith("(all instances)"):
            name = sel[:-16].strip()
            if fg_name == name:
                return True
        for pid, name in self.get_user_processes():
            if isinstance(pid, list):
                if sel == f"{name} (all instances)" and fg_name == name:
                    return True
            else:
                pname = f"{name} (PID {pid})"
                if sel == pname and fg_name == name and fg_pid == pid:
                    return True
        return False

    def toggle_clicking(self):
        if self.failsafe_active or self.setting_hotkey:
            return
        if not self.is_clicker_allowed():
            self.set_status("Nicht im gewählten Programm!", color="orange", is_error=True)
            return
        try:
            if self.mode.get() == "Toggle":
                if not self.clicking:
                    self.clicking = True
                    self.set_status("AutoClicker active", color="blue")
                    self.click_thread = threading.Thread(target=self.click_loop, daemon=True)
                    self.click_thread.start()
                else:
                    self.clicking = False
                    self.set_status("Ready", color="green")
            elif self.mode.get() == "Hold":
                if not self.clicking:
                    self.clicking = True
                    self.set_status("AutoClicker (Hold)", color="blue")
                    self.click_thread = threading.Thread(target=self.click_loop, daemon=True)
                    self.click_thread.start()
        except Exception as e:
            self.set_status(f"Error starting: {e}", color="red", is_error=True)

    def click_loop(self):
        try:
            btn_idx = self.button_choice.get()
            btn = self.button_map.get(btn_idx, "left")
            btn_map = {'left': mouse.Button.left, 'right': mouse.Button.right, 'middle': mouse.Button.middle}
            m = mouse.Controller()
            while self.clicking:
                if not self.is_clicker_allowed():
                    self.clicking = False
                    self.set_status("Not allowed in the selected program!", color="orange", is_error=True)
                    break
                m.press(btn_map[btn])
                m.release(btn_map[btn])
                time.sleep(1.0 / max(1, self.kps.get()))
            self.set_status("Ready", color="green")
        except Exception as e:
            self.set_status(f"Click error: {e}", color="red", is_error=True)
            self.clicking = False

    def change_hotkey(self):
        self.setting_hotkey = True
        self.hotkey.set('...')
        self.set_status("Choose hotkey...", color="orange")
        self.after(100, self.wait_for_new_hotkey)

    def wait_for_new_hotkey(self):
        self._hotkey_set = False
        def on_press(key):
            if not self._hotkey_set:
                try:
                    if hasattr(key, 'char') and key.char:
                        self.hotkey.set(key.char.upper())
                    else:
                        self.hotkey.set(key.name.upper())
                except Exception:
                    self.hotkey.set(str(key).upper())
                self.save_settings()
                self.setting_hotkey = False
                self.set_status("Ready", color="green")
                self._hotkey_set = True
                listener.stop()
                try:
                    m_listener.stop()
                except Exception:
                    pass
        listener = keyboard.Listener(on_press=on_press)
        listener.start()
        def on_click(x, y, button, pressed):
            if pressed and not self._hotkey_set:
                btn_name = button.name.lower() if hasattr(button, 'name') else str(button).lower()
                self.hotkey.set(btn_name)
                self.save_settings()
                self.setting_hotkey = False
                self.set_status("Ready", color="green")
                self._hotkey_set = True
                m_listener.stop()
                try:
                    listener.stop()
                except Exception:
                    pass
        m_listener = mouse.Listener(on_click=on_click)
        m_listener.start()

    def failsafe_trigger(self):
        self.clicking = False
        self.failsafe_active = True
        self.failsafe_time = time.time() + 10
        self.set_status("Failsafe active", color="red")
        self.after(1000, self.failsafe_cooldown)

    def failsafe_cooldown(self):
        if time.time() < self.failsafe_time:
            self.set_status("Failsafe active", color="red")
            self.after(1000, self.failsafe_cooldown)
        else:
            self.failsafe_active = False
            self.set_status("Ready", color="green")

    def set_status(self, text, color="green", is_error=False):
        if self.failsafe_active:
            text = f"Failsafe activ ({max(0, int(self.failsafe_time - time.time()))}s)"
            color = "red"
        if is_error:
            self.error_label.configure(text=text)
            self.status_label.configure(text="Fehler", text_color="red")
        else:
            self.error_label.configure(text="")
            self.status_label.configure(text=text, text_color=color)

    def toggle_theme(self):
        mode = self.theme_mode.get()
        if mode == "Dark":
            ctk.set_appearance_mode("dark")
        else:
            ctk.set_appearance_mode("light")

    def minimize_to_tray(self):
        if pystray is None:
            self.set_status("pystray/Pillow not installed!", color="red", is_error=True)
            return
        self.withdraw()
        try:
            from PIL import Image, ImageDraw
            tray_icon_img = Image.open(icon_path)
        except Exception:
            from PIL import Image, ImageDraw
            tray_icon_img = Image.new('RGB', (64, 64), color='#1abc1a')
            d = ImageDraw.Draw(tray_icon_img)
            d.ellipse((16, 16, 48, 48), fill='#ffffff')
        menu = pystray.Menu(
            pystray.MenuItem('Open', self.restore_from_tray),
            pystray.MenuItem('Exit', self.exit_from_tray)
        )
        self.tray_icon = pystray.Icon("AutoClicker", tray_icon_img, "AutoClicker", menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def restore_from_tray(self):
        self.deiconify()
        if hasattr(self, 'tray_icon'):
            self.tray_icon.stop()

    def exit_from_tray(self):
        if hasattr(self, 'tray_icon'):
            self.tray_icon.stop()
        self.destroy()

    def protocol_handler(self):
        if self.minimize_to_tray_var.get():
            self.minimize_to_tray()
        else:
            self.destroy()

    def run(self):
        self.protocol("WM_DELETE_WINDOW", self.protocol_handler)
        self.mainloop()

    def get_user_processes(self):
        import psutil
        import ctypes
        user_procs = []
        def has_visible_window(pid):
            try:
                user32 = ctypes.windll.user32
                EnumWindows = user32.EnumWindows
                EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
                IsWindowVisible = user32.IsWindowVisible
                GetWindowThreadProcessId = user32.GetWindowThreadProcessId
                titles = []
                def foreach_window(hwnd, lParam):
                    if IsWindowVisible(hwnd):
                        pid_ = ctypes.c_ulong()
                        GetWindowThreadProcessId(hwnd, ctypes.byref(pid_))
                        if pid_.value == pid:
                            length = user32.GetWindowTextLengthW(hwnd)
                            if length > 0:
                                buff = ctypes.create_unicode_buffer(length + 1)
                                user32.GetWindowTextW(hwnd, buff, length + 1)
                                title = buff.value.strip()
                                if title:
                                    titles.append(title)
                    return True
                EnumWindows(EnumWindowsProc(foreach_window), 0)
                return len(titles) > 0
            except Exception:
                return False
        name_pid_map = {}
        for proc in psutil.process_iter(['pid', 'name', 'username']):
            try:
                if proc.info['username'] and not proc.info['username'].lower().startswith(('nt ', 'system', 'local', 'network')):
                    name = proc.info['name']
                    if name and name.lower() not in ("system", "idle", "services", "svchost.exe", "conhost.exe", "comhost.exe"):
                        if has_visible_window(proc.info['pid']):
                            if name not in name_pid_map:
                                name_pid_map[name] = []
                            name_pid_map[name].append(proc.info['pid'])
            except Exception:
                continue
        result = []
        for name, pids in name_pid_map.items():
            if len(pids) == 1:
                result.append((pids[0], name))
            else:
                result.append((pids, name))
        return sorted(result, key=lambda x: x[1].lower())

if __name__ == "__main__":
    app = AutoClickerApp()
    app.run()
