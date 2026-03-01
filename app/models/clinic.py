from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class Clinic(BaseModel):
    __tablename__ = "clinics"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    external_org_id: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True, index=True)

    users = relationship("User", back_populates="clinic", lazy="selectin")
