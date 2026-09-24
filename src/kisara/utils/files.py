"""File publication helpers shared by application services."""

import os
import tempfile
from pathlib import Path
from typing import Optional


def atomic_write_bytes(path: Path, content: bytes) -> None:
    """Replace a file atomically after writing in its existing parent dir."""

    temporary: Optional[Path] = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=str(path.parent), prefix=".kisara-", suffix=".tmp", delete=False,
        ) as output:
            temporary = Path(output.name)
            output.write(content)
        os.replace(str(temporary), str(path))
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
