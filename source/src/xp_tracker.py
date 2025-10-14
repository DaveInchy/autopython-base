import time
import threading
from datetime import timedelta
import os
from .game_screen import GameScreen
from .runelite_api import RuneLiteAPI

class XPTracker:
    def __init__(self, skill_name='MAGIC'):
        self.ocr = GameScreen()
        self.runelite = RuneLiteAPI()
        self.skill_name = skill_name.upper()
        self.using_runelite = False
        
        self.start_xp = None
        self.current_xp = None
        self.last_update = None
        self.xp_per_hour = 0
        self.xp_gained = 0
        self.stop_event = threading.Event()
        
        # Runtime tracking
        self.start_time = None
        self.total_runtime = timedelta()
        
        # XP validation
        self.last_valid_xp = None
        self.max_xp_change_per_second = 100  # Maximum reasonable XP change per second
        self.consecutive_invalid_reads = 0
        self.max_consecutive_invalid_reads = 5  # Reset last_valid_xp after this many invalid reads
        
        # Moving average for XP/hour calculation
        self.xp_history = []  # List of (timestamp, xp) tuples
        self.history_window = 300  # 5 minutes of history for calculating xp/hour
        
        # Try to connect to RuneLite
        self._check_runelite_availability()
        
        # XP table for levels 1-99
        self.xp_table = {
            1: 0, 2: 83, 3: 174, 4: 276, 5: 388, 6: 512, 7: 650, 8: 801, 9: 969, 10: 1154,
            11: 1358, 12: 1584, 13: 1833, 14: 2107, 15: 2411, 16: 2746, 17: 3115, 18: 3523,
            19: 3973, 20: 4470, 21: 5018, 22: 5624, 23: 6291, 24: 7028, 25: 7842, 26: 8740,
            27: 9730, 28: 10824, 29: 12031, 30: 13363, 31: 14833, 32: 16456, 33: 18247,
            34: 20224, 35: 22406, 36: 24815, 37: 27473, 38: 30408, 39: 33648, 40: 37224,
            41: 41171, 42: 45529, 43: 50339, 44: 55649, 45: 61512, 46: 67983, 47: 75127,
            48: 83014, 49: 91721, 50: 101333, 51: 111945, 52: 123660, 53: 136594, 54: 150872,
            55: 166636, 56: 184040, 57: 203254, 58: 224466, 59: 247886, 60: 273742, 61: 302288,
            62: 333804, 63: 368599, 64: 407015, 65: 449428, 66: 496254, 67: 547953, 68: 605032,
            69: 668051, 70: 737627, 71: 814445, 72: 899257, 73: 992895, 74: 1096278, 75: 1210421,
            76: 1336443, 77: 1475581, 78: 1629200, 79: 1798808, 80: 1986068, 81: 2192818,
            82: 2421087, 83: 2673114, 84: 2951373, 85: 3258594, 86: 3597792, 87: 3972294,
            88: 4385776, 89: 4842295, 90: 5346332, 91: 5902831, 92: 6517253, 93: 7195629,
            94: 7944614, 95: 8771558, 96: 9684577, 97: 10692629, 98: 11805606, 99: 13034431
        }

    def _check_runelite_availability(self):
        """Check if RuneLite API is available"""
        try:
            if self.runelite.is_logged_in():
                self.using_runelite = True
                return True
        except:
            self.using_runelite = False
        return False

    def get_xp(self):
        """Get XP value, trying RuneLite first, falling back to OCR"""
        # Try RuneLite API first
        if self.using_runelite:
            try:
                xp = self.runelite.get_skill_xp(self.skill_name)
                print(f"RuneLite API returned XP: {xp}")
                if xp is not None:
                    return xp
                # If we failed to get XP, check if RuneLite is still available
                self._check_runelite_availability()
            except:
                self.using_runelite = False
        
        # Fallback to OCR if RuneLite is not available
        if not self.using_runelite:
            try:
                # Capture and read XP from the specified coordinates (1571, 35) to (1658, 48)
                xp_text = self.ocr.read_region(1571, 35, 1658, 48)
                if xp_text:
                    return int(xp_text.replace(',', ''))
            except Exception as e:
                print(f"\rError reading XP: {str(e)}", end='')
        
        print("get_xp is returning None")
        return None

    def get_level_for_xp(self, xp):
        """Get the level for a given XP amount"""
        for level in range(99, 0, -1):
            if xp >= self.xp_table[level]:
                return level
        return 1

    def get_progress_to_next_level(self, xp):
        """Calculate progress to next level"""
        current_level = self.get_level_for_xp(xp)
        if current_level >= 99:
            return 100, 0, 0
        
        current_level_xp = self.xp_table[current_level]
        next_level_xp = self.xp_table[current_level + 1]
        xp_needed = next_level_xp - current_level_xp
        xp_gained = xp - current_level_xp
        
        progress = (xp_gained / xp_needed) * 100
        remaining_xp = next_level_xp - xp
        
        return progress, remaining_xp, current_level + 1

    def create_progress_bar(self, progress, width=50):
        """Create ASCII progress bar"""
        filled = int(width * progress / 100)
        bar = '█' * filled + '░' * (width - filled)
        return f'[{bar}] {progress:.2f}%'

    def format_time(self, seconds):
        """Format time in seconds to HH:MM:SS"""
        return str(timedelta(seconds=int(seconds)))

    def format_runtime(self):
        """Format total runtime in days, hours, minutes, seconds"""
        if not self.total_runtime:
            return "00:00:00"
        
        days = self.total_runtime.days
        hours = self.total_runtime.seconds // 3600
        minutes = (self.total_runtime.seconds % 3600) // 60
        seconds = self.total_runtime.seconds % 60
        
        if days > 0:
            return f"{days}d {hours:02d}:{minutes:02d}:{seconds:02d}"
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def validate_xp_reading(self, new_xp, current_time):
        """Validate XP reading and return True if valid, False if invalid"""
        print(f"Validating XP reading: {new_xp}")
        if new_xp is None:
            self.consecutive_invalid_reads += 1
            return False
            
        if self.last_valid_xp is None:
            self.last_valid_xp = new_xp
            self.consecutive_invalid_reads = 0
            return True
            
        # Calculate time since last valid reading
        time_diff = current_time - (self.last_update or current_time)
        if time_diff <= 0:
            time_diff = 0.1  # Avoid division by zero
            
        # Calculate maximum allowed XP change for this time period
        max_allowed_change = self.max_xp_change_per_second * time_diff
        actual_change = abs(new_xp - self.last_valid_xp)
        
        if actual_change <= max_allowed_change:
            self.last_valid_xp = new_xp
            self.consecutive_invalid_reads = 0
            return True
        
        self.consecutive_invalid_reads += 1
        if self.consecutive_invalid_reads >= self.max_consecutive_invalid_reads:
            # Reset last_valid_xp after too many invalid reads
            # This helps recover from persistent misreads
            self.last_valid_xp = new_xp
            self.consecutive_invalid_reads = 0
            return True
            
        return False
        
    def update_xp_history(self, current_time, xp):
        """Update XP history and calculate XP/hour using moving average"""
        # Add new data point
        self.xp_history.append((current_time, xp))
        
        # Remove old data points outside our window
        cutoff_time = current_time - self.history_window
        self.xp_history = [(t, x) for t, x in self.xp_history if t >= cutoff_time]
        
        # Calculate XP/hour if we have enough history
        if len(self.xp_history) >= 2:
            oldest_time, oldest_xp = self.xp_history[0]
            newest_time, newest_xp = self.xp_history[-1]
            time_diff = newest_time - oldest_time
            
            if time_diff > 0:
                xp_diff = newest_xp - oldest_xp
                # Calculate hourly rate based on the window
                self.xp_per_hour = (xp_diff / time_diff) * 3600

    def update_display(self):
        """Update the terminal display"""
        os.system('cls' if os.name == 'nt' else 'clear')
        print("--- XP TRACKER UPDATE ---")
        
        if not self.current_xp:
            print("\nWaiting for XP reading...")
            return

        current_level = self.get_level_for_xp(self.current_xp)
        progress, remaining_xp, next_level = self.get_progress_to_next_level(self.current_xp)
        
        # Calculate time remaining for next level
        time_remaining = "∞"
        if self.xp_per_hour > 0:
            time_remaining = self.format_time(remaining_xp / (self.xp_per_hour / 3600))

        # Create header
        print("\n" + "=" * 60)
        print(f"{'XP TRACKER':^60}")
        print("=" * 60 + "\n")

        # Runtime and Level information
        print(f"Runtime: {self.format_runtime()}")
        print(f"Current Level: {current_level:>3}  │  Next Level: {next_level:>3}")
        print(f"Current XP: {self.current_xp:,}")
        print(f"XP Gained: {self.xp_gained:,}")
        print(f"XP/Hour: {int(self.xp_per_hour):,}")
        print(f"\nProgress to Level {next_level}:")
        print(self.create_progress_bar(progress))
        print(f"XP Remaining: {remaining_xp:,}")
        print(f"Time to Next Level: {time_remaining}")
        
        # Debug area at the bottom
        print("\n" + "-" * 60)
        print("Bot Status:")
        print("-" * 60)

    def run(self):
        """Main loop"""
        try:
            self.start_time = time.time()
            last_display_update = 0
            display_interval = 0.4  # Update display every 0.4 seconds
            
            while not self.stop_event.is_set():
                current_time = time.time()
                self.total_runtime = timedelta(seconds=int(current_time - self.start_time))
                
                xp = self.get_xp()
                if self.validate_xp_reading(xp, current_time):
                    if self.start_xp is None:
                        self.start_xp = xp
                        self.last_update = current_time
                    
                    self.current_xp = xp
                    self.xp_gained = xp - self.start_xp
                    
                    # Update XP history and calculate XP/hour
                    self.update_xp_history(current_time, xp)
                    
                    # Update display if enough time has passed
                    if current_time - last_display_update >= display_interval:
                        self.update_display()
                        last_display_update = current_time
                    
                    self.last_update = current_time
                
                time.sleep(0.1)  # Small delay to prevent high CPU usage
                
        except Exception as e:
            print(f"An error occurred in XP Tracker: {e}")
            import traceback
            traceback.print_exc()
        finally:
            print("\nXP Tracker stopped.")
