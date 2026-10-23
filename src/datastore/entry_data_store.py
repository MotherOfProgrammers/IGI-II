# Created By MotherOfProgrammers(MOP)
import os
from pathlib import Path
from dataclasses import dataclass, field
from dotenv import load_dotenv


load_dotenv(Path(__file__).with_name(".env"))

@dataclass(frozen=True, slots=True)
class DataStore:
    _entry_key: str = field(repr=False)

    @classmethod
    def load(cls):
        key = os.getenv("ENTRY_KEY")

        if not key:
            raise RuntimeError("ENTRY_KEY is not configured")

        return cls(_entry_key=key)

    @property
    def entry_key(self) -> str:
        return self._entry_key


# store = DataStore.load() # initialize the data store
# print(store.entry_key)

