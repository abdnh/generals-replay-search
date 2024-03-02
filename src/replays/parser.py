"""
Parser for replay files.

Credit: based on the OpenSAGE implementation <https://github.com/OpenSAGE/OpenSAGE/tree/master/src/OpenSage.Game/Data/Rep>
"""

from __future__ import annotations

import dataclasses
import datetime
import enum
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO


def read_uint16(file: BinaryIO) -> int:
    return struct.unpack("<H", file.read(2))[0]


def read_uint32(file: BinaryIO) -> int:
    return struct.unpack("<I", file.read(4))[0]


def read_null_terminated_string(file: BinaryIO) -> str:
    chars = []
    while c := file.read(1):
        if c == b"\x00":
            break
        chars.append(c)
    return b"".join(chars).decode()


def read_null_terminated_utf16_string(file: BinaryIO) -> str:
    chars = []
    while c := file.read(2):
        if c == b"\x00\x00":
            break
        chars.append(c)
    return b"".join(chars).decode(encoding="utf_16")


class ReplayParserException(Exception):
    pass


class GameType(enum.Enum):
    GENERALS = enum.auto()
    BFME = enum.auto()
    BFME2 = enum.auto()


@dataclass
class ReplayTimestamp:
    year: int
    month: int
    day_of_week: int
    day: int
    hour: int
    minute: int
    second: int
    millisecond: int

    @classmethod
    def parse(cls, file: BinaryIO) -> ReplayTimestamp:
        return cls(
            read_uint16(file),
            read_uint16(file),
            read_uint16(file),
            read_uint16(file),
            read_uint16(file),
            read_uint16(file),
            read_uint16(file),
            read_uint16(file),
        )


class ReplaySlotType(enum.Enum):
    EMPTY = 0
    HUMAN = 1
    COMPUTER = 2


class ReplaySlotDifficulty(enum.Enum):
    EASY = 1
    MEDIUM = 2
    HARD = 3


@dataclass
class ReplaySlot:
    slot_type: ReplaySlotType
    human_name: str = ""
    # As shown by RepInfo
    user_id: int = 0
    computer_difficulty: ReplaySlotDifficulty | None = None
    color: int = 0
    faction: int = 0
    star_position: int = 0
    team: int = 0

    @classmethod
    def parse(cls, raw: str) -> ReplaySlot:
        slot_type = cls._read_slot_type(raw)
        slot = ReplaySlot(slot_type)
        slot_details = [p for p in raw.split(",") if p]
        if slot_type == ReplaySlotType.HUMAN:
            slot.human_name = slot_details[0][1:]
            slot.user_id = int(slot_details[1], base=16)
            slot.color = int(slot_details[4])
            slot.faction = int(slot_details[5])
            slot.star_position = int(slot_details[6])
            slot.team = int(slot_details[7])
        elif slot_type == ReplaySlotType.COMPUTER:
            slot.computer_difficulty = cls._read_slot_difficulty(raw)
            slot.color = int(slot_details[1])
            slot.faction = int(slot_details[2])
            slot.star_position = int(slot_details[3])
            slot.team = int(slot_details[4])

        return slot

    @staticmethod
    def _read_slot_type(raw: str) -> ReplaySlotType:
        c = raw[0]
        if c == "H":
            return ReplaySlotType.HUMAN
        if c == "C":
            return ReplaySlotType.COMPUTER
        if c == "C":
            return ReplaySlotType.COMPUTER
        if c in ("X", "O"):
            return ReplaySlotType.EMPTY
        raise ReplayParserException(f"invalid replay slot type: {raw[0]}")

    @staticmethod
    def _read_slot_difficulty(raw: str) -> ReplaySlotDifficulty:
        c = raw[1]
        if c == "E":
            return ReplaySlotDifficulty.EASY
        if c == "M":
            return ReplaySlotDifficulty.EASY
        if c == "H":
            return ReplaySlotDifficulty.EASY
        raise ReplayParserException(f"invalid replay slot difficulty: {raw[0]}")


@dataclass
class ReplayMetadata:
    mapfile_unknown_int: int = 0
    mapfile: str = ""
    map_crc: int = 0
    map_size: int = 0
    SD: int = 0
    C: int = 0
    SR: int = 0
    starting_credits: int = 0
    O: int = 0
    slots: list[ReplaySlot] = dataclasses.field(default_factory=list)

    @classmethod
    def parse(cls, file: BinaryIO) -> ReplayMetadata:
        metadata = ReplayMetadata()
        raw = read_null_terminated_string(file)
        raw_split = [p for p in raw.split(";") if p]
        for entry in raw_split:
            key, value = entry.split("=", maxsplit=1)
            if key == "US":
                pass
            elif key == "M":
                int_end = 0
                for c in value:
                    if not ("9" >= c >= "0"):
                        break
                    int_end += 1
                metadata.mapfile_unknown_int = int(value[:int_end])
                metadata.mapfile = value[int_end:]
            elif key == "MC":
                metadata.map_crc = int(value, base=16)
            elif key == "MS":
                metadata.map_size = int(value)
            elif key == "SD":
                metadata.SD = int(value)
            elif key == "C":
                metadata.C = int(value)
            elif key == "SR":
                metadata.SR = int(value)
            elif key == "SC":
                metadata.starting_credits = int(value)
            elif key == "O":
                metadata.O = value
            elif key == "S":
                for slot_raw in value.split(":"):
                    if not slot_raw:
                        continue
                    metadata.slots.append(ReplaySlot.parse(slot_raw))
            else:
                raise ReplayParserException(f"Unexpected replay metadata key: {key}")

        return metadata


class Replay:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        with open(self.path, "rb") as file:
            self._parse(file)

    def _parse(self, file: BinaryIO) -> None:
        self.game_type = self._parse_game_type(file)
        if self.game_type != GameType.GENERALS:
            raise ReplayParserException(
                f"parsing for game type {self.game_type.name} not implemented yet"
            )
        self.start_date = self._parse_timestamp(file)
        self.end_date = self._parse_timestamp(file)
        self.num_timecodes = read_uint16(file)
        _zero = file.read(12)
        self.filename = read_null_terminated_utf16_string(file)
        self.timestamp = ReplayTimestamp.parse(file)
        self.version = read_null_terminated_utf16_string(file)
        self.build_date = read_null_terminated_utf16_string(file)
        self.version_minor = read_uint16(file)
        self.version_major = read_uint16(file)
        self.unknown_hash = file.read(8)
        self.metadata = ReplayMetadata.parse(file)
        self.unknown1 = read_uint16(file)
        self.unknown2 = read_uint32(file)
        self.unknown3 = read_uint32(file)
        self.unknown4 = read_uint32(file)
        self.game_speed = read_uint32(file)

    def _parse_game_type(self, file: BinaryIO) -> GameType:
        game_type = file.read(6).decode()
        if game_type == "GENREP":
            return GameType.GENERALS
        game_type = file.read(6).decode()
        if game_type == "BFMEREPL":
            return GameType.BFME
        elif game_type == "BFME2RPL":
            return GameType.BFME2
        raise ReplayParserException(f"Unrecognized replay type: {game_type}")

    def _parse_timestamp(self, file: BinaryIO) -> datetime.datetime:
        timestamp = read_uint32(file)
        return datetime.datetime.fromtimestamp(timestamp)
