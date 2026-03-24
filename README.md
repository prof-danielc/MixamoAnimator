# MixamoAnimator

Automate character uploads and animation downloads from Mixamo using Playwright.

## Setup

1.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

2.  **Install Playwright Browsers:**
    ```bash
    playwright install chromium
    ```

## Usage

Run the main script to start the CLI:

```bash
python main.py
```

### Command Line Options

-   `--headless`: Run the browser in headless mode (default: False).
-   `--model_path`: Path to the character model (FBX/OBJ/ZIP) to upload.
-   `--output_dir`: Directory to save animations (default: `downloads`).
-   `--limit`: Maximum number of animations to fetch from the catalog (default: 50).

### Initial Login & Security

The first time you run the bot, it's recommended to run in **headful mode** (without the `--headless` flag) if you need to handle complex Adobe SSO steps or MFA.

```bash
python main.py
```

The bot saves its session to `session.json` after a successful login, so you won't need to login every time. Subsequent runs can be done in headless mode:

```bash
python main.py --headless
```

**Security Considerations:**
-   `config.json` stores your Adobe credentials in plain text.
-   `session.json` stores your browser session state, including authentication cookies.
-   Both files are included in `.gitignore` to prevent accidental commits to version control.
-   **Never share these files** or commit them to a public repository.

### Configuration

Settings are stored in `config.json` in the root directory. You can edit this file directly or use the CLI prompts.

```json
{
    "email": "your-email@example.com",
    "password": "your-password"
}
```

## Features

-   **Upload Character:** Upload an FBX/OBJ/ZIP character to Mixamo and trigger the auto-rigger.
-   **Download Animations:** Search and download animations for your character.
-   **Batch Processing:** Automate the download of multiple animations with a progress bar.

## Development

### Running Tests

```bash
python -m pytest tests/
```

### Project Structure

-   `bot/`: Contains `MixamoBot` for Playwright automation.
-   `cli/`: Contains the CLI user interface using `rich` and `inquirer`.
-   `config/`: Contains `SettingsManager` for configuration management.
-   `tests/`: Contains unit and integration tests.
-   `main.py`: Entry point for the application.
