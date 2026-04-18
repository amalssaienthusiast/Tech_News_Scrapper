"""Articles API routes."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from ..main import verify_api_key, ArticleResponse, ArticlesListResponse

router = APIRouter(prefix="/v1/articles", tags=["Articles"])


@router.get("", response_model=ArticlesListResponse)
async def list_articles(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    source: Optional[str] = Query(None),
    auth: dict = Depends(verify_api_key)
):
    """Get paginated list of articles."""
    from src.database import Database
    
    db = Database()
    all_articles = db.get_all_articles()
    
    filtered = all_articles
    if source:
        filtered = [a for a in filtered if source.lower() in (a.get("source", "") or "").lower()]
    
    start = (page - 1) * per_page
    end = start + per_page
    page_articles = filtered[start:end]
    
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
        total=len(filtered),
        page=page,
        per_page=per_page,
        has_more=end < len(filtered),
    )


@router.get("/{article_id}", response_model=ArticleResponse)
async def get_article(article_id: str, auth: dict = Depends(verify_api_key)):
    """Get single article by ID."""
    from src.database import Database
    
    db = Database()
    articles = db.get_all_articles()
    
    for a in articles:
        if a.get("id") == article_id:
            return ArticleResponse(
                id=a.get("id", ""),
                title=a.get("title", ""),
                url=a.get("url", ""),
                source=a.get("source", ""),
                published_at=a.get("published_at"),
                summary=a.get("summary") or a.get("ai_summary"),
            )
    
    raise HTTPException(status_code=404, detail="Article not found")
