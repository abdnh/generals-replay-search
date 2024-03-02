import traceback
from pathlib import Path

from .replays.database import ReplayDatabase
from .replays.parser import Replay

db = ReplayDatabase(Path("replays.db"))
for sample_path in Path("data/zh").rglob("*.rep"):
    print(f"{sample_path.name=}")
    try:
        replay = Replay(sample_path)
        db.add_replay(replay)
    except Exception as exc:
        with open("failing.txt", "a", encoding="utf-8") as file:
            file.write(f"- {str(sample_path)}:\n")
            traceback.print_exc(file=file)
    db.connection.commit()
