import uuid
from typing import Any, List, Optional, Tuple, Union

from sqlalchemy import or_
from sqlalchemy.orm import Session

from . import models


def _sync_pending_achievements(db: Session, user: models.User):
    pendings = (
        db.query(models.PendingAchievement).filter(
            models.PendingAchievement.user_reference.in_(
                [
                    str(user.id),
                    f"discord:{user.discord_id}",
                    f"discord:{user.discord_username}",
                    f"twitter:{user.twitter_id}",
                    f"twitter:{user.twitter_username}",
                ]
            )
        )
        # .order_by(models.PendingAchievement.achievement.updated_at.desc())
        .all()
    )

    names = set()
    for pending in pendings:
        if pending.achievement.name in names:
            continue

        pending.achievement.owner = user
        db.delete(pending)

        names.add(pending.achievement.name)

    db.commit()


def create_user(
    db: Session,
    discord_username: Optional[str] = None,
    discord_id: Optional[str] = None,
    twitter_username: Optional[str] = None,
    twitter_id: Optional[str] = None,
) -> models.User:
    db_user = models.User(
        discord_username=discord_username,
        discord_id=discord_id,
        twitter_username=twitter_username,
        twitter_id=twitter_id,
    )
    db.add(db_user)
    db.commit()
    _sync_pending_achievements(db, db_user)
    db.refresh(db_user)
    return db_user


def delete_user(db: Session, user: models.User):
    db.delete(user)


def delete_achievement(db: Session, achievement: models.Achievement):
    db.delete(achievement)


def modify_user(
    db: Session,
    user: models.User,
    discord_username: Optional[str] = None,
    discord_id: Optional[str] = None,
    twitter_username: Optional[str] = None,
    twitter_id: Optional[str] = None,
) -> models.User:
    if discord_username:
        user.discord_username = discord_username
    if discord_id:
        user.discord_id = discord_id
    if twitter_username:
        user.twitter_username = twitter_username
    if twitter_id:
        user.twitter_id = twitter_id
    db.commit()
    _sync_pending_achievements(db, user)
    db.refresh(user)
    return user


def create_achievement(
    db: Session,
    name: str,
    owner: Optional[models.User] = None,
    owner_ref: Optional[Union[uuid.UUID, str]] = None,
    tags: Any = None,
) -> models.User:
    if owner:
        db_achievement = get_user_achievement(db, owner, name)
        if db_achievement:
            db.delete(db_achievement)

    if owner:
        db_achievement = models.Achievement(
            name=name,
            tags=tags,
            owner=owner,
        )
    else:
        db_achievement = models.Achievement(name=name, tags=tags)
    db.add(db_achievement)
    db.commit()
    db.refresh(db_achievement)

    if owner is None and owner_ref is not None:
        db_pending = models.PendingAchievement(
            achievement=db_achievement,
            user_reference=str(owner_ref),
        )
        db.add(db_pending)
        db.commit()

    return db_achievement


def get_user(db: Session, userref: Union[uuid.UUID, str]):
    if isinstance(userref, uuid.UUID):
        f = models.User.id == userref
    else:
        try:
            prefix, username = userref.split(":")
        except ValueError:
            return None

        if prefix == "discord":
            f = or_(
                models.User.discord_username == username,
                models.User.discord_id == username,
            )
        elif prefix == "twitter":
            f = or_(
                models.User.twitter_username == username,
                models.User.twitter_id == username,
            )

    user = db.query(models.User).filter(f).first()
    return user


def get_token(db: Session, token: uuid.UUID):
    tk = db.query(models.Token).filter_by(id=token).first()
    return tk


def get_users(db: Session, limit_offset: Tuple[int, int]):
    limit, offset = limit_offset
    users = db.query(models.User).offset(offset).limit(limit).all()
    return users


def count_users(db: Session) -> int:
    return db.query(models.User).count()


def get_achievement(db: Session, id: uuid.UUID):
    achieve = db.query(models.Achievement).filter_by(id=id).first()
    return achieve


def get_achievements(db: Session, limit_offset: Tuple[int, int]):
    limit, offset = limit_offset
    achieves = db.query(models.Achievement).offset(offset).limit(limit).all()
    return achieves


def count_achievements(db: Session) -> int:
    return db.query(models.Achievement).count()


def get_user_achievement(
    db: Session, user: models.User, achievement: Union[uuid.UUID, str]
):
    if isinstance(achievement, uuid.UUID):
        f = models.Achievement.id == achievement
    else:
        f = models.Achievement.name == achievement
    return user.achievements.filter(f).first()


def get_user_achievements(
    db: Session, user: models.User, limit_offset: Tuple[int, int]
):
    limit, offset = limit_offset
    return user.achievements.limit(limit).offset(offset).all()


def count_user_achievements(db: Session, user: models.User) -> int:
    return user.achievements.count()
