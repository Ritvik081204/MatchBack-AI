"""SQLAlchemy models. Only generic column types are used so the schema works on PostgreSQL unchanged."""
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Team(Base):
    __tablename__ = "teams"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    abbreviation: Mapped[str] = mapped_column(String(8))


class Player(Base):
    __tablename__ = "players"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    cricsheet_id: Mapped[str | None] = mapped_column(String(16), unique=True, nullable=True)


class Match(Base):
    __tablename__ = "matches"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)  # Cricsheet match id
    source: Mapped[str] = mapped_column(String(32), default="cricsheet")
    data_kind: Mapped[str] = mapped_column(String(16), default="HISTORICAL")
    format: Mapped[str] = mapped_column(String(8), index=True)  # T20 / ODI / TEST
    raw_match_type: Mapped[str] = mapped_column(String(16))
    gender: Mapped[str] = mapped_column(String(8), default="male")
    tournament: Mapped[str | None] = mapped_column(String(160), nullable=True)
    stage: Mapped[str | None] = mapped_column(String(60), nullable=True)
    season: Mapped[str | None] = mapped_column(String(16), nullable=True)
    venue: Mapped[str | None] = mapped_column(String(200), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    date_start: Mapped[str] = mapped_column(String(10), index=True)
    date_end: Mapped[str] = mapped_column(String(10))
    team1_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    team2_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    toss_winner: Mapped[str | None] = mapped_column(String(120), nullable=True)
    toss_decision: Mapped[str | None] = mapped_column(String(10), nullable=True)
    winner: Mapped[str | None] = mapped_column(String(120), nullable=True)
    outcome: Mapped[dict] = mapped_column(JSON, default=dict)
    outcome_text: Mapped[str] = mapped_column(String(240), default="")
    player_of_match: Mapped[list] = mapped_column(JSON, default=list)
    squads: Mapped[dict] = mapped_column(JSON, default=dict)  # {team: [player names]}
    balls_per_over: Mapped[int] = mapped_column(Integer, default=6)
    overs_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_deliveries: Mapped[int] = mapped_column(Integer, default=0)
    data_issues: Mapped[list] = mapped_column(JSON, default=list)
    ingested_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    team1 = relationship("Team", foreign_keys=[team1_id])
    team2 = relationship("Team", foreign_keys=[team2_id])
    innings = relationship("Innings", back_populates="match", cascade="all, delete-orphan", order_by="Innings.innings_no")


class Innings(Base):
    __tablename__ = "innings"
    __table_args__ = (UniqueConstraint("match_id", "innings_no"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[str] = mapped_column(ForeignKey("matches.id", ondelete="CASCADE"), index=True)
    innings_no: Mapped[int] = mapped_column(Integer)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    target_runs: Mapped[int | None] = mapped_column(Integer, nullable=True)
    target_overs: Mapped[float | None] = mapped_column(Float, nullable=True)
    declared: Mapped[bool] = mapped_column(Boolean, default=False)
    forfeited: Mapped[bool] = mapped_column(Boolean, default=False)
    super_over: Mapped[bool] = mapped_column(Boolean, default=False)
    total_runs: Mapped[int] = mapped_column(Integer, default=0)
    wickets: Mapped[int] = mapped_column(Integer, default=0)
    legal_balls: Mapped[int] = mapped_column(Integer, default=0)

    match = relationship("Match", back_populates="innings")
    team = relationship("Team")


class Delivery(Base):
    __tablename__ = "deliveries"
    __table_args__ = (
        UniqueConstraint("match_id", "seq"),
        Index("ix_deliveries_match_innings", "match_id", "innings_no"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[str] = mapped_column(ForeignKey("matches.id", ondelete="CASCADE"))
    innings_no: Mapped[int] = mapped_column(Integer)
    seq: Mapped[int] = mapped_column(Integer)  # global order within the match, 0-based
    over_no: Mapped[int] = mapped_column(Integer)  # 0-based
    ball_idx: Mapped[int] = mapped_column(Integer)  # position in over, 1-based, includes illegal balls
    batter_id: Mapped[int] = mapped_column(ForeignKey("players.id"))
    non_striker_id: Mapped[int | None] = mapped_column(ForeignKey("players.id"), nullable=True)
    bowler_id: Mapped[int] = mapped_column(ForeignKey("players.id"))
    batter_runs: Mapped[int] = mapped_column(Integer, default=0)
    extras: Mapped[int] = mapped_column(Integer, default=0)
    total: Mapped[int] = mapped_column(Integer, default=0)
    wides: Mapped[int] = mapped_column(Integer, default=0)
    noballs: Mapped[int] = mapped_column(Integer, default=0)
    byes: Mapped[int] = mapped_column(Integer, default=0)
    legbyes: Mapped[int] = mapped_column(Integer, default=0)
    penalty: Mapped[int] = mapped_column(Integer, default=0)
    non_boundary: Mapped[bool] = mapped_column(Boolean, default=False)
    review: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class Wicket(Base):
    __tablename__ = "wickets"
    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[str] = mapped_column(ForeignKey("matches.id", ondelete="CASCADE"), index=True)
    delivery_seq: Mapped[int] = mapped_column(Integer)
    innings_no: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(32))
    player_out_id: Mapped[int] = mapped_column(ForeignKey("players.id"))
    fielders: Mapped[list] = mapped_column(JSON, default=list)


class Partnership(Base):
    __tablename__ = "partnerships"
    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[str] = mapped_column(ForeignKey("matches.id", ondelete="CASCADE"), index=True)
    innings_no: Mapped[int] = mapped_column(Integer)
    wicket_no: Mapped[int] = mapped_column(Integer)
    batter1: Mapped[str] = mapped_column(String(120))
    batter2: Mapped[str] = mapped_column(String(120))
    runs: Mapped[int] = mapped_column(Integer)
    balls: Mapped[int] = mapped_column(Integer)
    start_seq: Mapped[int] = mapped_column(Integer)
    end_seq: Mapped[int] = mapped_column(Integer)
    unbroken: Mapped[bool] = mapped_column(Boolean, default=False)
    detail: Mapped[dict] = mapped_column(JSON, default=dict)


class PlayerMatchStatistics(Base):
    __tablename__ = "player_match_statistics"
    __table_args__ = (UniqueConstraint("match_id", "player_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[str] = mapped_column(ForeignKey("matches.id", ondelete="CASCADE"), index=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), index=True)
    team: Mapped[str] = mapped_column(String(120))
    runs: Mapped[int] = mapped_column(Integer, default=0)
    balls_faced: Mapped[int] = mapped_column(Integer, default=0)
    fours: Mapped[int] = mapped_column(Integer, default=0)
    sixes: Mapped[int] = mapped_column(Integer, default=0)
    wickets: Mapped[int] = mapped_column(Integer, default=0)
    balls_bowled: Mapped[int] = mapped_column(Integer, default=0)
    runs_conceded: Mapped[int] = mapped_column(Integer, default=0)
    maidens: Mapped[int] = mapped_column(Integer, default=0)
    catches: Mapped[int] = mapped_column(Integer, default=0)
    run_outs: Mapped[int] = mapped_column(Integer, default=0)
    stumpings: Mapped[int] = mapped_column(Integer, default=0)
    impact: Mapped[float] = mapped_column(Float, default=0)


class MatchEvent(Base):
    __tablename__ = "match_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[str] = mapped_column(ForeignKey("matches.id", ondelete="CASCADE"), index=True)
    seq: Mapped[int] = mapped_column(Integer, index=True)
    innings_no: Mapped[int] = mapped_column(Integer)
    type: Mapped[str] = mapped_column(String(32), index=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)


class MatchMilestone(Base):
    __tablename__ = "match_milestones"
    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[str] = mapped_column(ForeignKey("matches.id", ondelete="CASCADE"), index=True)
    seq: Mapped[int] = mapped_column(Integer)
    innings_no: Mapped[int] = mapped_column(Integer)
    category: Mapped[str] = mapped_column(String(16))
    kind: Mapped[str] = mapped_column(String(40))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)


class MatchTurningPoint(Base):
    __tablename__ = "match_turning_points"
    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[str] = mapped_column(ForeignKey("matches.id", ondelete="CASCADE"), index=True)
    innings_no: Mapped[int] = mapped_column(Integer)
    start_seq: Mapped[int] = mapped_column(Integer)
    end_seq: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(40))
    score: Mapped[float] = mapped_column(Float)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)


class MatchSummary(Base):
    """Cache of generated recaps, keyed by the exact request so identical requests are instant."""
    __tablename__ = "match_summaries"
    __table_args__ = (UniqueConstraint("match_id", "cutoff_seq", "length", "focus", "engine"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[str] = mapped_column(ForeignKey("matches.id", ondelete="CASCADE"), index=True)
    cutoff_seq: Mapped[int] = mapped_column(Integer)
    length: Mapped[str] = mapped_column(String(12))
    focus: Mapped[str] = mapped_column(String(16))
    engine: Mapped[str] = mapped_column(String(40))
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
