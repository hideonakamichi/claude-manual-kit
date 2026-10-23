"""portalock.py — Mac/Linux（fcntl.flock）と Windows（msvcrt.locking）で同じ形で使える排他ロック

どちらも「ロックを持つプロセスが消えれば OS が自動で外す」ので、異常終了でロックが残らない。

  lock_ex(f)                 取れるまで待つ
  lock_ex(f, blocking=False) 取れなければ BlockingIOError を投げる（待たない）

f は open() したファイルオブジェクトか、os.open() の fd（整数）。ロックは閉じるまで保持される。
"""
from __future__ import annotations

import sys
import time

if sys.platform == "win32":
    import msvcrt
    import os

    def lock_ex(f, blocking: bool = True) -> None:
        fd = f if isinstance(f, int) else f.fileno()
        while True:
            try:
                os.lseek(fd, 0, os.SEEK_SET)          # ロックは現在位置から数えるので、先頭に固定する
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)  # 先頭1バイトを排他ロック（ファイルが空でも可）
                return
            except OSError:
                if not blocking:
                    raise BlockingIOError("lock is held by another process")
                time.sleep(0.5)
else:
    import fcntl

    def lock_ex(f, blocking: bool = True) -> None:
        flags = fcntl.LOCK_EX if blocking else (fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.flock(f, flags)
