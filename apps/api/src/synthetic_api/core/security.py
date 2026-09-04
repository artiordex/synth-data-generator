import hashlib

from pathlib import Path



def calculate_sha256(file_path: Path) -> str:

    h = hashlib.sha256()

    with open(file_path, "rb") as f:

        while chunk := f.read(8192):

            h.update(chunk)

    return h.hexdigest()
