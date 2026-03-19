from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.keyword import Keyword


class KeywordAlert(Base):
    __tablename__ = "keyword_alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    keyword_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("keywords.id", ondelete="CASCADE"), nullable=False
    )
    threshold: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    notify_email: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    keyword_rel: Mapped[Keyword] = relationship("Keyword", back_populates="alerts")

    def __repr__(self) -> str:
        return f"<KeywordAlert id={self.id} keyword_id={self.keyword_id}>"
