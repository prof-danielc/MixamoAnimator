#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import io
import json
import threading
import time
import webbrowser
from dataclasses import dataclass
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any
from urllib.parse import quote

import requests
from PIL import Image, ImageOps, ImageSequence, ImageTk


PREVIEW_SIZE = (420, 420)
HTTP_TIMEOUT_SECONDS = 20
PREVIEW_CACHE_DIR = Path(".cache") / "animation_previews"
PREVIEW_RETRY_COUNT = 3
PREVIEW_RETRY_DELAY_SECONDS = 0.75
DETAILS_TAG_HIGHLIGHT = "search_highlight"


@dataclass
class PreviewPayload:
    frames: list[Image.Image]
    delays_ms: list[int]
    source: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Browse animations_catalog.json with previews, filters, and export tools."
    )
    parser.add_argument(
        "--catalog",
        type=Path,
        default=Path("animations_catalog.json"),
        help="Path to animations_catalog.json",
    )
    return parser.parse_args()


def normalize_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def load_catalog(catalog_path: Path) -> list[dict[str, Any]]:
    if not catalog_path.exists():
        raise FileNotFoundError(f"Catalog file not found: {catalog_path}")

    with catalog_path.open("r", encoding="utf-8") as catalog_file:
        data = json.load(catalog_file)

    if not isinstance(data, list):
        raise ValueError("animations_catalog.json must contain a JSON array.")

    catalog: list[dict[str, Any]] = []
    for item in data:
        if isinstance(item, dict):
            catalog.append(item)

    catalog.sort(key=lambda animation: normalize_value(animation.get("name")).lower())
    return catalog


def preview_cache_path(source: str) -> Path:
    suffix = Path(source).suffix if not source.startswith(("http://", "https://")) else Path(source.split("?", 1)[0]).suffix
    if not suffix:
        suffix = ".img"
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
    return PREVIEW_CACHE_DIR / f"{digest}{suffix}"


def fetch_source_bytes(source: str) -> bytes:
    if source.startswith(("http://", "https://")):
        cache_path = preview_cache_path(source)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        if cache_path.exists():
            return cache_path.read_bytes()

        last_error: Exception | None = None
        for attempt in range(PREVIEW_RETRY_COUNT):
            try:
                response = requests.get(source, timeout=HTTP_TIMEOUT_SECONDS)
                response.raise_for_status()
                cache_path.write_bytes(response.content)
                return response.content
            except Exception as exc:
                last_error = exc
                if attempt + 1 < PREVIEW_RETRY_COUNT:
                    time.sleep(PREVIEW_RETRY_DELAY_SECONDS)

        if last_error is None:
            raise RuntimeError(f"Failed to download preview from {source}")
        raise last_error

    return Path(source).expanduser().read_bytes()


def build_preview_sources(animation: dict[str, Any]) -> list[str]:
    sources: list[str] = []
    for key in ("thumbnail_animated", "thumbnail"):
        value = normalize_value(animation.get(key)).strip()
        if value and value not in sources:
            sources.append(value)
    return sources


def fit_frame(frame: Image.Image) -> Image.Image:
    contained = ImageOps.contain(
        frame.convert("RGBA"),
        PREVIEW_SIZE,
        Image.Resampling.LANCZOS,
    )
    canvas = Image.new("RGBA", PREVIEW_SIZE, (22, 22, 22, 255))
    x_offset = (PREVIEW_SIZE[0] - contained.width) // 2
    y_offset = (PREVIEW_SIZE[1] - contained.height) // 2
    canvas.alpha_composite(contained, (x_offset, y_offset))
    return canvas


def load_preview_payload(source: str) -> PreviewPayload:
    image_stream = io.BytesIO(fetch_source_bytes(source))

    with Image.open(image_stream) as image:
        frames: list[Image.Image] = []
        delays_ms: list[int] = []

        iterator = ImageSequence.Iterator(image) if getattr(image, "is_animated", False) else [image]

        for frame in iterator:
            frames.append(fit_frame(frame))
            delays_ms.append(max(40, int(frame.info.get("duration", 100))))

    if not frames:
        raise ValueError(f"No preview frames found in {source}")

    return PreviewPayload(frames=frames, delays_ms=delays_ms, source=source)


def highlight_matches_for_list(text: str, query: str) -> str:
    if not query:
        return text

    lowered_text = text.lower()
    lowered_query = query.lower()
    start_index = 0
    output: list[str] = []

    while True:
        match_index = lowered_text.find(lowered_query, start_index)
        if match_index == -1:
            output.append(text[start_index:])
            break
        output.append(text[start_index:match_index])
        output.append(f"[{text[match_index:match_index + len(query)]}]")
        start_index = match_index + len(query)

    return "".join(output)


