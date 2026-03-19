from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.keyword import Keyword


class AlertLog(Base):
    __tablename__ = "alert_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    keyword_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("keywords.id", ondelete="SET NULL"), nullable=True
    )
    triggered_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    matched_keywords: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    keyword_rel: Mapped[Optional[Keyword]] = relationship("Keyword", back_populates="alert_logs")

    def __repr__(self) -> str:
        return f"<AlertLog id={self.id} keyword_id={self.keyword_id}>"
