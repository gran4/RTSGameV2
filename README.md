# SantaFest Destiny (RTSGameV2)

An experimental real-time strategy and settlement builder written in Python on top of the [Arcade](https://api.arcade.academy/en/latest/) engine. Guide Santa's helpers across procedurally generated archipelagos, build production chains, defend villages from raiders, and progress through a branching science tree with permanent upgrades that carry across runs.

The project mixes traditional RTS mechanics (base building, population/jobs, naval combat, enemy raids) with roguelite progression (history currency, repeatable upgrades, unlockable tech) and a festive setting built around presents, reindeer, and snowstorms.

## Feature Highlights

- **Arcade-powered rendering** – custom UI widgets, water shaders, particle effects, and compatibility helpers (`gui_compat.py`) keep the game running on Arcade 3.x.
- **Dynamic world creation** – `CustomCellularAutomata.py` builds playable islands by blending multiple cellular automata passes; `MyGame` then repopulates the map with terrain sprites, resources, and shoreline overlays.
- **Economy + logistics** – manage presents, wood, stone, metal, and science. Buildings from `Buildings.py` produce or store different resources, allow garrisoning, and change enemy spawn heatmaps.
- **Combat + AI** – `Enemys.py`, `Player.py`, and `MyPathfinding.py` define people, boats, enemy waves, and A\* pathfinding. Snow towers, boats, and units use `effects/` projectiles and fires.
- **Meta progression** – the start menu view (`main.py`) exposes the science tree, progress menu, and repeatable upgrades driven by `resources/GameBase.json` and stored in `resources/game.json`.
- **Save slots + tutorial** – three world slots are written to `save_files/`, plus a guided tutorial (`MyTutorial`) that walks through controls without touching persistent data.
- **Packaging ready** – PyInstaller specs (`main.spec`, `MainTestResizable.spec`) and a runtime hook (`pyi_arcade_version_fix.py`) create redistributable builds while keeping Arcade's assets available.

## Repository Layout

| Path | Purpose |
| --- | --- |
| `main.py` | Entry point, Arcade views (start menu, tutorial, main game, credits, volume menu, etc.), saving/loading, combat and water shader orchestration. |
| `BackGround.py`, `Buildings.py`, `Player.py`, `Enemys.py` | Core gameplay entities: terrain tiles, buildable structures, controllable people/boats, and hostile units. |
| `Components.py` | Shared UI widgets, text rendering, health bars, camera helpers, and direct Arcade compatibility shims. |
| `CustomCellularAutomata.py` | Standalone prototype used to generate and visualize randomized cave/island layouts. |
| `MyPathfinding.py` | Tile graph + A\* helpers (`LivingMap`, `_AStarSearch`) that drive path planning for people and enemies. |
| `effects/` | Particle, fire, and projectile helpers (`effects/fire.py`, `effects/projectiles.py`). |
| `resources/` | Sprites, audio, fonts, JSON configuration (`GameBase.json`, `game.json`). Bundled via PyInstaller. |
| `buttonInfo.json`, `textInfo.json` | Alternate UI definitions for selectable build/people/boat buttons and menu descriptions. |
| `save_files/` | Binary pickle saves keyed by world slot; safe to delete to reset progress. |
| `logs/ui.log` | Runtime log for UI actions, volume changes, and crash diagnostics. |

## Requirements

- **Python 3.11** (a local virtual environment already exists in `venv/` and was created with 3.11.3).
- **pip** plus the following packages:
  - `arcade>=3.0,<4`
  - `pyglet>=2.0,<3`
  - `pyinstaller>=6` (only needed for standalone builds)
  - Arcade automatically pulls in Pillow, numpy, and ModernGL.
- A GPU/driver that supports OpenGL 3.3 (Arcade's minimum).

If you're on macOS with Homebrew-installed Python, you may need to run inside `pythonw` or grant the terminal "Screen Recording" permission so Arcade can create an OpenGL context.

## Quick Start

```bash
# 1) Create/refresh a virtual environment (optional if you want to reuse ./venv)
python3.11 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 2) Upgrade pip and install runtime dependencies
python -m pip install --upgrade pip
python -m pip install "arcade>=3.0,<4" "pyglet>=2.0,<3"

# (Optional) Tools used for packaging/distribution
python -m pip install "pyinstaller>=6"
```

The repo keeps a `venv/` directory that you can reactivate (`source venv/bin/activate`) instead of creating a new one if you trust its Python version.

## Running the Game

### From source (recommended)

1. **Activate an environment**
   ```bash
   # macOS/Linux
   source venv/bin/activate
   # Windows PowerShell
   .\venv\Scripts\Activate.ps1
   ```
   Alternatively, create a fresh `.venv` with `python3.11 -m venv .venv` and substitute `.venv` in the commands below if you prefer to keep `venv/` untouched.
2. **Install requirements** (only needed the first time or after pulling new dependencies):
   ```bash
   python -m pip install --upgrade pip
   python -m pip install "arcade>=3.0,<4" "pyglet>=2.0,<3"
   ```
   On Apple Silicon, Homebrew’s Python often installs Arcade’s wheel under `~/Library/Python/3.11/lib/python/site-packages`; activating the virtual environment keeps everything isolated.
3. **Launch the game window**:
   ```bash
   python main.py
   ```
   - Use `pythonw main.py` on macOS if the default interpreter cannot create an OpenGL context from a non-GUI terminal.
   - On Windows, `py -3.11 main.py` ensures you target the expected version.
4. **(Optional) Auto-reload assets** – run from an IDE such as VS Code or PyCharm with “Run on Save” enabled so edits to sprites or JSON immediately show up after pressing `R` in the window (Arcade reloads textures when a file timestamp changes).

### Alternative entry points

- `python CustomCellularAutomata.py` launches the standalone terrain generator window so you can iterate on island parameters without booting the full game loop.
- `pyinstaller main.spec` (see “Packaging” below) creates `dist/main/main` (Windows/Linux) and `dist/main/main.app` (macOS). Double-click the generated binary to run without Python installed.
- `pyinstaller MainTestResizable.spec` builds the alternate spec that keeps Arcade’s console for debugging and uses the test view defined in `MainTestResizable.spec`.
- `python -m arcade --version` validates that Arcade is discoverable by the interpreter before you attempt to run the game.

### Game flow & controls

1. **Start Menu** – choose one of the three world slots (empty slots show “World N (Empty)”), open the tutorial, inspect the science tree, visit the standalone Upgrades menu (repeatable bonuses distinct from the science/progression tree), or peek at the Credits screen that lists asset contributors (most sprites/animations are custom, but not all). Slots save to `save_files/world_<slot>.pkl`.
2. **World Creation** – if a slot does not yet exist you’ll be taken to the world setup view where you pick the world generator (Normal / Desert / Forest) and difficulty.
3. **In-Game Controls**
   - `WASD` / arrow keys move the player between tiles (`main.py:1953`).
   - `H` cycles HUD panels between summary/detail to declutter the UI.
   - Left-click selects buildings/people/boats, places constructions, interacts with menu buttons, and triggers object-specific actions (`Buildings.BaseBuilding.clicked`).
   - Right-click (or mouse button 4) on UI buttons displays contextual tooltips in many menus (see `startMenu.Start`, `MyGame.on_ScienceMenuclick`).
   - Mouse drag scrolls the deployable buttons list when it grows taller than the screen.
   - The bottom-left speed slider lets you slow the sim down to 0.5× or crank it to 10× during intense waves.
   - The collapsible top-right sidebar (`Panels`, `Menus`, `Deploy`, `Save`, `Return`) drives the loop:
     - `Panels` expands the HUD summary/detail cards; the persistent top-left resource strip always shows presents, wood, stone, metal, and science totals.
     - `Menus` opens the science tree, volume controls, and includes the `Save` button, while `Return` hops back to the start screen.
     - `Deploy` toggles between Buildings, People, and Boats so you can place new assets.
   - Boats auto-embark characters standing on top of them; the leave/move/destroy buttons appear once a boat is selected (`Player.BaseBoat.clicked`).
4. **Saving/Returning** – click the `Save` button (top-right `Menus` column) to serialize the current run, or `Return` to go back to the start menu. Saves are disabled during the tutorial to keep it deterministic.

Game data (resources, science unlocks, bonuses) is summarized at the bottom of the HUD, while alerts and informational popups appear near the minimap area.

### Gameplay loop & progression

1. **Gather → Build → Operate** – people are your universal workers. March them onto tree, stone, or berry sprites to harvest; park them on top of a ghosted building footprint to help construct; then send them *into* finished structures to activate their production bonuses (`Buildings.BaseBuilding.add/remove` manage occupancy).
2. **Maintain presents** – every in-game “Christmas” deadline consumes a quota of presents. Keep production buildings staffed and upgrade multipliers so you can pay the quota; failing too many times ends the run.
3. **Defend the village** – naughty children (enemies) arrive in escalating waves. Move soldiers/boats into firing range, place towers, and keep Fire Stations ready. Boats can ferry units across water, and shoreline overlays show likely landing zones.
4. **Save & resume** – hit the `Save` button in-game to serialize the entire state (resources, terrain, buildings, enemies) into the active slot. Loading from the start menu restores *everything*, so you can pause mid-run.
5. **Death & History** – when your population is wiped or you miss the present quota, the run ends. You gain `History`, a meta-currency spent on the science tree, progress menu, and repeatable upgrades back at the start menu. These unlocks persist across worlds and speed up the next attempt.
6. **Tutorial status** – the tutorial view (`MyTutorial`) mirrors the normal loop but is currently broken and mainly serves as a sandbox showcasing every implemented enemy type. It does not allow saving and should be treated as a museum rather than a guided intro until it is rebuilt.

Keep repeating the loop: expand resource harvesting, erect defenses, stockpile presents, survive the next raid, and eventually fall to unlock more of the tech tree.

## Progression, Saves, and Data Files

- **World saves** – stored as pickled dictionaries in `save_files/`. Each file contains player/building/boat/enemy snapshots, terrain state, and resource counts. Delete a slot file to reset that world.
- **Meta progression** – `resources/game.json` tracks unlock states for the science tree, progress menu, repeatable upgrades, audio levels, and accumulated “History” currency. The start menu normalizes/repairs this file on load to survive schema changes.
- **GameBase.json** – defines the nodes displayed in the in-game science tree (`ScienceMenu`), the progress milestones (`ProgressUpgradeMenu`), and repeatable upgrade templates (`RepeatableUpgrades`). Tweak this file to rebalance unlock costs, prerequisites, or reward multipliers.
- **UI definitions** – `buttonInfo.json` and `textInfo.json` can override the selectable buttons and their ordering if you want to prototype a new UI quickly. `TextInfo.py` contains the authoritative definitions used for deployment categories, placement requirements, and tooltips.
- **Logs** – `logs/ui.log` collects information about UI manager events, slider interactions, and exceptions to make debugging easier. Delete the file if it grows large; a new one is created automatically.

## Customization Tips

- **Resources and sprites** live under `resources/`. Replace textures/audio there (respecting existing filenames) if you want to re-skin the game. Make sure the replacements keep the same dimensions; many sprites rely on fixed hitboxes (`BackGround.py`, `Buildings.py`).
- **Terrain + generation** – tweak `CustomCellularAutomata.py` constants (e.g., `CHANCE_TO_START_ALIVE`, `NUMBER_OF_STEPS`) to experiment with new map densities, then feed the resulting grids into `MyGame` if you want to change the default world look.
- **Enemy behavior** – modify `Enemys.py` or `MyPathfinding.py` to adjust attack waves, spawn rates, or routing logic. `MyGame.BuildingChangeEnemySpawner` demonstrates how buildings alter spawn heatmaps.
- **Audio** – replace or add audio assets in `resources/audio/` and wire them up inside `main.py`’s views. `apply_audio_volume` centralizes volume scaling across UI/background channels.
- **Shaders** – the water shader is defined at the top of `main.py` (`WATER_VERTEX_SHADER`, `WATER_FRAGMENT_SHADER`). Adjust parameters such as `WATER_OVERLAY_REPEAT` or `WATER_TIME_SCALE` to experiment with different looks.

## Packaging a Standalone Build

PyInstaller configs are already checked in:

```bash
python -m pip install "pyinstaller>=6"
pyinstaller main.spec
# or pyinstaller MainTestResizable.spec for the alternate entry point
```

`pyi_arcade_version_fix.py` is registered as a runtime hook so Arcade knows its version number when frozen. Assets under `resources/` are included via the `datas` section of the spec. Finished binaries land in `dist/` and staging files go into `build/`.

## Troubleshooting

- **Arcade crashes on launch** – ensure your GPU/driver supports OpenGL 3.3. On macOS, running `pythonw main.py` or launching from a terminal with screen-recording permission often fixes “invalid drawable” errors.
- **Water shader disabled** – if the GPU can’t compile the GLSL code, `MyGame._init_water_shader` logs the error and falls back to a static overlay. Check `logs/ui.log` for details.
- **Corrupted save** – delete the offending `save_files/world_<slot>.pkl` file (and optionally `resources/game.json`) to rebuild from defaults. The save loader already guards against missing or renamed classes, but manual edits can still break pickles.
- **PyInstaller build missing assets** – make sure you run PyInstaller from the repository root so the relative `resources` path resolves, and keep `pyi_arcade_version_fix.py` next to `main.spec`.

---

SantaFest Destiny is still a prototype; balance numbers, UI layout, and content change frequently. Contributions are easiest when focused on isolated modules (e.g., adding a new building class in `Buildings.py` or expanding the science tree JSON). Enjoy experimenting, and feel free to iterate on the gameplay loop! 
