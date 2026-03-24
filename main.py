#!/usr/bin/env python3
import argparse
import sys
import os
import logging
from pathlib import Path
from config.settings import SettingsManager
from bot.mixamo_bot import MixamoBot
from cli.ui import UI

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """
    Main entry point for the MixamoAnimator bot.
    Coordinates settings, the Playwright bot, and the terminal UI.
    """
    parser = argparse.ArgumentParser(description="Mixamo Animator Bot")
    parser.add_argument("--model_path", type=str, help="Path to the 3D model file (fbx, obj, zip)")
    parser.add_argument("--headless", action="store_true", default=False, help="Run browser in headless mode")
    parser.add_argument("--no-headless", action="store_false", dest="headless", help="Run browser in headful mode")
    parser.add_argument("--output_dir", type=str, default="downloads", help="Directory to save animations")
    parser.add_argument("--limit", type=int, default=20, help="Maximum number of animations to fetch from catalog (Mixamo has ~2500)")
    
    args = parser.parse_args()
    ui = UI()
    settings = SettingsManager()

    # 1. Ensure credentials exist
    if not settings.email or not settings.password:
        ui.print_header("Mixamo Credentials")
        ui.print_message("Credentials not found in config. Please enter them below.")
        email, password = ui.get_credentials()
        settings.email = email
        settings.password = password
        settings.save()
        ui.print_success("Credentials saved to config.json")

    # 2. Resolve model path
    model_path = args.model_path
    if not model_path:
        model_path = ui.console.input("[bold yellow][?][/bold yellow] Enter path to your 3D model: ").strip()
    
    model_path = os.path.abspath(model_path)
    if not os.path.exists(model_path):
        ui.print_error(f"Model file not found: {model_path}")
        sys.exit(1)

    # 3. Initialize Bot
    ui.print_header("Initializing Mixamo Bot")
    bot = MixamoBot(headless=args.headless)
    
    try:
        # 4. Login
        ui.print_message("Logging in to Mixamo...")
        if not bot.login(settings.email, settings.password):
            ui.print_error("Login failed. Please check your credentials and internet connection.")
            sys.exit(1)
        ui.print_success("Logged in successfully.")

        # 5. Upload Character
        ui.print_message(f"Uploading character: {os.path.basename(model_path)}...")
        if not bot.upload_character(model_path):
            ui.print_error("Character upload failed.")
            sys.exit(1)
        ui.print_success("Character uploaded and rigged.")

        # 6. Fetch Catalog
        ui.print_message("Fetching animation catalog...")
        catalog = bot.fetch_animation_catalog(limit=args.limit)
        if not catalog:
            ui.print_error("Failed to fetch animation catalog.")
            sys.exit(1)
        
        # 7. Selection
        selected_anims = ui.select_animations(catalog)
        if not selected_anims:
            ui.print_message("No animations selected. Exiting.")
            return

        # 8. Batch Download
        ui.print_header(f"Downloading {len(selected_anims)} Animations")
        
        with ui.create_progress_bar() as progress:
            task = progress.add_task("[cyan]Downloading...", total=len(selected_anims))
            
            # Since download_animations handles the loop internally in the bot class,
            # we'll tweak it to support progress reporting if needed, 
            # or just call it and update at the end.
            # For now, let's call it and update progress.
            
            results = bot.download_animations(selected_anims, args.output_dir)
            progress.update(task, completed=len(selected_anims))

        # 9. Report
        success_count = sum(1 for r in results.values() if r)
        ui.print_header("Execution Summary")
        ui.print_message(f"Total Selected: {len(selected_anims)}")
        ui.print_message(f"Successfully Downloaded: {success_count}")
        ui.print_message(f"Failed: {len(selected_anims) - success_count}")
        ui.print_success(f"Animations saved to: {os.path.abspath(args.output_dir)}")

    except Exception as e:
        ui.print_error(f"An unexpected error occurred: {str(e)}")
    finally:
        ui.print_message("Closing browser...")
        bot.stop()
        ui.print_message("Done.")

if __name__ == "__main__":
    main()
