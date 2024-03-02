import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .parser import Replay


class ReplayDatabase:
    def __init__(self, path: Path):
        self.connection = sqlite3.connect(path)
        self._setup()

    def _setup(self) -> None:
        self.connection.executescript(
            """
CREATE TABLE IF NOT EXISTS replays (
    id INTEGER PRIMARY KEY,
    start_date INTEGER,
    end_date  INTEGER,
    filename TEXT,
    version TEXT,
    build_date TEXT,
    version_major INT,
    version_minor INT,
    game_speed INT,
    mapfile TEXT,
    starting_credits INT
);

CREATE TABLE IF NOT EXISTS slots (
    replay_id INTEGER,
    type INTEGER,
    human_name TEXT,
    user_id INTEGER,
    computer_difficulty INTEGER,
    color INTEGER,
    faction INTEGER,
    star_position INTEGER,
    team INTEGER
);
"""
        )

    def add_replay(self, replay: "Replay") -> None:
        # TODO: duplicate handling
        (replay_id, *_) = self.connection.execute(
            """
INSERT INTO replays(start_date, end_date, filename, version, build_date, version_major, version_minor, game_speed, mapfile, starting_credits) values(?, ?, ?, ?, ?, ?, ?, ?, ?, ?) RETURNING id;
""",
            (
                int(replay.start_date.timestamp()),
                int(replay.end_date.timestamp()),
                replay.path.name,
                replay.version,
                replay.build_date,
                replay.version_major,
                replay.version_minor,
                replay.game_speed,
                replay.metadata.mapfile,
                replay.metadata.starting_credits,
            ),
        ).fetchone()
        print(f"{replay_id=}")
        for slot in replay.metadata.slots:
            if not slot.slot_type.value:
                continue
            self.connection.execute(
                "INSERT INTO slots(replay_id, type, human_name, user_id, computer_difficulty, color, faction, star_position, team) values(?, ?, ?, ?, ?, ?, ?, ?, ?);",
                (
                    replay_id,
                    slot.slot_type.value,
                    slot.human_name,
                    slot.user_id,
                    slot.computer_difficulty.value if slot.computer_difficulty else 0,
                    slot.color,
                    slot.faction,
                    slot.star_position,
                    slot.team,
                ),
            )
