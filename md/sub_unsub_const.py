

from typing import Final
from enum import StrEnum

class SubUnsubMode(StrEnum):
    Full : Final = "full"
    Quote: Final = "quote"
    Ltp: Final = "ltp"

class SubUnsubKeys(StrEnum):
    Sub = "sub"
    Unsub = "unsub"
    InstIds = "instids"
    Mode = "mode"

