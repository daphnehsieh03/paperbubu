from fastapi import APIRouter

from app.deps import CurrentUser, SessionDep
from app.models import HeatmapResponse, MeStatsResponse
from app.services.analytics import get_heatmap, get_stats

router = APIRouter(prefix="/me", tags=["analytics"])


@router.get("/heatmap", response_model=HeatmapResponse)
def heatmap(session: SessionDep, user: CurrentUser) -> HeatmapResponse:
    return get_heatmap(session, user.id)


@router.get("/stats", response_model=MeStatsResponse)
def stats(session: SessionDep, user: CurrentUser) -> MeStatsResponse:
    return get_stats(session, user.id)
