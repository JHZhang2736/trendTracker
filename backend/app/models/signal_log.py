from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SignalLog(Base):
    __tablename__ = "signal_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    signal_type: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="rank_jump | new_entry | heat_surge"
    )
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    keyword: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, comment="人类可读的信号描述")
    value: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="信号量化值（如跃升位数、倍数等）"
    )
    detected_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)

    def __repr__(self) -> str:
        return (
            f"<SignalLog id={self.id} type={self.signal_type!r}"
            f" platform={self.platform!r} keyword={self.keyword!r}>"
        )
