# Fortress Coverage Optimization

## Table of Contents

- [Description](#description)
- [Installation and Launch](#installation-and-launch)
- [Functionality](#functionality)
- [Working with the Graph](#working-with-the-graph)
- [Vertex Types and Constraints](#vertex-types-and-constraints)
- [File Formats](#file-formats)
- [Usage Example: Settings for Rogieria](#usage-example-settings-for-rogieria)
- [Troubleshooting](#troubleshooting)

---

## Description

Interactive application for working with undirected graphs:

- Edit the graph in text form with automatic edge symmetrisation.
- Graph visualisation with drag‑and‑drop nodes and zoom (standard matplotlib toolbar).
- Calculation of a minimal set of “forts” covering the entire graph (dominating set problem) taking into account:
  - mandatory (red) vertices,
  - preferred (orange) vertices,
  - exceptional (purple) vertices,
  - group constraints (“at least N from a set of vertices”),
  - neighbouring‑fort restrictions (three modes).
- Manual validation of an arbitrary set of forts.
- Support for two languages: Russian and English, switchable on the fly.

The application uses the **PuLP** library to solve an ILP model exactly, which allows optimal coverage to be found for graphs with hundreds of vertices in a few seconds.

---

## Installation and Launch

### Requirements

- Python 3.8 or higher ([python.org](https://python.org))
- Install dependencies:

  ```bash
  pip install networkx matplotlib pulp
  ```

### Project Structure

Download the files and place them in one folder:

```directory
project_folder/
├── graph_app.py
├── localization.py
└── localization/
    ├── ru.json
    └── en.json
```

> **Important:** The folder with translations must be named **`localization`**. If you rename it, change `lang_dir` in `localization.py`.

### Launch

From the command line in the project folder run:

```bash
python graph_app.py
```

If successful, the main application window will open.

---

## Functionality

### Main Features

- **Graph input** – the top‑left text area (format described below).
- **Name dictionary** – mapping vertex numbers to their names (e.g., `817 : Bladeskeep`).
- **Mandatory vertices** – for mission trees that require a fort in a specific province.
- **Preferred vertices** – the optimiser will try to include them (among solutions with the same number of forts).
- **Exceptional vertices** – used in the “allow only in exceptional” neighbour‑fort mode.
- **Group constraints** – line like `GroupName: province1,province2,province3 : 1` means “at least one fort from the set of vertices 762,761,759”.
- **Neighbour fort restrictions** – three modes of restrictions on building forts in adjacent provinces.
- **Optimisation** – button “Find Optimal Coverage”.
- **Manual validation** – enter a list of vertices (separated by spaces, commas, or newlines) and the program will report any violations.
- **Save / Load configuration** – all input (graph, names, lists, groups, timer, mode) is saved to `graph_config.json`.
- **Language switching** – button that toggles between “English” / “Русский”.
- **Toolbar** – standard matplotlib toolbar (zoom, pan, home).

---

## Working with the Graph

### Graph Description Format

Each line: `<vertex> : <comma‑separated neighbor list>`

- Spaces are ignored.
- Lines starting with `#` are treated as comments.
- The graph is undirected – the program will automatically add reverse edges (keep in mind that deleting a province and its connections will be more difficult because the program will re‑add them based on connections recorded in other vertices. To avoid this, increase the graph update timer).
- Vertices mentioned as neighbours but lacking their own definition line will be placed in the `# Unattended` section (automatically).

**Example:**

```config
# Northern lands
779 : 777, 778, 780
778 : 358, 775, 777, 779
```

### Interaction with Visualisation

- **Drag nodes** – hold left mouse button on a node and move.
- **Pan** – use the toolbar buttons (hand with a magnifying glass) or right mouse button (if custom panning is not disabled; the current version uses only the toolbar).
- **Zoom** – mouse wheel or toolbar buttons.
- **Reset view** – “Home” button on the toolbar.

---

## Vertex Types and Constraints

| Colour | Role | Effect on Optimisation |
| -------- | ------ | ------------------------ |
| 🔴 Red | Mandatory fort | Always included in the solution |
| 🟠 Orange | Preferred fort | Maximised among solutions with minimal number of forts |
| 🟣 Purple | Exceptional fort | May be allowed as a neighbour (mode 1) |
| 🟡 Gold | Ordinary fort | Chosen by the algorithm when necessary |
| 💗 Pink | Fort that belongs to a group constraint | Separate colour for clarity |

### Group Constraints

Syntax: `Name: vertex1, vertex2, ... : minimum_count`

**Example:** `Falsemire: 762,761,759 : 1` – at least one of the three specified vertices must be a fort.

### Neighbour Fort Modes

- **0 – Forbid any neighbouring forts** – no pair of adjacent vertices may both be forts.
- **1 – Allow only in exceptional** – if two adjacent vertices are both forts, at least one of them must be purple (exceptional).
- **2 – No restrictions** – any combination is allowed.

---

## File Formats

### `graph_config.json`

Automatically created on save. Contains all data from the text areas and settings:

- `graph_config` – the graph text,
- `names_config` – the name dictionary,
- `mandatory_list` / `preferred_list` / `purple_list` – vertex lists,
- `group_list` – group constraints,
- `update_delay_ms` – auto‑update timer (ms),
- `neighbor_constraint_mode` – selected mode (0/1/2).

### `localization/ru.json` and `en.json`

Translation files. When adding new keys you need to edit both files. The keys used by the program are listed in the JSON files themselves.

---

## Usage Example: Settings for Rogieria

The program includes several files containing ready‑made input data for the **Rogieria** tag (Anbennar mod). These files allow you to reproduce the optimal fort coverage given in `Rogieria Solution.txt`.

### 1. Prepare the Files

Make sure you have the following files (they are located in the **Examples** folder):

- `Adjacents.txt` – graph description (adjacency list)
- `Dictionary.txt` – vertex name dictionary (number → name)
- `Mandatory.txt` – mandatory forts (red)
- `Preferable.txt` – preferred forts (orange)
- `Exceptional.txt` – exceptional forts (purple)
- `Mandatory Group.txt` – group constraints
- `Rogieria Solution.txt` – expected result (for verification)

### 2. Step‑by‑Step Loading into the Application

1. **Launch the program** (`python graph_app.py`).

2. **Graph Configuration**  
   Open `Adjacents.txt` (e.g., in Notepad), select all content and copy (Ctrl+A, Ctrl+C). Paste it (Ctrl+V) into the top‑left “Graph Configuration” text area.  
   > If needed, the program will automatically add missing reverse edges.

3. **Name Dictionary**  
   Copy the contents of `Dictionary.txt` into the “Node names dictionary (number : name)” field.

4. **Mandatory Forts**  
   Copy `Mandatory.txt` into the “Mandatory forts (red)” field.

5. **Preferred Forts**  
   Copy `Preferable.txt` into the “Preferred forts (orange)” field.

6. **Exceptional Forts**  
   Copy `Exceptional.txt` into the “Exceptional forts (purple)” field.

7. **Group Constraints**  
   Copy `Mandatory Group.txt` into the “Group constraints” field.

8. **Neighbour Fort Mode**  
   In the “Neighbor fort restrictions” section select:  
   **“Allow only in exceptional (purple) vertices”** – this is the mode used in the example (see last line of `Rogieria Solution.txt`: *Neighbor fort mode: allow only in preferred (purple) vertices*).

9. **Apply Configuration**  
   Click **“Apply Configuration”** to display the graph on the right panel. Adjust zoom and position if needed (matplotlib toolbar).

10. **Optimisation**  
    Click **“Find Optimal Coverage”**.  
    The program will compute a minimal set of forts respecting all entered constraints.

### 3. Compare with the Expected Result

After the calculation finishes, the “Result” area will show the list of selected forts. Compare it with the contents of `Rogieria Solution.txt`. Both lists should match almost exactly (order and wording may differ slightly, but vertex numbers and their statuses will be the same).

Example expected fragment:

```config
Selected forts:
229 (Bal_Mire) (mandatory)
358 (Coldrest) (exceptional)
725 (Entalenham) (mandatory)
...
```

### 4. Notes

- If you want to save all entered data for later use, click **“Save Configuration”** – a file `graph_config.json` will be created. Next time you can load it with the **“Load Configuration”** button.
- The files `Dictionary.txt`, `Mandatory.txt`, etc. are prepared according to the program’s syntax – comments (lines starting with `#`) are ignored, vertices can be listed in any convenient format (one per line, spaces, or commas).
- The solution obtained by the program should match the one in `Rogieria Solution.txt` if you use the same input data and mode.

---

## Troubleshooting

### Error “localisation file not found”

Make sure the folder is named **`localization`** (not `localisations`, not `locale`) and that `ru.json` and `en.json` are inside it. If you renamed it, change `lang_dir` in `localization.py`.

### Error “PuLP not installed”

Install PuLP: `pip install pulp`. Alternatively, you can use only manual coverage validation (optimisation will not work).

### Graph appears mirrored / incorrectly

Use the pan and zoom on the toolbar to rotate/move the view. You can also manually drag vertices.

### No forts found or solution too slow

- For graphs larger than 300 vertices, ILP may take minutes. Increase `timeLimit` in `solve_with_pulp` (currently 300 seconds).
- Ensure that the mandatory vertices can actually cover the graph – otherwise no solution exists.
- Group constraints can significantly complicate the problem.

---

## License and Contacts

The program was ~~generated by a neural network~~ developed within the community. You are free to use, modify, and redistribute it. All third‑party libraries are open‑source.

If you have any questions, open an issue on GitHub.

**Good luck with fortress optimisation!**
