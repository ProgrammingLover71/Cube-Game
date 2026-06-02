import pygame as pg
from pathlib import Path
import shutil
from tkinter import filedialog, Tk


class LevelOptionsState:
    """State for editing level metadata (difficulty, songs, etc.)"""
    
    SCREEN_W = 1280
    SCREEN_H = 720
    
    def __init__(self, level_editor_state):
        self.level_editor_state = level_editor_state
        self.metadata = level_editor_state.metadata.copy()
        self.difficulty = self.metadata.get("difficulty", 1)
        
        # Check if song.mp3 exists in level folder
        level_dir = Path(level_editor_state.level_path).parent
        song_file = level_dir / "song.mp3"
        self.song_filename = "song.mp3" if song_file.exists() else ""
        
        # Track all available songs for this level
        self.songs = []
        if song_file.exists():
            self.songs.append(str(song_file))
    
    def enter(self, manager):
        self.manager = manager
        self.font = pg.font.SysFont(None, 32)
        self.font_small = pg.font.SysFont(None, 24)
        self.font_title = pg.font.SysFont(None, 48)
    
    def handle_event(self, event):
        if event.type == pg.KEYDOWN:
            if event.key == pg.K_ESCAPE:
                # Go back without saving
                self.manager.change(self.level_editor_state)
            elif event.key == pg.K_RETURN:
                # Save and go back
                self.save_and_exit()
            elif event.key == pg.K_UP:
                self.difficulty = min(10, self.difficulty + 1)
            elif event.key == pg.K_DOWN:
                self.difficulty = max(1, self.difficulty - 1)
        
        elif event.type == pg.MOUSEBUTTONDOWN:
            if event.button == 1:
                # Check button clicks
                if self.difficulty_up_rect().collidepoint(event.pos):
                    self.difficulty = min(10, self.difficulty + 1)
                elif self.difficulty_down_rect().collidepoint(event.pos):
                    self.difficulty = max(1, self.difficulty - 1)
                elif self.save_button_rect().collidepoint(event.pos):
                    self.save_and_exit()
                elif self.cancel_button_rect().collidepoint(event.pos):
                    self.manager.change(self.level_editor_state)
                elif self.browse_song_rect().collidepoint(event.pos):
                    self.browse_song()
    
    def update(self, dt):
        pass
    
    def render(self, surface):
        surface.fill((30, 30, 40))
        
        # Title
        title = self.font_title.render("Level Options", True, (255, 255, 255))
        surface.blit(title, title.get_rect(center=(self.SCREEN_W // 2, 60)))
        
        # Difficulty section
        self.render_difficulty_section(surface)
        
        # Song section
        self.render_song_section(surface)
        
        # Buttons
        self.render_buttons(surface)
    
    def render_difficulty_section(self, surface):
        y = 180
        
        # Label
        label = self.font.render("Difficulty:", True, (200, 200, 200))
        surface.blit(label, (100, y))
        
        # Value display
        value_text = self.font.render(str(self.difficulty), True, (255, 200, 100))
        surface.blit(value_text, (400, y))
        
        # Down button
        down_rect = self.difficulty_down_rect()
        pg.draw.rect(surface, (60, 60, 100), down_rect, border_radius=6)
        pg.draw.rect(surface, (120, 120, 180), down_rect, width=2, border_radius=6)
        down_text = self.font_small.render("-", True, (255, 255, 255))
        surface.blit(down_text, down_text.get_rect(center=down_rect.center))
        
        # Up button
        up_rect = self.difficulty_up_rect()
        pg.draw.rect(surface, (60, 60, 100), up_rect, border_radius=6)
        pg.draw.rect(surface, (120, 120, 180), up_rect, width=2, border_radius=6)
        up_text = self.font_small.render("+", True, (255, 255, 255))
        surface.blit(up_text, up_text.get_rect(center=up_rect.center))
        
        # Difficulty scale bar
        scale_y = y + 50
        pg.draw.line(surface, (100, 100, 150), (100, scale_y), (500, scale_y), 3)
        marker_x = 100 + (self.difficulty - 1) * (400 / 9)
        pg.draw.circle(surface, (255, 200, 100), (int(marker_x), scale_y), 6)
    
    def render_song_section(self, surface):
        y = 320
        
        # Label
        label = self.font.render("Song:", True, (200, 200, 200))
        surface.blit(label, (100, y))
        
        # Song display
        display_text = self.song_filename if self.song_filename else "(None)"
        song_text = self.font_small.render(display_text, True, (150, 200, 255))
        surface.blit(song_text, (400, y))
        
        # Browse button
        browse_rect = self.browse_song_rect()
        pg.draw.rect(surface, (60, 100, 60), browse_rect, border_radius=6)
        pg.draw.rect(surface, (120, 180, 120), browse_rect, width=2, border_radius=6)
        browse_text = self.font_small.render("Browse", True, (255, 255, 255))
        surface.blit(browse_text, browse_text.get_rect(center=browse_rect.center))
    
    def render_buttons(self, surface):
        # Save button
        save_rect = self.save_button_rect()
        pg.draw.rect(surface, (40, 160, 60), save_rect, border_radius=8)
        pg.draw.rect(surface, (80, 220, 100), save_rect, width=2, border_radius=8)
        save_text = self.font.render("Save", True, (255, 255, 255))
        surface.blit(save_text, save_text.get_rect(center=save_rect.center))
        
        # Cancel button
        cancel_rect = self.cancel_button_rect()
        pg.draw.rect(surface, (160, 40, 60), cancel_rect, border_radius=8)
        pg.draw.rect(surface, (220, 80, 100), cancel_rect, width=2, border_radius=8)
        cancel_text = self.font.render("Cancel", True, (255, 255, 255))
        surface.blit(cancel_text, cancel_text.get_rect(center=cancel_rect.center))
        
        # Help text
        help_text = self.font_small.render("Up Arrow, Down Arrow - Adjust Difficulty | Enter - Save | Escape - Cancel", True, (150, 150, 150))
        surface.blit(help_text, (self.SCREEN_W // 2 - help_text.get_width() // 2, self.SCREEN_H - 40))
    
    def difficulty_up_rect(self):
        return pg.Rect(500, 180, 60, 40)
    
    def difficulty_down_rect(self):
        return pg.Rect(570, 180, 60, 40)
    
    def browse_song_rect(self):
        return pg.Rect(400, 320, 100, 40)
    
    def save_button_rect(self):
        return pg.Rect(350, 450, 200, 60)
    
    def cancel_button_rect(self):
        return pg.Rect(700, 450, 200, 60)
    
    def save_and_exit(self):
        """Save metadata and return to level editor"""
        # Only save difficulty to match Fantasy format
        self.metadata["difficulty"] = self.difficulty
        # Don't save song to metadata - it's auto-detected as song.mp3 in the folder
        self.level_editor_state.metadata = self.metadata
        self.level_editor_state.save_level()
        self.manager.change(self.level_editor_state)
    
    def browse_song(self):
        """Open file browser to select a song file and copy it as song.mp3 to level folder and songs folder"""
        # Hide pygame window and show file dialog
        root = Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        
        file_path = filedialog.askopenfilename(
            title="Select a song file",
            filetypes=[("Audio files", "*.mp3 *.wav *.ogg *.flac"), ("All files", "*.*")]
        )
        root.destroy()
        
        if file_path:
            # Get level folder
            level_folder = Path(self.level_editor_state.level_path).parent
            song_path = level_folder / "song.mp3"
            
            # Get workspace root (parent of src folder)
            workspace_root = Path(__file__).parent.parent
            songs_folder = workspace_root / "songs"
            songs_folder.mkdir(exist_ok=True)
            
            try:
                # Delete old song.mp3 if it exists
                if song_path.exists():
                    song_path.unlink()
                
                # Copy selected file as song.mp3 to level folder
                src = Path(file_path)
                shutil.copy2(src, song_path)
                self.song_filename = "song.mp3"
                
                # Also copy to songs folder with original filename
                song_dest = songs_folder / src.name
                shutil.copy2(src, song_dest)
                
                # Add to songs list if not already there
                song_str = str(song_dest)
                if song_str not in self.songs:
                    self.songs.append(song_str)
            except Exception as e:
                print(f"Error copying song: {e}")
