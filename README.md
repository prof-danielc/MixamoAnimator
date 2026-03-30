# MixamoAnimator

Automate character uploads and animation downloads from Mixamo using direct API integration and Playwright.

This project is based on the API research and original work of [MixamoHarvester](https://github.com/paulpierre/MixamoHarvester).

## Features

-   **Direct API Integration**: Faster and more robust than web scraping.
-   **Web Scraping Fallback**: If API fails for any reasons the system uses web scraping.
-   **Upload Character**: Automatically upload FBX/OBJ/ZIP characters to Mixamo.
-   **Download Animations**: Concurrent multi-threaded downloads of animations.
-   **Animation Catalog**: Local caching of the Mixamo animation library.
-   **Blender Integration**: Script to merge multiple downloaded animations into a single GLB file with NLA tracks.
-   **Session Management**: Saves login state and API tokens for seamless reuse.

## Setup

1.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

2.  **Install Playwright Browsers:**
    ```bash
    playwright install chromium
    ```

3.  **Authentication:**
    Create a `mixamo_token.txt` file in the root directory and paste your Mixamo Bearer Token, OR run the script in headful mode once to let it extract the token automatically from your browser session.

## Usage

### Main Application (`main.py`)

Run the main script to start the interactive CLI:

```bash
python main.py
```

#### Command Line Options

| Option | Description |
| :--- | :--- |
| `--model_path` | Path to the 3D model file (`.fbx`, `.obj`, `.zip`) to upload. |
| `--headless` | Run browser in headless mode (default). |
| `--no-headless` | Run browser in headful mode (recommended for first-time login). |
| `--output_dir` | Directory where animations will be saved (default: `downloads`). |
| `--limit` | Max animations to fetch from catalog (default: 50). |
| `--no-skin` | Download animations without skin (smaller files, ideal for Blender). |
| `--no-refresh-catalog` | Use the local `animations_catalog.json` cache instead of fetching from API. |
| `--animations` | List of animation names to download (e.g., `--animations Wave "Running Fast"`) to bypass the selection UI. |

### Batch Examples

We've provided several `.bat` files as examples of how to automate the workflow:

-   **`run.bat`**: A simple headless run that uploads `TPose.fbx` and fetches the full catalog (2500 items).
    ```batch
    python main.py --headless --model_path TPose.fbx --limit 2500
    ```
-   **`run_animation_list.bat`**: Demonstrates how to download specific animations by name without using the interactive UI.
    ```batch
    python main.py --model_path TPose.fbx --headless --no-refresh-catalog --animations Wave Waving
    ```
-   **`run_merge_animations.bat`**: Runs the Blender merge script.
    ```batch
    python merge_animations.py
    ```

### Merging Animations (`merge_animations.py`)

This script uses Blender (in background mode) to take all animations in your `downloads` folder and merge them onto a single master skeleton. It creates a `.glb` file where each animation is a separate NLA track.

**Usage:**
```bash
python merge_animations.py --folder "./downloads" -- "./textures" --master "TPose.fbx" --output "Merged.glb"
```

**Parameters:**
-   `--folder`: Directory containing the FBX files to merge.
-   `--tex`: Directory to search for textures (recursive search).
-   `--master`: The base T-Pose/Model file to use as the skeleton.
-   `--output`: Name of the exported GLB file.

*Note: Requires Blender 3.x or 4.x to be installed and in your PATH (or in a standard install location).*

## Project Structure

-   **`bot/`**: Core logic including `MixamoAPIClient` and `MixamoBot`.
-   **`cli/`**: UI components using `rich` and `inquirer`.
-   **`config/`**: Settings and configuration management.
-   **`merge_animations.py`**: A standalone wrapper that executes an embedded Blender script to combine animations.
-   **`tests/`**: Comprehensive test suite for API and Bot logic.

## Credits

Special thanks to [Paul Pierre](https://github.com/paulpierre) and the [MixamoHarvester](https://github.com/paulpierre/MixamoHarvester) project for providing the foundational research on the Mixamo API.

## Security

-   `session.json` and `mixamo_token.txt` contain sensitive authentication data.
-   These files are ignored by git via `.gitignore`.
-   **Never** share your token or session files publicly.
