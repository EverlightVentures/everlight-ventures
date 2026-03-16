import time
import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class ManifestHandler(FileSystemEventHandler):
    def __init__(self):
        self.last_run = 0
        self.debounce_seconds = 2

    def on_any_event(self, event):
        # Ignore logs, hidden files, and the manifest itself to prevent loops
        if any(x in event.src_path for x in ['_logs', '.git', 'WORKSPACE_MANIFEST.md', '.gemini', '.claude']):
            return
        
        current_time = time.time()
        if current_time - self.last_run > self.debounce_seconds:
            print(f"Change detected: {event.src_path}. Updating manifest...")
            subprocess.run(["python3", "/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/file_organizer/manifest_generator.py"])
            self.last_run = current_time

if __name__ == "__main__":
    path = "/mnt/sdcard/AA_MY_DRIVE"
    event_handler = ManifestHandler()
    observer = Observer()
    observer.schedule(event_handler, path, recursive=True)
    print(f"Watching {path} for changes...")
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
