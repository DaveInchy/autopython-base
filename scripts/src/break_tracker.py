import time
import random
from .xp_tracker import XPTracker
from .client_window import RuneLiteClientWindow

class BreakManager:
	def __init__(self, script_queue=None, skill_name='MAGIC', min_play=900, max_play=3600, min_break=300, max_break=1200, xp_bias=100):
		"""
		script_queue: list of (callable, args, kwargs) tuples
		skill_name: skill to track for XP bias
		min_play, max_play: min/max play session length in seconds
		min_break, max_break: min/max break length in seconds
		xp_bias: if XP to next level is less than this, delay break
		"""
		self.script_queue = script_queue or []
		self.skill_name = skill_name
		self.min_play = min_play
		self.max_play = max_play
		self.min_break = min_break
		self.max_break = max_break
		self.xp_bias = xp_bias
		self.xp_tracker = XPTracker(skill_name=skill_name)
		self.client = RuneLiteClientWindow()
		self.running = False

	def add_script(self, func, *args, **kwargs):
		self.script_queue.append((func, args, kwargs))

	def _should_break(self):
		# Bias: if close to level, keep playing
		xp = self.xp_tracker.get_xp()
		if xp is None:
			return True  # If can't read XP, err on side of break
		_, remaining_xp, _ = self.xp_tracker.get_progress_to_next_level(xp)
		if remaining_xp < self.xp_bias:
			return False  # Too close to level, keep going
		return True

	def _random_play_time(self):
		return random.randint(self.min_play, self.max_play)

	def _random_break_time(self):
		return random.randint(self.min_break, self.max_break)

	def run(self):
		self.running = True
		while self.running:
			# Login if not already
			if not self.client.is_logged_in():
				print("[BreakManager] Logging in...")
				# self.client.secure_login(username, password)  # Implement as needed
				print("[BreakManager] (Stub) Please log in manually.")
				while not self.client.is_logged_in():
					time.sleep(5)
			# Play session
			play_time = self._random_play_time()
			print(f"[BreakManager] Starting play session for {play_time//60}m {play_time%60}s.")
			session_start = time.time()
			while time.time() - session_start < play_time:
				if not self.script_queue:
					print("[BreakManager] No scripts in queue. Idling...")
					time.sleep(10)
					continue
				func, args, kwargs = self.script_queue.pop(0)
				print(f"[BreakManager] Running script: {func.__name__}")
				try:
					func(*args, **kwargs)
				except Exception as e:
					print(f"[BreakManager] Script {func.__name__} failed: {e}")
				self.script_queue.append((func, args, kwargs))  # Re-queue for rotation
				# Check break bias after each script
				if self._should_break() and time.time() - session_start > self.min_play:
					print("[BreakManager] Decided to take a break.")
					break
			# Logout for break
			print("[BreakManager] Logging out for break...")
			# self.client.secure_logout()  # Implement as needed
			print("[BreakManager] (Stub) Please log out manually.")
			while self.client.is_logged_in():
				time.sleep(5)
			break_time = self._random_break_time()
			print(f"[BreakManager] Taking a break for {break_time//60}m {break_time%60}s.")
			time.sleep(break_time)

	def stop(self):
		self.running = False
