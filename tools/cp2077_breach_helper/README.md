# CP2077 Breach Helper (Windows)

Dieses Tool erstellt eine kleine GUI-App für Windows, die auf `Alt+Strg+Druck` reagiert:

1. Prüft, ob `Cyberpunk2077.exe` läuft.
2. Erstellt einen Screenshot des Hauptmonitors.
3. Prüft heuristisch, ob das Breach-Protokoll-Minigame zu sehen ist.
4. Versucht Matrix und Zielsequenzen per OCR auszulesen.
5. Berechnet eine Lösung gemäß den Minigame-Regeln.
6. Zeigt die Ausgabe per Windows-Systembenachrichtigung an.

## Architektur

- `app.py`: GUI, Hotkey, Prozessprüfung, Screenshot, Notification.
- `detector.py`: Bild-Heuristik + OCR-Extraktion für Matrix/Sequenzen.
- `solver.py`: DFS-Löser mit den CP2077-Auswahlregeln (Zeile/Spalte alternierend).
- `tests/test_solver.py`: Unit-Tests für den Solver.

## Voraussetzungen (Windows)

- Python 3.11+
- Tesseract OCR installiert und im PATH
- Abhängigkeiten:

```powershell
pip install -r requirements.txt
```

## Start

```powershell
python app.py
```

## Hinweise

- OCR ist abhängig von Auflösung, Sprache, HUD-Skalierung und Kontrast.
- Für bessere Erkennung kann man später feste Template-Matching-Regionen pro Auflösung ergänzen.
- Aktuell wird nur ein erster, praktikabler Prototyp geliefert.
