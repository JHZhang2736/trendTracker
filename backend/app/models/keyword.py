from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.alert_log import AlertLog
    from app.models.keyword_alert import KeywordAlert


class Keyword(Base):
    __tablename__ = "keywords"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    keyword: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)

    alerts: Mapped[list[KeywordAlert]] = relationship("KeywordAlert", back_populates="keyword_rel")
    alert_logs: Mapped[list[AlertLog]] = relationship("AlertLog", back_populates="keyword_rel")

    def __repr__(self) -> str:
        return f"<Keyword id={self.id} keyword={self.keyword!r}>"
