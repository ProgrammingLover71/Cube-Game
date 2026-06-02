"""File management and level transitions for the level editor."""

import json
import tkinter as tk
from os import mkdir
from pathlib import Path
from tkinter import messagebox


class FileManager:
    """Handles file I/O, level loading/saving, and state transitions."""

    def __init__(self, state):
        self.state = state

    def save_level(self):
        """Save the current level to disk."""
        self.state.level_path.parent.mkdir(parents=True, exist_ok=True)
        data = dict(self.state.metadata)

        normalized_blocks = []
        for block in self.state.blocks:
            normalized = self.state.blocks_mgr.normalize_block(block)
            if normalized is not None:
                normalized_blocks.append(normalized)

        data["blocks"] = normalized_blocks
        with open(self.state.level_path, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=2)

        self.state.message = f"Saved {self.state.level_path}"
        self.state.message_timer = 2.0

    def start_playtest(self):
        """Start a playtest of the current level."""
        self.save_level()
        try:
            from game_state.state import GameState
            self.state.manager.change(GameState(self.state.level_path, True))
        except Exception as exc:
            self.state.message = f"Playtest failed: {exc}"
            self.state.message_timer = 3.0

    def open_level(self):
        """Open the level select screen."""
        self.save_level()
        from level_select_state import LevelSelectState
        self.state.manager.change(LevelSelectState(self.state.level_path.parent, True))

    def new_level(self):
        """Create a new level."""
        self.save_level()
        # Create a new level path with an incremented name
        base_name = "Unnamed Level"
        counter = 1
        while (self.state.level_path.parent / f"{base_name} {counter}.json").exists():
            counter += 1
        level_name = f"{base_name} {counter}"
        level_path = Path("levels") / level_name / "level.json"
        mkdir(level_path.parent)
        level_path.touch(exist_ok=True)
        from level_editor import LevelEditorState
        self.state.manager.change(LevelEditorState(level_path))

    def delete_level(self):
        """Delete the current level."""
        level_name = self.state.level_path.parent.name or self.state.level_path.stem

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)

        confirmed = messagebox.askyesno(
            title="Delete Level",
            message=f'Are you sure you want to delete "{level_name}"? This action CANNOT be undone.',
            icon=messagebox.WARNING,
        )
        root.destroy()

        if not confirmed:
            return

        if self.state.level_path.exists():
            self.state.level_path.unlink()
            parent = self.state.level_path.parent
            if parent.exists() and parent.is_dir():
                try:
                    parent.rmdir()
                except OSError:
                    pass

        from level_editor import LevelEditorState
        self.state.manager.change(LevelEditorState(self.state.default_level_path))

    def open_options(self):
        """Open the level options screen."""
        self.save_level()
        from level_editor.options import LevelOptionsState
        self.state.manager.change(LevelOptionsState(self.state))