def non_empty_fields(animation: dict[str, Any]) -> list[tuple[str, str]]:
    ordered_keys = [
        ("name", "Name"),
        ("id", "ID"),
        ("motion_id", "Motion ID"),
        ("type", "Type"),
        ("category", "Category"),
        ("character_type", "Character Type"),
        ("source", "Source"),
        ("description", "Description"),
        ("thumbnail", "Thumbnail"),
        ("thumbnail_animated", "Animated Thumbnail"),
    ]
    rows: list[tuple[str, str]] = []
    for key, label in ordered_keys:
        value = normalize_value(animation.get(key)).strip()
        if value:
            rows.append((label, value))
    if animation.get("motions"):
        rows.append(("Motion Count", str(len(animation["motions"]))))
    return rows


def build_mixamo_url(animation: dict[str, Any]) -> str:
    query_value = normalize_value(animation.get("name")).strip() or normalize_value(animation.get("id")).strip()
    return f"https://www.mixamo.com/#/?page=1&query={quote(query_value)}&type=Motion%2CMotionPack"


def build_cli_args_for_animations(animations: list[dict[str, Any]]) -> str:
    ids = [normalize_value(animation.get("id")).strip() for animation in animations]
    ids = [animation_id for animation_id in ids if animation_id]
    if not ids:
        return ""
    return "--animations_ids " + " ".join(ids)


