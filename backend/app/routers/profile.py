import json
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, field_validator
from sqlmodel import Session

from app.db import get_session
from app.models import UserProfile, utc_now

router = APIRouter(tags=["profile"])

SessionDep = Annotated[Session, Depends(get_session)]


class ProfilePatch(BaseModel):
    goal: str | None = None
    diet_preference: str | None = None
    cooking_condition: str | None = None
    avoid_foods: list[str] | None = None
    allergies_optional: str | None = None
    health_notes_optional: str | None = None

    @field_validator("goal", "diet_preference", "cooking_condition", mode="before")
    @classmethod
    def required_profile_fields_cannot_be_null(cls, value: Any) -> Any:
        if value is None:
            raise ValueError("This field cannot be null.")
        return value


class ProfileResponse(BaseModel):
    id: int
    goal: str
    diet_preference: str
    cooking_condition: str
    avoid_foods: list[str]
    allergies_optional: str | None
    health_notes_optional: str | None
    created_at: str
    updated_at: str


@router.get("/profile", response_model=ProfileResponse)
def get_profile(session: SessionDep) -> ProfileResponse:
    return _serialize_profile(_get_or_create_profile(session))


@router.patch("/profile", response_model=ProfileResponse)
def patch_profile(payload: ProfilePatch, session: SessionDep) -> ProfileResponse:
    profile = _get_or_create_profile(session)
    updates = payload.model_dump(exclude_unset=True)

    for field_name, value in updates.items():
        if field_name == "avoid_foods":
            profile.avoid_foods = json.dumps(value or [], ensure_ascii=False)
        else:
            setattr(profile, field_name, value)

    profile.updated_at = utc_now()
    session.add(profile)
    session.commit()
    session.refresh(profile)
    return _serialize_profile(profile)


def _get_or_create_profile(session: Session) -> UserProfile:
    profile = session.get(UserProfile, 1)
    if profile is not None:
        return profile

    profile = UserProfile(id=1)
    session.add(profile)
    session.commit()
    session.refresh(profile)
    return profile


def _serialize_profile(profile: UserProfile) -> ProfileResponse:
    return ProfileResponse(
        id=profile.id or 0,
        goal=profile.goal,
        diet_preference=profile.diet_preference,
        cooking_condition=profile.cooking_condition,
        avoid_foods=_loads(profile.avoid_foods, []),
        allergies_optional=profile.allergies_optional,
        health_notes_optional=profile.health_notes_optional,
        created_at=profile.created_at.isoformat(),
        updated_at=profile.updated_at.isoformat(),
    )


def _loads(value: str | None, fallback: Any) -> Any:
    if value is None:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback
