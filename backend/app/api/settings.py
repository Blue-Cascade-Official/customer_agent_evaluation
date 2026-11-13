from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.services import eval_settings as eval_settings_service

router = APIRouter(prefix="/api/settings", tags=["settings"])


class EvalSettingsUpdate(BaseModel):
    enabled: dict[str, bool] = Field(default_factory=dict)


@router.get("/evaluation")
def get_evaluation_settings(db: Session = Depends(get_db)):
    return eval_settings_service.settings_payload(db)


@router.put("/evaluation")
def put_evaluation_settings(payload: EvalSettingsUpdate, db: Session = Depends(get_db)):
    return eval_settings_service.update_settings(db, payload.enabled)
