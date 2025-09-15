"""Pydantic models for ESPN API responses."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class SportCategory(BaseModel):
    """Sport category model."""
    id: str
    name: str
    slug: Optional[str] = None
    icon_url: Optional[str] = None
    leagues: Optional[List[Dict[str, Any]]] = None


class Team(BaseModel):
    """Team model for sports events."""
    id: Optional[str] = None
    name: str
    abbreviation: Optional[str] = None
    logo_url: Optional[str] = None
    score: Optional[str] = None
    winner: Optional[bool] = None
    rank: Optional[str] = None


class Event(BaseModel):
    """Sports event model."""
    id: str
    sport_name: Optional[str] = Field(None, alias="sportName")
    event_name: Optional[str] = Field(None, alias="eventName")
    game_state: Optional[str] = Field(None, alias="gameState")  # pre, in, post
    game_date: Optional[datetime] = Field(None, alias="gameDate")
    league_name: Optional[str] = Field(None, alias="leagueName")
    status_text: Optional[str] = Field(None, alias="statusText")
    headline: Optional[str] = None
    teams: Optional[List[Team]] = None
    player_one_name: Optional[str] = Field(None, alias="playerOneName")
    player_two_name: Optional[str] = Field(None, alias="playerTwoName")
    player_one_score: Optional[List[Dict[str, Any]]] = Field(None, alias="playerOneLinescore")
    player_two_score: Optional[List[Dict[str, Any]]] = Field(None, alias="playerTwoLinescore")
    tv_info: Optional[str] = Field(None, alias="eventTv")
    note: Optional[str] = None
    webview_url: Optional[str] = Field(None, alias="webviewURL")
    deep_link_url: Optional[str] = Field(None, alias="deepLinkURL")
    

class HomeFeedItem(BaseModel):
    """Home feed content item."""
    id: str
    type: str
    published_date: Optional[datetime] = Field(None, alias="publishedDate")
    last_modified: Optional[datetime] = Field(None, alias="lastModified")
    headline: Optional[str] = None
    description: Optional[str] = None
    items: Optional[List[Dict[str, Any]]] = None


class ClubhouseResponse(BaseModel):
    """Response from clubhouse endpoint."""
    content: Optional[List[Dict[str, Any]]] = None
    meta: Optional[Dict[str, Any]] = None


class HomeFeedResponse(BaseModel):
    """Response from home feed endpoint."""
    content: List[HomeFeedItem]
    next_cursor: Optional[str] = Field(None, alias="nextCursor")


class TopEventsResponse(BaseModel):
    """Response from top events endpoint."""
    content: Optional[List[Dict[str, Any]]] = None
    items: Optional[List[Event]] = None


class SportsListResponse(BaseModel):
    """Response from sports list endpoint."""
    sports: List[SportCategory]
    meta: Optional[Dict[str, Any]] = None


class EventDetailsResponse(BaseModel):
    """Response for event details."""
    event: Event
    game_details: Optional[Dict[str, Any]] = None
    stats: Optional[Dict[str, Any]] = None
    play_by_play: Optional[List[Dict[str, Any]]] = None

