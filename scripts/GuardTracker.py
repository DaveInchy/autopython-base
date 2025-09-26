import tkinter as tk
from tkinter import ttk
import time
from osrs_macro_sdk.api import RuneLiteAPI
from osrs_macro_sdk.game_state import GameState
from osrs_macro_sdk.game_state.guard_tracking import GuardTracker, BoundaryArea

class GuardTrackerUI:
    def __init__(self, guard_tracker: GuardTracker):
        self.tracker = guard_tracker
        
        # Create main window
        self.root = tk.Tk()
        self.root.title("Guard Tracker")
        self.root.attributes('-topmost', True)  # Keep window on top
        self.root.geometry("300x400")
        
        # Create widgets
        self.create_widgets()
        
        # Update timer
        self.root.after(1000, self.update)
        
    def create_widgets(self):
        # Status frame
        status_frame = ttk.LabelFrame(self.root, text="Status")
        status_frame.pack(fill="x", padx=5, pady=5)
        
        self.boundary_status = ttk.Label(status_frame, text="Boundary: Not Set")
        self.boundary_status.pack(anchor="w", padx=5)
        
        self.player_status = ttk.Label(status_frame, text="Player: Unknown")
        self.player_status.pack(anchor="w", padx=5)
        
        # Guard info frame
        guard_frame = ttk.LabelFrame(self.root, text="Guard Information")
        guard_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.guard_list = ttk.Treeview(
            guard_frame, 
            columns=("distance", "combat"),
            height=8
        )
        self.guard_list.heading("distance", text="Distance")
        self.guard_list.heading("combat", text="Combat")
        self.guard_list.column("#0", width=120)  # Name column
        self.guard_list.column("distance", width=70)
        self.guard_list.column("combat", width=70)
        self.guard_list.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Threat gauge
        threat_frame = ttk.LabelFrame(self.root, text="Threat Level")
        threat_frame.pack(fill="x", padx=5, pady=5)
        
        self.threat_bar = ttk.Progressbar(
            threat_frame,
            orient="horizontal",
            mode="determinate"
        )
        self.threat_bar.pack(fill="x", padx=5, pady=5)
        
        # Control buttons
        control_frame = ttk.Frame(self.root)
        control_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Button(
            control_frame,
            text="Set Boundary Here",
            command=self.set_boundary
        ).pack(side="left", padx=5)
        
        ttk.Button(
            control_frame,
            text="Find Safe Spot",
            command=self.show_safe_spots
        ).pack(side="left", padx=5)
        
    def set_boundary(self):
        if self.tracker.set_boundary_from_current_location(radius=20):
            self.boundary_status.config(text="Boundary: Set (20 tile radius)")
        
    def show_safe_spots(self):
        safe_spots = self.tracker.get_safe_spots()
        if safe_spots:
            spots_text = "\n".join(
                f"({spot.x}, {spot.y})" for spot in safe_spots[:5]
            )
            tk.messagebox.showinfo(
                "Safe Spots",
                f"Found {len(safe_spots)} safe spots. Top 5:\n{spots_text}"
            )
        else:
            tk.messagebox.showinfo(
                "Safe Spots",
                "No safe spots found! Try moving to a different area."
            )
        
    def update(self):
        try:
            # Update player status
            loc = self.tracker.game_state.get_player_location()
            if loc:
                within = self.tracker.is_within_boundary()
                status = "OK" if within else "OUTSIDE BOUNDARY!"
                self.player_status.config(
                    text=f"Player: ({loc.x}, {loc.y}) - {status}",
                    foreground="green" if within else "red"
                )
            
            # Update guard list
            self.guard_list.delete(*self.guard_list.get_children())
            for guard in self.tracker.get_nearby_guards():
                self.guard_list.insert(
                    "",
                    "end",
                    text=guard.name,
                    values=(
                        f"{guard.distance:.1f}",
                        guard.combat_level
                    )
                )
                
            # Update threat level
            threat = self.tracker.get_guard_threat_level()
            self.threat_bar["value"] = threat * 100
            
            # Color code threat bar
            if threat < 0.3:
                self.threat_bar["style"] = "green.Horizontal.TProgressbar"
            elif threat < 0.7:
                self.threat_bar["style"] = "yellow.Horizontal.TProgressbar"
            else:
                self.threat_bar["style"] = "red.Horizontal.TProgressbar"
                
        except Exception as e:
            print(f"Error updating UI: {e}")
            
        finally:
            # Schedule next update
            self.root.after(1000, self.update)
            
    def run(self):
        # Create progress bar styles
        style = ttk.Style()
        style.configure(
            "green.Horizontal.TProgressbar",
            background="green"
        )
        style.configure(
            "yellow.Horizontal.TProgressbar",
            background="yellow"
        )
        style.configure(
            "red.Horizontal.TProgressbar",
            background="red"
        )
        
        self.root.mainloop()

def main():
    # Initialize API and tracker
    api = RuneLiteAPI()
    tracker = GuardTracker(api)
    
    # Create and run UI
    ui = GuardTrackerUI(tracker)
    ui.run()

if __name__ == "__main__":
    main()
