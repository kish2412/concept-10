from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class Clinic(BaseModel):
    __tablename__ = "clinics"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    external_org_id: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True, index=True)
    ai_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    ai_policy_tier: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ai_guardrail_profile: Mapped[str | None] = mapped_column(String(100), nullable=True)

    users = relationship("User", back_populates="clinic", lazy="selectin")
