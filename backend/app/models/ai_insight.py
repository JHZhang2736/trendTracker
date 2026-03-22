from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.trend import Trend


class AIInsight(Base):
    __tablename__ = "ai_insights"

    __table_args__ = (Index("ix_ai_insights_keyword", "keyword"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    keyword: Mapped[str] = mapped_column(String(200), nullable=False)
    trend_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("trends.id", ondelete="SET NULL"), nullable=True
    )
    insight_type: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Deep analysis fields (Stage 3 pipeline)
    search_context: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    deep_analysis: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_urls: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    analysis_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)

    trend: Mapped[Optional[Trend]] = relationship("Trend", back_populates="ai_insights")

    def __repr__(self) -> str:
        return f"<AIInsight id={self.id} type={self.insight_type!r}>"
