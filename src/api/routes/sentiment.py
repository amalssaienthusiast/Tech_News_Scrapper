"""Sentiment API routes."""

from typing import List

from fastapi import APIRouter, Depends, Query

from ..main import verify_api_key, SentimentResponse, TrendResponse

router = APIRouter(prefix="/v1/sentiment", tags=["Sentiment"])


@router.get("/analyze", response_model=SentimentResponse)
async def analyze_text(
    text: str = Query(..., min_length=10, description="Text to analyze"),
    auth: dict = Depends(verify_api_key)
):
    """Analyze sentiment of provided text."""
    from src.intelligence.sentiment_analyzer import get_sentiment_analyzer
    
    analyzer = get_sentiment_analyzer()
    result = analyzer.analyze(text, persist=False)
    
    return SentimentResponse(
        score=result.score,
        label=result.label.value,
        emoji=result.label.emoji,
        topics=result.topics,
        keywords=result.keywords_detected,
    )


@router.get("/trends", response_model=List[TrendResponse])
async def get_trends(
    period: str = Query("24h", pattern="^(24h|7d|30d)$"),
    auth: dict = Depends(verify_api_key)
):
    """Get sentiment trends across topics."""
    from src.intelligence.sentiment_analyzer import get_sentiment_analyzer
    
    analyzer = get_sentiment_analyzer()
    summary = analyzer.get_topic_sentiment_summary()
    
    trends = []
    for topic, trend in summary.items():
        trends.append(TrendResponse(
            topic=topic,
            period=period,
            avg_score=trend.avg_score,
            score_change=trend.score_change,
            article_count=trend.article_count,
            trend_direction=trend.trend_direction,
        ))
    
    return trends


@router.get("/article/{article_id}", response_model=SentimentResponse)
async def get_article_sentiment(
    article_id: str,
    auth: dict = Depends(verify_api_key)
):
    """Get stored sentiment for an article."""
    from src.intelligence.sentiment_analyzer import get_sentiment_analyzer
    
    analyzer = get_sentiment_analyzer()
    result = analyzer.get_sentiment(article_id)
    
    if not result:
        # Try to analyze from database
        from src.database import Database
        db = Database()
        articles = db.get_all_articles()
        
        for a in articles:
            if a.get("id") == article_id:
                text = a.get("content") or a.get("title", "")
                result = analyzer.analyze(text, article_id=article_id)
                break
    
    if not result:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Article not found")
    
    return SentimentResponse(
        score=result.score,
        label=result.label.value,
        emoji=result.label.emoji,
        topics=result.topics,
        keywords=result.keywords_detected,
    )
