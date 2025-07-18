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
        self.title("Speed Auto Clicker by taker")
        self.geometry("400x700")
        self.resizable(False, False)
    
        ctk.set_default_color_theme("green")
        self.kps = ctk.IntVar(value=10)
        self.button_choice = ctk.StringVar(value="right")  # Standard: Rechtsklick
        self.hotkey = ctk.StringVar(value="F6")
        self.mode = ctk.StringVar(value="Hold")  # Standard: Halten

        # Initialisiere Hilfsvariablen für Map und Theme-Mode
        self.button_map = {"Links": "left", "Rechts": "right", "Mitte": "middle"}
        self.theme_mode = ctk.StringVar(value="Dark")

        # Erweiterte Einstellungen als Attribute (für Settings-Dialog und Save/Load)
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

        # Icon für das Tray-Menü (immer verfügbar)
        try:
            from PIL import Image, ImageDraw
            self.iconbitmap(icon_path)
        except Exception:
            pass

        self.create_widgets()
        self.load_settings()
        self.after(100, self.start_hotkey_listener)
        #self.init_pygame_joystick()

    def create_widgets(self):
        # Gruppierung: Klickrate
        ctk.CTkLabel(self, text="Klicks pro Sekunde:", font=("Arial", 13)).pack(pady=(15, 0))
        ctk.CTkSlider(self, from_=1, to=100, variable=self.kps, number_of_steps=99, width=250).pack(pady=5)
        ctk.CTkLabel(self, textvariable=self.kps, font=("Arial", 12, "bold")).pack()

        # Maustaste & Hotkey
        ctk.CTkLabel(self, text="Maustaste:", font=("Arial", 13)).pack(pady=(15, 0))
        mouse_menu = ctk.CTkOptionMenu(self, variable=self.button_choice, values=list(self.button_map.keys()))
        mouse_menu.pack(pady=5)
        # Tooltip für Maustaste

        ctk.CTkLabel(self, text="Hotkey:", font=("Arial", 13)).pack(pady=(15, 0))
        hotkey_entry = ctk.CTkEntry(self, textvariable=self.hotkey, width=100, state="readonly")
        hotkey_entry.pack(pady=5)
        hotkey_btn = ctk.CTkButton(self, text="Hotkey ändern", command=self.change_hotkey)
        hotkey_btn.pack(pady=5)
        # Tooltip für Hotkey

        # Modus
        ctk.CTkLabel(self, text="Modus:", font=("Arial", 13)).pack(pady=(15, 0))
        mode_menu = ctk.CTkOptionMenu(self, variable=self.mode, values=["Toggle", "Hold"])
        mode_menu.pack(pady=5)
        # Tooltip für Modus

        # Aktionen
        ctk.CTkButton(self, text="Speichern", command=self.save_settings).pack(pady=(20, 0))
        ctk.CTkButton(self, text="Beenden", command=self.destroy).pack(pady=5)

        # Statusbereich
        self.status_frame = ctk.CTkFrame(self, fg_color="#4cce84", border_width=2, border_color="#8fe68f")
        self.status_frame.pack(pady=(20, 0), padx=10, fill="x")
        self.status_label = ctk.CTkLabel(self.status_frame, text="Bereit", text_color="#000000", font=("Arial", 13, "bold"))
        self.status_label.pack(pady=(8, 0))
        self.error_label = ctk.CTkLabel(self.status_frame, text="", text_color="#000000", font=("Arial", 11))
        self.error_label.pack(pady=(2, 8))

        # Tooltips als schwebende Labels (ohne Attributbindung)
        def add_tooltip(widget, text):
            def get_bg():
                return "#222222" if ctk.get_appearance_mode() == "Dark" else "#f4f4f4"
            tooltip = ctk.CTkLabel(self, text=text, font=("Arial", 10), text_color="#888", bg_color=get_bg(), wraplength=250, justify="left")
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

        add_tooltip(mouse_menu, "Welche Maustaste soll geklickt werden?")
        add_tooltip(hotkey_entry, "Taste/Maus/Controller zum Starten/Stoppen")
        add_tooltip(hotkey_btn, "Neuen Hotkey festlegen")
        add_tooltip(mode_menu, "Toggle: Ein/Aus, Hold: Nur solange gedrückt")

        # Zahnrad-Icon für Settings-Menü (gear.png, immer sichtbar oben rechts)
        try:
            from PIL import Image
            gear_img = Image.open(os.path.join(os.path.dirname(__file__), "gear.png"))
            self.settings_icon_img = ctk.CTkImage(light_image=gear_img, dark_image=gear_img, size=(24, 24))
            self.settings_icon = ctk.CTkButton(self, text="", width=32, height=32, image=self.settings_icon_img, command=self.open_settings, fg_color="transparent")
        except Exception:
            self.settings_icon = ctk.CTkButton(self, text="⚙", width=32, height=32, command=self.open_settings, fg_color="transparent")
        self.settings_icon.place(x=360, y=10)

    def open_settings(self):
        if hasattr(self, 'settings_window') and self.settings_window.winfo_exists():
            self.settings_window.lift()
            return
        self.settings_window = ctk.CTkToplevel(self)
        self.settings_window.title("Einstellungen")
        self.settings_window.geometry("320x340")
        self.settings_window.resizable(False, False)
        self._settings_tooltips = []
        # Theme
        ctk.CTkLabel(self.settings_window, text="Theme:", font=("Arial", 13)).pack(pady=(15, 0))
        ctk.CTkSwitch(self.settings_window, text="Dark Mode", variable=self.theme_mode, onvalue="Dark", offvalue="Light", command=self.toggle_theme).pack(pady=5)
        # Tray
        ctk.CTkCheckBox(self.settings_window, text="Beim Schließen ins Tray minimieren", variable=self.minimize_to_tray_var).pack(anchor="w", pady=(15, 0), padx=20)
        # Failsafe
        ctk.CTkLabel(self.settings_window, text="Failsafe-Taste:").pack(anchor="w", padx=20, pady=(15, 0))
        failsafe_entry = ctk.CTkEntry(self.settings_window, textvariable=self.failsafe_key, width=100)
        failsafe_entry.pack(anchor="w", padx=20, pady=(0, 5))
        # Prozessauswahl (asynchron laden)
        ctk.CTkLabel(self.settings_window, text="Nur aktiv in Anwendung:").pack(anchor="w", padx=20, pady=(15, 0))
        if not hasattr(self, 'selected_process'):
            self.selected_process = ctk.StringVar(value="Alle Anwendungen")
        self.process_menu = ctk.CTkOptionMenu(self.settings_window, variable=self.selected_process, values=["Lade Prozesse..."])
        self.process_menu.pack(anchor="w", padx=20, pady=(0, 5))
        self.process_menu.configure(state="disabled")
        def fill_process_menu():
            process_list = self.get_user_processes()
            process_names = []
            for pid, name in process_list:
                if isinstance(pid, list):
                    process_names.append(f"{name} (alle Instanzen)")
                else:
                    process_names.append(f"{name} (PID {pid})")
            process_names.insert(0, "Alle Anwendungen")
            def update_menu():
                self.process_menu.configure(values=process_names, state="normal")
                # Auswahl wiederherstellen, falls vorhanden
                if hasattr(self, 'selected_process') and self.selected_process.get() in process_names:
                    self.process_menu.set(self.selected_process.get())
                else:
                    self.process_menu.set("Alle Anwendungen")
            self.settings_window.after(0, update_menu)
        import threading
        threading.Thread(target=fill_process_menu, daemon=True).start()
        # Tooltip für Prozessauswahl
        def add_tooltip_settings(widget, text):
            def get_bg():
                return "#222222" if ctk.get_appearance_mode() == "Dark" else "#f4f4f4"
            tooltip = ctk.CTkLabel(self.settings_window, text=text, font=("Arial", 10), text_color="#888", bg_color=get_bg(), wraplength=250, justify="left")
            self._settings_tooltips.append(tooltip)
            def show(event):
                tooltip.configure(bg_color=get_bg())
                x = widget.winfo_rootx() - self.settings_window.winfo_rootx() + 10
                y = widget.winfo_rooty() - self.settings_window.winfo_rooty() + widget.winfo_height() + 2
                # Prüfen, ob Tooltip rechts rausgeht
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
        add_tooltip_settings(failsafe_entry, "Taste, die den Clicker IMMER sofort stoppt (z.B. ESC, F12, F10, Q ...)")
        add_tooltip_settings(self.process_menu, "Wähle eine Anwendung, in der der AutoClicker aktiv sein darf. 'Alle Anwendungen' = überall.")
        def on_close():
            for t in getattr(self, '_settings_tooltips', []):
                t.place_forget()
                t.destroy()
            self.settings_window.destroy()
        self.settings_window.protocol("WM_DELETE_WINDOW", on_close)

    def save_settings(self):
        # Fensterposition und Theme speichern
        x = self.winfo_x()
        y = self.winfo_y()
        data = {
            "kps": self.kps.get(),
            "button": self.button_choice.get(),
            "hotkey": self.hotkey.get(),
            "mode": self.mode.get(),
            "window_x": x,
            "window_y": y,
            "theme": self.theme_mode.get(),
            "minimize_to_tray": self.minimize_to_tray_var.get(),
            "failsafe_key": self.failsafe_key.get(),
            "selected_process": self.selected_process.get() if hasattr(self, 'selected_process') else "Alle Anwendungen"
        }
        with open(SETTINGS_FILE, "w") as f:
            json.dump(data, f)

    def load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r") as f:
                data = json.load(f)
                self.kps.set(data.get("kps", 10))
                btn = data.get("button", "Links")
                if btn in self.button_map:
                    self.button_choice.set(btn)
                elif btn in self.button_map.values():
                    for k, v in self.button_map.items():
                        if v == btn:
                            self.button_choice.set(k)
                            break
                else:
                    self.button_choice.set("Links")
                self.hotkey.set(data.get("hotkey", "F6"))
                self.mode.set(data.get("mode", "Toggle"))
                # Fensterposition wiederherstellen
                x = data.get("window_x")
                y = data.get("window_y")
                if x is not None and y is not None:
                    self.geometry(f"+{x}+{y}")
                # Theme wiederherstellen
                theme = data.get("theme")
                if theme in ("Dark", "Light"):
                    self.theme_mode.set(theme)
                    self.toggle_theme()
                # Erweiterte Einstellungen
                self.minimize_to_tray_var.set(data.get("minimize_to_tray", False))
                self.failsafe_key.set(data.get("failsafe_key", "ESC"))
                # Prozessauswahl
                if hasattr(self, 'selected_process'):
                    self.selected_process.set(data.get("selected_process", "Alle Anwendungen"))

    def start_hotkey_listener(self):
        # Start keyboard listener
        if self.pynput_keyboard_listener is None:
            self.pynput_keyboard_listener = keyboard.Listener(on_press=self.on_key_press, on_release=self.on_key_release)
            self.pynput_keyboard_listener.start()
        # Start mouse listener
        if self.pynput_mouse_listener is None:
            self.pynput_mouse_listener = mouse.Listener(on_click=self.on_mouse_click)
            self.pynput_mouse_listener.start()

    def on_key_press(self, key):
        try:
            # Konfigurierbare Failsafe-Taste
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
            self.set_status(f"Key-Fehler: {e}", color="red", is_error=True)

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
                self.set_status("Bereit", color="green")
        except Exception as e:
            self.set_status(f"Key-Fehler: {e}", color="red", is_error=True)

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
                self.set_status("Bereit", color="green")
        except Exception as e:
            self.set_status(f"Maus-Fehler: {e}", color="red", is_error=True)

    def get_foreground_process_name(self):
        # Windows: aktives Fenster und Prozessname ermitteln
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
        # Prüft, ob der Clicker im aktuellen Prozess aktiv sein darf
        fg_name, fg_pid = self.get_foreground_process_name()
        # Eigene Fenster blockieren
        if fg_name is None:
            return False
        own_names = [os.path.basename(sys.executable), "python.exe", "pythonw.exe"]
        if fg_name.lower() in own_names:
            return False
        # Settings-Fenster blockieren (Fenstertitel prüfen)
        if hasattr(self, 'settings_window') and self.settings_window.winfo_exists():
            try:
                import ctypes
                user32 = ctypes.windll.user32
                hwnd = user32.GetForegroundWindow()
                title = ctypes.create_unicode_buffer(512)
                user32.GetWindowTextW(hwnd, title, 512)
                if "Einstellungen" in title.value:
                    return False
            except Exception:
                pass
        # Auswahl "Alle Anwendungen" = immer erlaubt
        if not hasattr(self, 'selected_process') or self.selected_process.get() == "Alle Anwendungen":
            return True
        sel = self.selected_process.get()
        if sel.startswith("Alle "):
            return True
        fg_name, fg_pid = self.get_foreground_process_name()
        # Gruppen-Check: "Name (alle Instanzen)"
        if sel.endswith("(alle Instanzen)"):
            name = sel[:-16].strip()
            if fg_name == name:
                return True
        # Einzelprozess-Check
        for pid, name in self.get_user_processes():
            if isinstance(pid, list):
                if sel == f"{name} (alle Instanzen)" and fg_name == name:
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
                    self.set_status("AutoClicker aktiv", color="blue")
                    self.click_thread = threading.Thread(target=self.click_loop, daemon=True)
                    self.click_thread.start()
                else:
                    self.clicking = False
                    self.set_status("Bereit", color="green")
            elif self.mode.get() == "Hold":
                if not self.clicking:
                    self.clicking = True
                    self.set_status("AutoClicker (Hold)", color="blue")
                    self.click_thread = threading.Thread(target=self.click_loop, daemon=True)
                    self.click_thread.start()
        except Exception as e:
            self.set_status(f"Fehler beim Starten: {e}", color="red", is_error=True)

    def click_loop(self):
        try:
            btn_display = self.button_choice.get()
            btn = self.button_map.get(btn_display, "left")
            btn_map = {'left': mouse.Button.left, 'right': mouse.Button.right, 'middle': mouse.Button.middle}
            m = mouse.Controller()
            while self.clicking:
                if not self.is_clicker_allowed():
                    self.clicking = False
                    self.set_status("Nicht im gewählten Programm!", color="orange", is_error=True)
                    break
                m.press(btn_map[btn])
                m.release(btn_map[btn])
                time.sleep(1.0 / max(1, self.kps.get()))
            self.set_status("Bereit", color="green")
        except Exception as e:
            self.set_status(f"Klick-Fehler: {e}", color="red", is_error=True)
            self.clicking = False

    def change_hotkey(self):
        self.setting_hotkey = True
        self.hotkey.set('...')
        self.set_status("Hotkey wählen...", color="orange")
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
                self.set_status("Bereit", color="green")
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
                self.set_status("Bereit", color="green")
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
        self.set_status("Failsafe aktiv", color="red")
        self.after(1000, self.failsafe_cooldown)

    def failsafe_cooldown(self):
        if time.time() < self.failsafe_time:
            self.set_status("Failsafe aktiv", color="red")
            self.after(1000, self.failsafe_cooldown)
        else:
            self.failsafe_active = False
            self.set_status("Bereit", color="green")

    def set_status(self, text, color="green", is_error=False):
        if self.failsafe_active:
            text = f"Failsafe aktiv ({max(0, int(self.failsafe_time - time.time()))}s)"
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
            self.set_status("pystray/Pillow nicht installiert!", color="red", is_error=True)
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
            pystray.MenuItem('Öffnen', self.restore_from_tray),
            pystray.MenuItem('Beenden', self.exit_from_tray)
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
        # Fensterhandle zu Prozess-Map
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
        # Prozesse gruppieren nach Name, nur mit sichtbarem Fenster
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
        # Namen gruppieren, aber alle PIDs merken
        result = []
        for name, pids in name_pid_map.items():
            if len(pids) == 1:
                result.append((pids[0], name))
            else:
                result.append((pids, name))
        # Sortiert nach Name
        return sorted(result, key=lambda x: x[1].lower())

if __name__ == "__main__":
    app = AutoClickerApp()
    app.run()
