"""Master profile schema, whitelist validation, and DB persistence (Stage 1.1)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


class MasterBullet(BaseModel):
    id: str
    text: str
    tags: list[str] = Field(default_factory=list)
    facts: list[str] = Field(default_factory=list)


class MasterExperience(BaseModel):
    id: str
    category: Literal["internship", "project", "training"]
    organization: str
    role: str
    period: str
    bullets: list[MasterBullet] = Field(default_factory=list)


class MasterEducation(BaseModel):
    school: str
    college: str = ""
    major: str
    degree: str
    period: str
    graduation_year: int = 2027
    core_courses: list[str] = Field(default_factory=list)


class SkillItem(BaseModel):
    name: str
    level: str
    category: str = ""


class MasterProfile(BaseModel):
    version_tag: str
    education: MasterEducation
    certifications: list[str] = Field(default_factory=list)
    skills: list[SkillItem] = Field(default_factory=list)
    experiences: list[MasterExperience] = Field(default_factory=list)
    proper_nouns_whitelist: list[str] = Field(default_factory=list)

    def all_bullet_ids(self) -> set[str]:
        return {b.id for exp in self.experiences for b in exp.bullets}


class QABankItem(BaseModel):
    id: str
    question: str
    category: str
    draft_answer: str
    evidence_ids: list[str] = Field(default_factory=list)


class QABank(BaseModel):
    version_tag: str
    items: list[QABankItem] = Field(default_factory=list)


def load_master_and_qa(
    profile_path: Path,
    qa_path: Path | None = None,
) -> tuple[MasterProfile, QABank]:
    profile_raw = json.loads(profile_path.read_text(encoding="utf-8"))
    profile = MasterProfile.model_validate(profile_raw)

    if qa_path is not None and qa_path.exists():
        qa_raw = json.loads(qa_path.read_text(encoding="utf-8"))
        qa_bank = QABank.model_validate(qa_raw)
    else:
        qa_bank = QABank(version_tag=profile.version_tag, items=[])

    valid_ids = profile.all_bullet_ids()
    for item in qa_bank.items:
        missing = [eid for eid in item.evidence_ids if eid not in valid_ids]
        if missing:
            raise ValueError(f"QA item {item.id} references unknown bullet ids: {missing}")

    return profile, qa_bank