class AnimationViewer:
    def __init__(self, root: tk.Tk, catalog: list[dict[str, Any]], catalog_path: Path):
        self.root = root
        self.catalog = catalog
        self.catalog_path = catalog_path
        self.animation_by_id = {
            normalize_value(animation.get("id")): animation
            for animation in self.catalog
            if normalize_value(animation.get("id"))
        }
        self.name_counts = self.build_name_counts()
        self.filtered_catalog: list[dict[str, Any]] = []
        self.preview_cache: dict[str, PreviewPayload] = {}
        self.preview_images: list[ImageTk.PhotoImage] = []
        self.preview_payload: PreviewPayload | None = None
        self.preview_frame_index = 0
        self.animation_after_id: str | None = None
        self.preview_request_id = 0
        self.current_animation: dict[str, Any] | None = None
        self.last_preview_sources: list[str] = []
        self.current_displayed_ids: list[str] = []
        self.queue_ids: list[str] = []

        self.search_var = tk.StringVar()
        self.sort_var = tk.StringVar(value="Name (A-Z)")
        self.copy_target_var = tk.StringVar(value="ID")
        self.selection_summary_var = tk.StringVar()
        self.preview_status_var = tk.StringVar(value="Select an animation to load its preview.")
        self.name_var = tk.StringVar(value="No animation selected")
        self.id_var = tk.StringVar(value="")
        self.category_var = tk.StringVar(value="")
        self.description_var = tk.StringVar(value="")
        self.clipboard_status_var = tk.StringVar(value="")
        self.queue_status_var = tk.StringVar(value="Queue is empty.")
        self.duplicate_status_var = tk.StringVar(value="")

        self.build_ui()
        self.bind_events()
        self.apply_filter()

    def build_name_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for animation in self.catalog:
            name = normalize_value(animation.get("name")).strip().lower()
            if name:
                counts[name] = counts.get(name, 0) + 1
        return counts

    def build_ui(self) -> None:
        self.root.title("Mixamo Animation Viewer")
        self.root.geometry("1460x930")
        self.root.minsize(1140, 760)

        container = ttk.Frame(self.root, padding=12)
        container.pack(fill=tk.BOTH, expand=True)

        paned = ttk.Panedwindow(container, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        left_panel = ttk.Frame(paned, padding=(0, 0, 12, 0))
        right_panel = ttk.Frame(paned)
        paned.add(left_panel, weight=1)
        paned.add(right_panel, weight=3)

        filters_frame = ttk.LabelFrame(left_panel, text="Filters", padding=10)
        filters_frame.pack(fill=tk.X)

        ttk.Label(filters_frame, text="Search").grid(row=0, column=0, sticky=tk.W)
        self.search_entry = ttk.Entry(filters_frame, textvariable=self.search_var)
        self.search_entry.grid(row=1, column=0, sticky=tk.EW, pady=(4, 0), padx=(0, 8))

        ttk.Label(filters_frame, text="Sort").grid(row=0, column=1, sticky=tk.W)
        self.sort_filter = ttk.Combobox(
            filters_frame,
            textvariable=self.sort_var,
            state="readonly",
            values=["Name (A-Z)", "Name (Z-A)", "Type", "ID"],
        )
        self.sort_filter.grid(row=1, column=1, sticky=tk.EW, pady=(4, 0))

        filters_frame.columnconfigure(0, weight=1)
        filters_frame.columnconfigure(1, weight=1)

        ttk.Label(left_panel, textvariable=self.selection_summary_var).pack(anchor=tk.W, pady=(10, 8))

        list_frame = ttk.Frame(left_panel)
        list_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.animation_listbox = tk.Listbox(
            list_frame,
            exportselection=False,
            selectmode=tk.EXTENDED,
            yscrollcommand=scrollbar.set,
            activestyle="none",
        )
        self.animation_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.animation_listbox.yview)

        selection_actions = ttk.LabelFrame(left_panel, text="Selection Actions", padding=10)
        selection_actions.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(selection_actions, text="Select All Filtered", command=self.select_all_filtered).grid(row=0, column=0, sticky=tk.EW, padx=(0, 6), pady=(0, 6))
        ttk.Button(selection_actions, text="Clear Selection", command=self.clear_listbox_selection).grid(row=0, column=1, sticky=tk.EW, pady=(0, 6))
        ttk.Button(selection_actions, text="Queue Selected", command=self.queue_selected_animations).grid(row=1, column=0, sticky=tk.EW, padx=(0, 6), pady=(0, 6))
        ttk.Button(selection_actions, text="Export Selected JSON", command=self.export_selected_json).grid(row=1, column=1, sticky=tk.EW, pady=(0, 6))
        ttk.Button(selection_actions, text="Export Selected IDs", command=self.export_selected_ids).grid(row=2, column=0, sticky=tk.EW, padx=(0, 6))
        ttk.Button(selection_actions, text="Copy Selected CLI Args", command=self.copy_selected_cli_args).grid(row=2, column=1, sticky=tk.EW)
        selection_actions.columnconfigure(0, weight=1)
        selection_actions.columnconfigure(1, weight=1)

        ttk.Label(
            left_panel,
            text=f"Catalog: {self.catalog_path}",
            foreground="#666666",
            wraplength=320,
        ).pack(anchor=tk.W, pady=(8, 0))

        details_frame = ttk.Frame(right_panel)
        details_frame.pack(fill=tk.X)

        header_frame = ttk.Frame(details_frame)
        header_frame.pack(fill=tk.X)

        ttk.Label(header_frame, textvariable=self.name_var, font=("Segoe UI", 16, "bold")).pack(side=tk.LEFT, anchor=tk.W)

        header_buttons = ttk.Frame(header_frame)
        header_buttons.pack(side=tk.RIGHT)
        ttk.Button(header_buttons, text="Copy Name", command=lambda: self.copy_current_field("name")).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(header_buttons, text="Copy ID", command=lambda: self.copy_current_field("id")).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(header_buttons, text="Copy CLI Args", command=self.copy_current_cli_args).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(header_buttons, text="Copy JSON", command=self.copy_current_json).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(header_buttons, text="Open in Mixamo", command=self.open_current_in_mixamo).pack(side=tk.LEFT)

        ttk.Label(details_frame, textvariable=self.id_var, foreground="#666666").pack(anchor=tk.W, pady=(2, 2))
        ttk.Label(details_frame, textvariable=self.category_var).pack(anchor=tk.W)
        ttk.Label(details_frame, textvariable=self.description_var, wraplength=900, justify=tk.LEFT).pack(anchor=tk.W, pady=(4, 4))
        ttk.Label(details_frame, textvariable=self.duplicate_status_var, foreground="#8f5a00").pack(anchor=tk.W)

        copy_target_row = ttk.Frame(details_frame)
        copy_target_row.pack(fill=tk.X, pady=(8, 8))
        ttk.Label(copy_target_row, text="Ctrl+C target").pack(side=tk.LEFT)
        ttk.Combobox(
            copy_target_row,
            textvariable=self.copy_target_var,
            state="readonly",
            width=20,
            values=["ID", "Name", "Motion ID", "Description", "CLI Args", "JSON"],
        ).pack(side=tk.LEFT, padx=(8, 12))
        ttk.Button(copy_target_row, text="Copy Selected IDs", command=self.copy_selected_ids).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(copy_target_row, text="Copy Selected JSON", command=self.copy_selected_json).pack(side=tk.LEFT)

        ttk.Label(details_frame, textvariable=self.clipboard_status_var, foreground="#1f6f43").pack(anchor=tk.W, pady=(0, 8))

        preview_frame = ttk.LabelFrame(right_panel, text="Preview", padding=12)
        preview_frame.pack(fill=tk.X)

        self.preview_label = ttk.Label(preview_frame, text="No preview loaded", anchor=tk.CENTER)
        self.preview_label.pack(fill=tk.BOTH, expand=True)
        ttk.Label(preview_frame, textvariable=self.preview_status_var, wraplength=900, foreground="#666666").pack(anchor=tk.W, pady=(10, 0))

        preview_actions = ttk.Frame(preview_frame)
        preview_actions.pack(fill=tk.X, pady=(10, 0))
        self.retry_preview_button = ttk.Button(preview_actions, text="Retry Preview", command=self.retry_preview)
        self.retry_preview_button.pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(preview_actions, text="Previous Frame", command=lambda: self.step_preview(-1)).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(preview_actions, text="Next Frame", command=lambda: self.step_preview(1)).pack(side=tk.LEFT)
        self.retry_preview_button.state(["disabled"])

        lower_panel = ttk.Panedwindow(right_panel, orient=tk.VERTICAL)
        lower_panel.pack(fill=tk.BOTH, expand=True, pady=(12, 0))

        queue_frame = ttk.LabelFrame(lower_panel, text="Download Queue", padding=12)
        details_body = ttk.LabelFrame(lower_panel, text="Animation Details", padding=12)
        lower_panel.add(queue_frame, weight=1)
        lower_panel.add(details_body, weight=3)

        ttk.Label(queue_frame, textvariable=self.queue_status_var).pack(anchor=tk.W, pady=(0, 8))

        queue_buttons = ttk.Frame(queue_frame)
        queue_buttons.pack(fill=tk.X, pady=(0, 8))
        ttk.Button(queue_buttons, text="Copy Queue CLI Args", command=self.copy_queue_cli_args).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(queue_buttons, text="Export Queue JSON", command=self.export_queue_json).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(queue_buttons, text="Export Queue IDs", command=self.export_queue_ids).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(queue_buttons, text="Clear Queue", command=self.clear_queue).pack(side=tk.LEFT)

        queue_scrollbar = ttk.Scrollbar(queue_frame, orient=tk.VERTICAL)
        queue_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.queue_listbox = tk.Listbox(queue_frame, exportselection=False, yscrollcommand=queue_scrollbar.set, height=6)
        self.queue_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        queue_scrollbar.config(command=self.queue_listbox.yview)

        details_scrollbar = ttk.Scrollbar(details_body, orient=tk.VERTICAL)
        details_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.details_text = tk.Text(
            details_body,
            wrap=tk.WORD,
            yscrollcommand=details_scrollbar.set,
            height=20,
        )
        self.details_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.details_text.configure(state=tk.DISABLED)
        self.details_text.tag_configure(DETAILS_TAG_HIGHLIGHT, background="#fff3a1")
        details_scrollbar.config(command=self.details_text.yview)

        self.search_entry.focus_set()

    def bind_events(self) -> None:
        self.search_var.trace_add("write", self.on_filter_changed)
        self.sort_var.trace_add("write", self.on_filter_changed)
        self.animation_listbox.bind("<<ListboxSelect>>", self.on_listbox_select)
        self.animation_listbox.bind("<Double-Button-1>", lambda _event: self.copy_current_field("id"))
        self.root.bind("<Return>", self.on_copy_id_shortcut)
        self.root.bind("<Control-c>", self.on_copy_shortcut)
        self.root.bind("<Left>", self.on_left_right_shortcut)
        self.root.bind("<Right>", self.on_left_right_shortcut)

    def on_filter_changed(self, *_: Any) -> None:
        self.apply_filter()

    def apply_filter(self) -> None:
        previous_id = normalize_value(self.current_animation.get("id")) if self.current_animation else ""
        query = self.search_var.get().strip().lower()

        filtered = list(self.catalog)
        if query:
            filtered = [
                animation
                for animation in filtered
                if query in normalize_value(animation.get("name")).lower()
                or query in normalize_value(animation.get("description")).lower()
                or query in normalize_value(animation.get("id")).lower()
                or query in normalize_value(animation.get("motion_id")).lower()
            ]

        self.filtered_catalog = self.sort_animations(filtered)

        self.animation_listbox.delete(0, tk.END)
        self.current_displayed_ids = []
        for animation in self.filtered_catalog:
            summary = self.build_list_summary(animation, query)
            self.animation_listbox.insert(tk.END, summary)
            self.current_displayed_ids.append(normalize_value(animation.get("id")))

        duplicate_names = sum(1 for count in self.name_counts.values() if count > 1)
        self.selection_summary_var.set(
            f"Showing {len(self.filtered_catalog)} of {len(self.catalog)} animations | Duplicate names in catalog: {duplicate_names}"
        )

        if not self.filtered_catalog:
            self.clear_selection()
            return

        restore_index = 0
        if previous_id:
            for index, animation in enumerate(self.filtered_catalog):
                if normalize_value(animation.get("id")) == previous_id:
                    restore_index = index
                    break

        self.animation_listbox.selection_clear(0, tk.END)
        self.animation_listbox.selection_set(restore_index)
        self.animation_listbox.activate(restore_index)
        self.animation_listbox.see(restore_index)
        self.show_animation(self.filtered_catalog[restore_index])

    def sort_animations(self, animations: list[dict[str, Any]]) -> list[dict[str, Any]]:
        option = self.sort_var.get()
        if option == "Name (Z-A)":
            return sorted(
                animations,
                key=lambda animation: normalize_value(animation.get("name")).lower(),
                reverse=True,
            )
        if option == "Type":
            return sorted(
                animations,
                key=lambda animation: (
                    normalize_value(animation.get("type")).lower(),
                    normalize_value(animation.get("name")).lower(),
                ),
            )
        if option == "ID":
            return sorted(animations, key=lambda animation: normalize_value(animation.get("id")).lower())
        return sorted(animations, key=lambda animation: normalize_value(animation.get("name")).lower())

    def build_list_summary(self, animation: dict[str, Any], query: str) -> str:
        name = normalize_value(animation.get("name")) or "Unnamed Animation"
        description = normalize_value(animation.get("description"))
        source = normalize_value(animation.get("source")) or "unknown"
        animation_type = normalize_value(animation.get("type")) or "unknown"
        duplicate_count = self.name_counts.get(name.lower(), 0)

        summary = f"{name} | {animation_type} | {source}"
        if description:
            summary = f"{summary} - {description}"
        if duplicate_count > 1:
            summary = f"{summary} (duplicate name x{duplicate_count})"
        return highlight_matches_for_list(summary, query)

    def clear_selection(self) -> None:
        self.current_animation = None
        self.cancel_animation()
        self.preview_images = []
        self.preview_payload = None
        self.preview_frame_index = 0
        self.preview_label.configure(image="", text="No preview loaded")
        self.preview_status_var.set("No animations match the current filter.")
        self.retry_preview_button.state(["disabled"])
        self.name_var.set("No animation selected")
        self.id_var.set("")
        self.category_var.set("")
        self.description_var.set("")
        self.clipboard_status_var.set("")
        self.duplicate_status_var.set("")
        self.last_preview_sources = []
        self.set_details_text("")

    def on_listbox_select(self, _event: Any) -> None:
        selected = self.get_selected_animations()
        if not selected:
            return
        self.show_animation(selected[0])

    def get_selected_animations(self) -> list[dict[str, Any]]:
        return [self.filtered_catalog[index] for index in self.animation_listbox.curselection() if index < len(self.filtered_catalog)]

    def get_current_animation(self) -> dict[str, Any] | None:
        if self.current_animation is not None:
            return self.current_animation
        selected = self.get_selected_animations()
        return selected[0] if selected else None

    def show_animation(self, animation: dict[str, Any]) -> None:
        self.current_animation = animation
        self.clipboard_status_var.set("")

        name = normalize_value(animation.get("name")) or "Unnamed Animation"
        description = normalize_value(animation.get("description")) or "No description"
        animation_id = normalize_value(animation.get("id"))
        category = normalize_value(animation.get("category")) or "Uncategorized"
        character_type = normalize_value(animation.get("character_type")) or "Unknown character type"
        source = normalize_value(animation.get("source")) or "Unknown source"
        duplicate_count = self.name_counts.get(name.lower(), 0)

        self.name_var.set(name)
        self.id_var.set(f"ID: {animation_id}")
        self.category_var.set(
            f"Category: {category}    Character Type: {character_type}    Source: {source}"
        )
        self.description_var.set(description)
        self.duplicate_status_var.set(
            f"Duplicate name detected: {duplicate_count} entries share this name."
            if duplicate_count > 1
            else ""
        )

        summary_lines = [f"{label}: {value}" for label, value in non_empty_fields(animation)]
        summary_lines.append("")
        summary_lines.append("Raw JSON:")
        summary_lines.append(json.dumps(animation, indent=2, ensure_ascii=False, sort_keys=True))
        self.set_details_text("\n".join(summary_lines))
        self.load_preview_for_animation(animation)

    def set_details_text(self, content: str) -> None:
        self.details_text.configure(state=tk.NORMAL)
        self.details_text.delete("1.0", tk.END)
        self.details_text.insert("1.0", content)
        self.details_text.tag_remove(DETAILS_TAG_HIGHLIGHT, "1.0", tk.END)

        query = self.search_var.get().strip()
        if query:
            start = "1.0"
            while True:
                match_start = self.details_text.search(query, start, nocase=True, stopindex=tk.END)
                if not match_start:
                    break
                match_end = f"{match_start}+{len(query)}c"
                self.details_text.tag_add(DETAILS_TAG_HIGHLIGHT, match_start, match_end)
                start = match_end

        self.details_text.configure(state=tk.DISABLED)

    def copy_to_clipboard(self, value: str, status_message: str) -> None:
        self.root.clipboard_clear()
        self.root.clipboard_append(value)
        self.root.update_idletasks()
        self.clipboard_status_var.set(status_message)

    def copy_current_field(self, field_name: str) -> None:
        animation = self.get_current_animation()
        if animation is None:
            self.clipboard_status_var.set("Select an animation before copying.")
            return

        value = normalize_value(animation.get(field_name)).strip()
        if not value:
            self.clipboard_status_var.set(f"This animation does not have a {field_name} value.")
            return

        self.copy_to_clipboard(value, f"Copied {field_name} to clipboard.")

    def copy_current_json(self) -> None:
        animation = self.get_current_animation()
        if animation is None:
            self.clipboard_status_var.set("Select an animation before copying.")
            return
        payload = json.dumps(animation, indent=2, ensure_ascii=False, sort_keys=True)
        self.copy_to_clipboard(payload, "Copied animation JSON to clipboard.")

    def copy_current_cli_args(self) -> None:
        animation = self.get_current_animation()
        if animation is None:
            self.clipboard_status_var.set("Select an animation before copying.")
            return
        args = build_cli_args_for_animations([animation])
        if not args:
            self.clipboard_status_var.set("The selected animation does not have an ID.")
            return
        self.copy_to_clipboard(args, "Copied CLI arguments to clipboard.")

    def copy_selected_ids(self) -> None:
        selected = self.get_selected_animations()
        ids = [normalize_value(animation.get("id")).strip() for animation in selected]
        ids = [animation_id for animation_id in ids if animation_id]
        if not ids:
            self.clipboard_status_var.set("Select one or more animations with IDs first.")
            return
        self.copy_to_clipboard("\n".join(ids), f"Copied {len(ids)} animation IDs to clipboard.")

    def copy_selected_json(self) -> None:
        selected = self.get_selected_animations()
        if not selected:
            self.clipboard_status_var.set("Select one or more animations before copying.")
            return
        payload = json.dumps(selected, indent=2, ensure_ascii=False, sort_keys=True)
        self.copy_to_clipboard(payload, f"Copied {len(selected)} selected animations as JSON.")

    def copy_selected_cli_args(self) -> None:
        selected = self.get_selected_animations()
        args = build_cli_args_for_animations(selected)
        if not args:
            self.clipboard_status_var.set("Select one or more animations with IDs first.")
            return
        self.copy_to_clipboard(args, "Copied selected CLI arguments to clipboard.")

    def on_copy_id_shortcut(self, event: tk.Event[Any]) -> str | None:
        if self.is_text_input_widget(event.widget):
            return None
        self.copy_current_field("id")
        return "break"

    def on_copy_shortcut(self, event: tk.Event[Any]) -> str | None:
        if self.is_text_input_widget(event.widget):
            return None
        target = self.copy_target_var.get()
        if target == "Name":
            self.copy_current_field("name")
        elif target == "Motion ID":
            self.copy_current_field("motion_id")
        elif target == "Description":
            self.copy_current_field("description")
        elif target == "CLI Args":
            self.copy_current_cli_args()
        elif target == "JSON":
            self.copy_current_json()
        else:
            self.copy_current_field("id")
        return "break"

    def on_left_right_shortcut(self, event: tk.Event[Any]) -> str | None:
        if self.is_text_input_widget(event.widget):
            return None
        if event.keysym == "Left":
            self.move_selection(-1)
        elif event.keysym == "Right":
            self.move_selection(1)
        return "break"

    def is_text_input_widget(self, widget: Any) -> bool:
        return isinstance(widget, (tk.Entry, tk.Text, ttk.Entry, ttk.Combobox))

    def move_selection(self, step: int) -> None:
        if not self.filtered_catalog:
            return

        current_indices = self.animation_listbox.curselection()
        current_index = current_indices[0] if current_indices else 0
        next_index = max(0, min(len(self.filtered_catalog) - 1, current_index + step))
        self.animation_listbox.selection_clear(0, tk.END)
        self.animation_listbox.selection_set(next_index)
        self.animation_listbox.activate(next_index)
        self.animation_listbox.see(next_index)
        self.show_animation(self.filtered_catalog[next_index])

    def select_all_filtered(self) -> None:
        if not self.filtered_catalog:
            return
        self.animation_listbox.selection_set(0, tk.END)
        self.animation_listbox.activate(0)
        self.show_animation(self.filtered_catalog[0])

    def clear_listbox_selection(self) -> None:
        self.animation_listbox.selection_clear(0, tk.END)
        if self.filtered_catalog:
            self.animation_listbox.selection_set(0)
            self.show_animation(self.filtered_catalog[0])

    def queue_selected_animations(self) -> None:
        selected = self.get_selected_animations()
        if not selected:
            self.queue_status_var.set("Select one or more animations before adding them to the queue.")
            return

        added_count = 0
        for animation in selected:
            animation_id = normalize_value(animation.get("id")).strip()
            if animation_id and animation_id not in self.queue_ids:
                self.queue_ids.append(animation_id)
                added_count += 1

        self.refresh_queue_listbox()
        self.queue_status_var.set(
            f"Queue contains {len(self.queue_ids)} animations. Added {added_count} new items."
        )

    def refresh_queue_listbox(self) -> None:
        self.queue_listbox.delete(0, tk.END)
        for animation_id in self.queue_ids:
            animation = self.animation_by_id.get(animation_id)
            if animation is None:
                self.queue_listbox.insert(tk.END, animation_id)
                continue
            name = normalize_value(animation.get("name")) or animation_id
            self.queue_listbox.insert(tk.END, f"{name} ({animation_id})")

    def clear_queue(self) -> None:
        self.queue_ids.clear()
        self.refresh_queue_listbox()
        self.queue_status_var.set("Queue is empty.")

    def queue_animations(self) -> list[dict[str, Any]]:
        return [self.animation_by_id[animation_id] for animation_id in self.queue_ids if animation_id in self.animation_by_id]

    def export_json_payload(self, payload: Any, default_name: str) -> None:
        destination = filedialog.asksaveasfilename(
            title="Export JSON",
            defaultextension=".json",
            initialfile=default_name,
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not destination:
            return
        Path(destination).write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")

    def export_lines(self, lines: list[str], default_name: str) -> None:
        destination = filedialog.asksaveasfilename(
            title="Export text",
            defaultextension=".txt",
            initialfile=default_name,
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if not destination:
            return
        Path(destination).write_text("\n".join(lines), encoding="utf-8")

    def export_selected_json(self) -> None:
        selected = self.get_selected_animations()
        if not selected:
            self.queue_status_var.set("Select one or more animations before exporting.")
            return
        self.export_json_payload(selected, "selected_animations.json")

    def export_selected_ids(self) -> None:
        selected = self.get_selected_animations()
        ids = [normalize_value(animation.get("id")).strip() for animation in selected]
        ids = [animation_id for animation_id in ids if animation_id]
        if not ids:
            self.queue_status_var.set("Select one or more animations with IDs before exporting.")
            return
        self.export_lines(ids, "selected_animation_ids.txt")

    def export_queue_json(self) -> None:
        queued = self.queue_animations()
        if not queued:
            self.queue_status_var.set("Queue is empty.")
            return
        self.export_json_payload(queued, "queued_animations.json")

    def export_queue_ids(self) -> None:
        if not self.queue_ids:
            self.queue_status_var.set("Queue is empty.")
            return
        self.export_lines(self.queue_ids, "queued_animation_ids.txt")

    def copy_queue_cli_args(self) -> None:
        queued = self.queue_animations()
        args = build_cli_args_for_animations(queued)
        if not args:
            self.queue_status_var.set("Queue is empty or does not contain valid IDs.")
            return
        self.copy_to_clipboard(args, "Copied queue CLI arguments to clipboard.")

    def open_current_in_mixamo(self) -> None:
        animation = self.get_current_animation()
        if animation is None:
            self.clipboard_status_var.set("Select an animation before opening Mixamo.")
            return
        webbrowser.open_new_tab(build_mixamo_url(animation))
        self.clipboard_status_var.set("Opened Mixamo search for the selected animation.")

    def load_preview_for_animation(self, animation: dict[str, Any]) -> None:
        self.cancel_animation()
        self.preview_images = []
        self.preview_payload = None
        self.preview_frame_index = 0
        self.preview_label.configure(image="", text="Loading preview...")
        self.retry_preview_button.state(["disabled"])

        sources = build_preview_sources(animation)
        self.last_preview_sources = sources
        if not sources:
            self.preview_status_var.set("No preview URL found for this animation.")
            self.preview_label.configure(text="No preview available")
            return

        self.preview_request_id += 1
        request_id = self.preview_request_id
        self.preview_status_var.set(f"Loading preview from {sources[0]}")

        cached_payload = self.get_cached_payload(sources)
        if cached_payload is not None:
            self.apply_preview_payload(request_id, cached_payload)
            return

        def worker() -> None:
            try:
                payload = self.fetch_preview_payload(sources)
                self.root.after(0, lambda: self.apply_preview_payload(request_id, payload))
            except Exception as exc:
                self.root.after(0, lambda: self.show_preview_error(request_id, str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def retry_preview(self) -> None:
        animation = self.get_current_animation()
        if animation is None:
            return
        self.load_preview_for_animation(animation)

    def get_cached_payload(self, sources: list[str]) -> PreviewPayload | None:
        for source in sources:
            if source in self.preview_cache:
                return self.preview_cache[source]
        return None

    def fetch_preview_payload(self, sources: list[str]) -> PreviewPayload:
        last_error: Exception | None = None
        for source in sources:
            if source in self.preview_cache:
                return self.preview_cache[source]
            try:
                payload = load_preview_payload(source)
                self.preview_cache[source] = payload
                return payload
            except Exception as exc:
                last_error = exc

        if last_error is None:
            raise RuntimeError("No preview sources were available.")
        raise last_error

    def apply_preview_payload(self, request_id: int, payload: PreviewPayload) -> None:
        if request_id != self.preview_request_id:
            return

        self.cancel_animation()
        self.preview_payload = payload
        self.preview_images = [ImageTk.PhotoImage(frame) for frame in payload.frames]
        self.preview_frame_index = 0
        self.retry_preview_button.state(["disabled"])

        self.preview_label.configure(image=self.preview_images[0], text="")
        self.preview_status_var.set(f"Preview source: {payload.source}")

        if len(self.preview_images) > 1:
            self.animate_preview(0, payload.delays_ms)

    def animate_preview(self, frame_index: int, delays_ms: list[int]) -> None:
        if not self.preview_images:
            return

        self.preview_label.configure(image=self.preview_images[frame_index], text="")
        self.preview_frame_index = frame_index
        next_index = (frame_index + 1) % len(self.preview_images)
        delay_ms = delays_ms[frame_index] if frame_index < len(delays_ms) else 100
        self.animation_after_id = self.root.after(
            delay_ms,
            self.animate_preview,
            next_index,
            delays_ms,
        )

    def step_preview(self, step: int) -> None:
        if not self.preview_images:
            return
        self.cancel_animation()
        self.preview_frame_index = (self.preview_frame_index + step) % len(self.preview_images)
        self.preview_label.configure(image=self.preview_images[self.preview_frame_index], text="")

    def cancel_animation(self) -> None:
        if self.animation_after_id is not None:
            self.root.after_cancel(self.animation_after_id)
            self.animation_after_id = None

    def show_preview_error(self, request_id: int, error_message: str) -> None:
        if request_id != self.preview_request_id:
            return

        self.cancel_animation()
        self.preview_images = []
        self.preview_payload = None
        self.preview_label.configure(image="", text="Preview unavailable")
        self.preview_status_var.set(f"Failed to load preview: {error_message}")
        self.retry_preview_button.state(["!disabled"])


def main() -> None:
    args = parse_args()

    try:
        catalog = load_catalog(args.catalog)
    except Exception as exc:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Mixamo Animation Viewer", str(exc))
        root.destroy()
        raise SystemExit(1) from exc

    root = tk.Tk()
    AnimationViewer(root, catalog, args.catalog.resolve())
    root.mainloop()


if __name__ == "__main__":
    main()