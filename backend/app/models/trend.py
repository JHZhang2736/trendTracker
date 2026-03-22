from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.ai_insight import AIInsight
    from app.models.platform import Platform


class Trend(Base):
    __tablename__ = "trends"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    platform_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("platforms.id", ondelete="SET NULL"), nullable=True
    )
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    keyword: Mapped[str] = mapped_column(String(200), nullable=False)
    rank: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    heat_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    relevance_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    relevance_label: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    relevance_reason: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    platform_rel: Mapped[Optional[Platform]] = relationship("Platform", back_populates="trends")
    ai_insights: Mapped[list[AIInsight]] = relationship("AIInsight", back_populates="trend")

    def __repr__(self) -> str:
        return f"<Trend id={self.id} platform={self.platform!r} keyword={self.keyword!r}>"
