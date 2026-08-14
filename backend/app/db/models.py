"""Central model registry imported by Alembic and test setup."""

from app.audit.models import AuditLog
from app.content.models import Announcement, BanlistVersion
from app.deck_submissions.models import DeckSubmission
from app.matches.models import Match, MatchSubmission
from app.messages.models import Message
from app.playoffs.models import PlayoffRound
from app.registrations.models import Registration, TournamentParticipant
from app.reports.models import WeeklyReport
from app.swiss.models import RankingSnapshot, SwissRound, Withdrawal
from app.tournaments.models import Tournament
from app.users.models import User

__all__ = [
    "Announcement",
    "AuditLog",
    "BanlistVersion",
    "DeckSubmission",
    "Match",
    "MatchSubmission",
    "Message",
    "PlayoffRound",
    "RankingSnapshot",
    "Registration",
    "SwissRound",
    "Tournament",
    "TournamentParticipant",
    "User",
    "WeeklyReport",
    "Withdrawal",
]
