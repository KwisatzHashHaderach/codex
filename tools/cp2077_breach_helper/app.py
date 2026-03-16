from __future__ import annotations

import threading
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk

import keyboard
import mss
import mss.tools
import psutil
from plyer import notification

from detector import BreachDetector
from solver import BreachSolver


class BreachHelperApp:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("CP2077 Breach Helper")
        self.root.geometry("720x420")

        self.status_var = tk.StringVar(value="Bereit. Hotkey: Alt+Strg+Druck")
        self.output = tk.Text(self.root, wrap=tk.WORD, height=18)
        self.output.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        status = ttk.Label(self.root, textvariable=self.status_var)
        status.pack(fill=tk.X, padx=12, pady=(0, 12))

        self.screenshot_dir = Path("screenshots")
        self.screenshot_dir.mkdir(exist_ok=True)
        self.detector = BreachDetector()

    def start(self) -> None:
        keyboard.add_hotkey("alt+ctrl+print screen", self._on_hotkey)
        self.root.protocol("WM_DELETE_WINDOW", self._close)
        self.root.mainloop()

    def _close(self) -> None:
        keyboard.unhook_all_hotkeys()
        self.root.destroy()

    def _on_hotkey(self) -> None:
        thread = threading.Thread(target=self._run_capture_pipeline, daemon=True)
        thread.start()

    def _run_capture_pipeline(self) -> None:
        self._set_status("Hotkey erkannt. Prüfe Prozess …")
        if not self._is_cyberpunk_running():
            self._notify("Cyberpunk 2077 läuft nicht.")
            self._set_status("Abbruch: Prozess nicht gefunden.")
            return

        screenshot_path = self._capture_screenshot()
        self._append(f"Screenshot gespeichert: {screenshot_path}")

        puzzle = self.detector.parse_screenshot(screenshot_path)
        if puzzle is None:
            self._notify("Kein Breach-Protokoll erkannt.")
            self._set_status("Kein passendes Minigame erkannt.")
            return

        solver = BreachSolver(
            matrix=puzzle.matrix,
            sequences=puzzle.sequences,
            buffer_size=puzzle.buffer_size,
        )
        result = solver.solve()

        if not result.path:
            self._notify("Keine Lösung gefunden.")
            self._set_status("Lösung fehlgeschlagen.")
            return

        token_path = " ".join(step.token for step in result.path)
        matched = ", ".join(str(idx + 1) for idx in result.matched_sequences)
        message = f"Lösung: {token_path}\nErfüllte Sequenzen: {matched or '-'}"

        self._append(message)
        self._notify(message)
        self._set_status("Lösung berechnet und als Benachrichtigung gesendet.")

    def _capture_screenshot(self) -> Path:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_file = self.screenshot_dir / f"capture_{stamp}.png"
        with mss.mss() as sct:
            shot = sct.grab(sct.monitors[1])
            mss.tools.to_png(shot.rgb, shot.size, output=str(out_file))
        return out_file

    def _is_cyberpunk_running(self) -> bool:
        for proc in psutil.process_iter(["name"]):
            name = proc.info.get("name")
            if isinstance(name, str) and name.lower() == "cyberpunk2077.exe":
                return True
        return False

    def _append(self, text: str) -> None:
        self.output.insert(tk.END, f"{text}\n")
        self.output.see(tk.END)

    def _set_status(self, text: str) -> None:
        self.status_var.set(text)

    def _notify(self, text: str) -> None:
        notification.notify(
            title="CP2077 Breach Helper",
            message=text,
            timeout=5,
            app_name="CP2077 Breach Helper",
        )


if __name__ == "__main__":
    app = BreachHelperApp()
    app.start()
