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

def create_parser():
    parser = argparse.ArgumentParser(description="Mixamo Animator Bot")
    parser.add_argument("--model_path", type=str, help="Path to the 3D model file (fbx, obj, zip)")
    parser.add_argument("--headless", action="store_true", default=False, help="Run browser in headless mode")
    parser.add_argument("--no-headless", action="store_false", dest="headless", help="Run browser in headful mode")
    parser.add_argument("--output_dir", type=str, default="downloads", help="Directory to save animations")
    parser.add_argument("--limit", type=int, default=20, help="Maximum number of animations to fetch from catalog (Mixamo has ~2500)")
    parser.add_argument("--no-skin", action="store_true", default=False, help="Download animations without skin (useful for Blender)")
    parser.add_argument("--inplace", action="store_true", default=False, help="Download animations in place (root motion locked to origin)")
    parser.add_argument("--no-refresh-catalog", action="store_false", default=True, help="Uses animation catalog cache")
    parser.add_argument("--animations_names", nargs="+", type=str, default=None, help="List of animation names to download (bypasses selection UI)")
    parser.add_argument("--animations_ids", nargs="+", type=str, default=None, help="List of animation ids to download (bypasses selection UI)")
    parser.add_argument("--animations_descriptions", nargs="+", type=str, default=None, help="List of animation descriptions to download (bypasses selection UI)")
    return parser

def main():
    """
    Main entry point for the MixamoAnimator bot.
    Coordinates settings, the Playwright bot, and the terminal UI.
    """
    parser = create_parser()
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
    ui.display_api_status(bot.api_client is not None)
    
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
        catalog = bot.fetch_animation_catalog(limit=args.limit, force_refresh=args.no_refresh_catalog)
        if not catalog:
            ui.print_error("Failed to fetch animation catalog.")
            sys.exit(1)
        
        # 7. Selection
        selected_anims = []
        
        if args.animations_names:
            # If animations were specified via CLI, filter the catalog accordingly
            # this is case insensitive and partial match based on the animation name
            selected_anims_tmp = [
                anim for anim in catalog
                if any(
                    chosen.lower() in anim["name"].lower()
                    for chosen in args.animations_names
                )
            ]
            
            if not selected_anims_tmp:
                ui.print_error(f"No matching animations in catalog for the specified names.")
                sys.exit(1)
            else:
                selected_anims.extend(selected_anims_tmp)

        if args.animations_ids:
            # If animations were specified via CLI, filter the catalog accordingly
            # this is case insensitive and partial match based on the animation name
            selected_anims_tmp = [
                anim for anim in catalog
                if any(
                    chosen.lower() in anim["id"].lower()
                    for chosen in args.animations_ids
                )
            ]
            
            if not selected_anims_tmp:
                ui.print_error(f"No matching animations in catalog for the specified ids.")
                sys.exit(1)
            else:
                selected_anims.extend(selected_anims_tmp)
                
        if args.animations_descriptions:
            # If animations were specified via CLI, filter the catalog accordingly
            # this is case insensitive and partial match based on the animation name
            selected_anims_tmp = [
                anim for anim in catalog
                if any(
                    chosen.lower() in anim["description"].lower()
                    for chosen in args.animations_descriptions
                )
            ]
            
            if not selected_anims_tmp:
                ui.print_error(f"No matching animations in catalog for the specified descriptions.")
                sys.exit(1)
            else:
                selected_anims.extend(selected_anims_tmp)
        
        if not selected_anims:
            selected_anims = ui.select_animations(catalog)
            if not selected_anims:
                ui.print_message("No animations selected. Exiting.")
                return

        # 8. Batch Download
        ui.print_header(f"Downloading {len(selected_anims)} Animations")
        
        with ui.create_progress_bar() as progress:
            task = progress.add_task("[cyan]Starting downloads...", total=len(selected_anims))
            
            def progress_callback(current, total, name, eta_seconds):
                # Format ETA: MM:SS
                eta_str = "Calculating..."
                if eta_seconds > 0:
                    minutes = eta_seconds // 60
                    seconds = eta_seconds % 60
                    eta_str = f"{minutes:02d}:{seconds:02d}"
                
                desc = f"[cyan]Download {current}/{total}: [bold]{name}[/bold] (ETA: {eta_str})"
                progress.update(task, description=desc, completed=current - 1)

            results = bot.download_animations(
                selected_anims, 
                args.output_dir, 
                progress_callback=progress_callback,
                include_skin=not args.no_skin,
                inplace=args.inplace
            )
            progress.update(task, description="[green]All downloads complete!", completed=len(selected_anims))

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
