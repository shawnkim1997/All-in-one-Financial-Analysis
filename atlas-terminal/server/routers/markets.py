"""Markets router for index constituent heatmap."""

from fastapi import APIRouter, Query

router = APIRouter()


@router.get("/heatmap/{index_name}", summary="Index constituent heatmap data")
async def heatmap(index_name: str, top_n: int = Query(default=50, ge=1, le=200)):
    from server.services.heatmap import get_heatmap_data

    stocks = await get_heatmap_data(index_name, top_n)
    return {"index": index_name, "count": len(stocks), "stocks": stocks}

