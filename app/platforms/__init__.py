from app.platforms.base import Platform
from app.platforms.dpaste import Dpaste
from app.platforms.ntfy import Ntfy
from app.platforms.paste_rs import PasteRs
from app.platforms.rentry import Rentry
from app.platforms.telegraph import Telegraph

PLATFORMS: list[Platform] = [Telegraph(), Dpaste(), PasteRs(), Ntfy(), Rentry()]
