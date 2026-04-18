"""Search API routes."""

from fastapi import APIRouter, Depends, Query

from ..main import verify_api_key, ArticleResponse, ArticlesListResponse

router = APIRouter(prefix="/v1/search", tags=["Search"])


@router.get("", response_model=ArticlesListResponse)
async def search(
    q: str = Query(..., min_length=2, description="Search query"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    auth: dict = Depends(verify_api_key)
):
    """Search articles by title and content."""
    from src.database import Database
    
    db = Database()
    results = db.search_articles(q, limit=per_page * page)
    
    start = (page - 1) * per_page
    page_articles = results[start:start + per_page]
    
    articles = [
        ArticleResponse(
            id=a.get("id", ""),
            title=a.get("title", ""),
            url=a.get("url", ""),
            source=a.get("source", ""),
            published_at=a.get("published_at"),
            summary=a.get("summary") or a.get("ai_summary"),
        )
        for a in page_articles
    ]
    
    return ArticlesListResponse(
        articles=articles,
        total=len(results),
        page=page,
        per_page=per_page,
        has_more=len(results) > page * per_page,
    )
