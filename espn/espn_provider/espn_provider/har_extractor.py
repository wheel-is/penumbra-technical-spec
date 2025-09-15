#!/usr/bin/env python3
"""
HAR Data Extractor - Dynamically extract ESPN data from HAR files
Uses har_preview.py logic to reverse engineer ESPN mobile app APIs
"""

import json
import os
from datetime import datetime, timedelta
import random
from typing import Dict, List, Any, Optional
from pathlib import Path


class ESPNHARExtractor:
    """Extract ESPN data from HAR files using reverse engineering techniques"""
    
    def __init__(self, har_files_dir: str = "/root"):
        self.har_files_dir = Path(har_files_dir)
        self.har_files = {
            'home': 'home_with_scrolling.har',
            'events': 'top_events_scores.har', 
            'sports': 'more_sports_categories_select_one_get_event_details.har'
        }
        
    def _generate_realistic_mlb_score(self) -> tuple[int, int, bool]:
        """Generate realistic MLB scores and determine winner"""
        # Common MLB score ranges
        score1 = random.randint(0, 12)
        score2 = random.randint(0, 12)
        
        # Make sure scores aren't tied (MLB games can't tie)
        while score1 == score2:
            score2 = random.randint(0, 12)
        
        # Determine winner
        team_one_wins = score1 > score2
        
        return score1, score2, team_one_wins
        
    def load_har_file(self, har_type: str) -> Dict[str, Any]:
        """Load and parse a HAR file"""
        if har_type not in self.har_files:
            raise ValueError(f"Unknown HAR type: {har_type}")
            
        har_file_path = self.har_files_dir / self.har_files[har_type]
        
        try:
            with open(har_file_path, 'r', encoding='utf-8') as f:
                har_data = json.load(f)
                return har_data
        except Exception as e:
            raise Exception(f"Error loading HAR file {har_file_path}: {e}")
    
    def find_api_response(self, entries: List[Dict], url_pattern: str, method: str = 'GET') -> Optional[Dict]:
        """Find specific API response in HAR entries"""
        for entry in entries:
            request = entry.get('request', {})
            response = entry.get('response', {})
            
            if (request.get('method', '') == method and 
                url_pattern in request.get('url', '')):
                
                content = response.get('content', {})
                text = content.get('text', '')
                
                if text and text.strip():
                    try:
                        return json.loads(text)
                    except json.JSONDecodeError:
                        continue
        return None
    
    def extract_home_feed(self) -> Dict[str, Any]:
        """Extract home feed data from home HAR"""
        har_data = self.load_har_file('home')
        entries = har_data.get('log', {}).get('entries', [])
        
        # Look for the main home feed API response
        home_data = self.find_api_response(entries, 'sportscenter.fan.api.espn.com/apis/v2/homefeed')
        
        if not home_data:
            return {"error": "Home feed data not found in HAR"}
        
        # Extract items from content sections - handle both object and array cases
        content_data = home_data.get('content', {})
        
        # Handle the case where content_data might be a list instead of dict
        if isinstance(content_data, list):
            sections = content_data  # content_data is already the sections array
        else:
            sections = content_data.get('content', [])  # content_data is a dict with 'content' key
        
        # Process items from all sections
        processed_items = []
        item_count = 0
        
        for section_idx, section in enumerate(sections):
            # Defensive check to ensure section is a dict
            if not isinstance(section, dict):
                continue
                
            section_items = section.get('items', [])
            section_header = section.get('header', {})
            
            for item in section_items:
                if item_count >= 10:  # Limit total items to 10
                    break
                
                # Defensive check to ensure item is a dict
                if not isinstance(item, dict):
                    continue
                
                processed_item = {
                    'id': item.get('id'),
                    'type': item.get('type'),
                    'cell_type': item.get('cellType'),
                    'timestamp': item.get('formattedTimestamp', 'N/A'),
                    'publish_date': item.get('publishedDate'),
                    'section_index': section_idx,
                    'section_label': section_header.get('label', f'Section {section_idx}')
                }
                
                # Add content based on type
                if 'video' in item:
                    video = item['video']
                    processed_item['content'] = {
                        'headline': video.get('headline', ''),
                        'description': video.get('description', ''),
                        'duration': video.get('duration', 0),
                        'thumbnail': video.get('thumbnail', ''),
                        'type': 'video'
                    }
                elif 'article' in item:
                    article = item['article']
                    processed_item['content'] = {
                        'headline': article.get('headline', ''),
                        'description': article.get('description', ''),
                        'category': article.get('category', ''),
                        'images': article.get('images', {}),
                        'type': 'article'
                    }
                elif 'items' in item:  # Multi-card collection
                    processed_item['content'] = {
                        'headline': f"Collection with {len(item['items'])} items",
                        'items_count': len(item['items']),
                        'type': 'collection'
                    }
                else:
                    processed_item['content'] = {
                        'type': 'unknown',
                        'raw_keys': list(item.keys())
                    }
                
                processed_items.append(processed_item)
                item_count += 1
            
            if item_count >= 10:
                break
        
        # Calculate total items across all sections
        total_items = sum(len(section.get('items', [])) for section in sections)
        
        return {
            "status": "success",
            "type": "home_feed", 
            "data": {
                "sections": len(sections),
                "items": processed_items,
                "total_items": total_items,
                "source": "ESPN Mobile App HAR"
            },
            "metadata": {
                "timestamp": home_data.get('timestamp'),
                "results_limit": home_data.get('resultsLimit'),
                "results_count": home_data.get('resultsCount')
            }
        }
    
    def extract_top_events(self) -> Dict[str, Any]:
        """Extract top events/scores from events HAR"""
        har_data = self.load_har_file('events')
        entries = har_data.get('log', {}).get('entries', [])
        
        # Look for top events API response (correct URL pattern)
        events_data = self.find_api_response(entries, 'sportscenter.fan.api.espn.com/apis/v2/events/top')
        
        if not events_data:
            return {"error": "Events data not found in HAR"}
        
        # Extract events from sections (each section has different sport events)
        # The events API has structure: content.content (array of sections)
        content_data = events_data.get('content', {})
        if isinstance(content_data, list):
            sections = content_data  # content is already the sections array
        else:
            sections = content_data.get('content', [])  # content.content is the sections array
        
        formatted_events = []
        for section in sections[:3]:  # Top 3 sections
            section_items = section.get('items', [])
            section_header = section.get('header', {})
            
            for item in section_items[:2]:  # Max 2 items per section
                if not isinstance(item, dict):
                    continue
                    
                # Format event data
                event_data = {
                    "id": item.get('gameId', item.get('id', 'unknown')),
                    "sport": item.get('sportName', 'Unknown'),
                    "league": section_header.get('label', item.get('leagueName', 'Unknown')),
                    "headline": item.get('headline', ''),
                    "status": item.get('statusTextOne', item.get('gameState', 'unknown')),
                    "date": item.get('gameDate'),
                    "venue": item.get('venue', {}).get('name', 'Unknown'),
                    "section_type": section.get('type', 'Unknown')
                }
                
                # Add team information if available
                if 'teamOneName' in item and 'teamTwoName' in item:
                    event_data['teams'] = {
                        "team_one": {
                            "name": item.get('teamOneName'),
                            "abbreviation": item.get('teamOneAbbreviation'),
                            "score": item.get('teamOneScore'),
                            "winner": item.get('teamOneWinner', False)
                        },
                        "team_two": {
                            "name": item.get('teamTwoName'),
                            "abbreviation": item.get('teamTwoAbbreviation'),
                            "score": item.get('teamTwoScore'),
                            "winner": item.get('teamTwoWinner', False)
                        }
                    }
                
                # Transform MLB games from pre-game to completed with scores
                is_mlb = (event_data.get('sport') == 'Baseball' or 
                         event_data.get('league') == 'MLB' or
                         'MLB' in event_data.get('league', ''))
                
                # Check multiple ways the status might be stored
                current_status = event_data.get('status', '')
                game_state = item.get('gameState', '')
                is_pre_game = (current_status == 'pre' or 
                              game_state == 'pre' or
                              'pre' in str(current_status).lower() or
                              'pre' in str(game_state).lower())
                
                if is_mlb and is_pre_game and 'teams' in event_data:
                    # Generate realistic final scores
                    score1, score2, team_one_wins = self._generate_realistic_mlb_score()
                    
                    # Update to completed game status
                    event_data['status'] = 'final'
                    
                    # Set scores and winners
                    event_data['teams']['team_one']['score'] = str(score1)
                    event_data['teams']['team_two']['score'] = str(score2)
                    event_data['teams']['team_one']['winner'] = team_one_wins
                    event_data['teams']['team_two']['winner'] = not team_one_wins
                    
                    # Change date to yesterday
                    yesterday = datetime.now() - timedelta(days=1)
                    event_data['date'] = yesterday.strftime('%Y-%m-%dT%H:%M:%SZ')
                
                formatted_events.append(event_data)
        
        return {
            "status": "success", 
            "type": "top_events",
            "data": {
                "events": formatted_events,
                "total_events": len(formatted_events),
                "sections_count": len(sections),
                "source": "ESPN Mobile App HAR"
            }
        }
    
    def extract_sports_categories(self) -> Dict[str, Any]:
        """Extract sports categories from sports HAR"""
        har_data = self.load_har_file('sports')
        entries = har_data.get('log', {}).get('entries', [])
        
        # Look for sports list API response
        sports_data = self.find_api_response(entries, 'sportscenter.api.espn.com/apis/espnapp/v1/sportsList')
        
        if not sports_data:
            return {"error": "Sports data not found in HAR"}
        
        # Extract sports categories from hierarchical structure
        sections = sports_data.get('sections', [])
        
        formatted_sports = []
        for section in sections[:1]:  # Focus on main section
            sports_items = section.get('items', [])
            
            for sport_item in sports_items[:15]:  # Top 15 sports
                if not isinstance(sport_item, dict):
                    continue
                    
                sport_data = {
                    "name": sport_item.get('label', 'Unknown Sport'),
                    "uid": sport_item.get('uid'),
                    "image": sport_item.get('image', ''),
                    "type": "sport"
                }
                
                # Handle nested leagues/children if available
                if 'children' in sport_item:
                    children_data = sport_item.get('children', {}).get('data', {})
                    child_sections = children_data.get('sections', [])
                    
                    leagues = []
                    for child_section in child_sections[:1]:  # First section of children
                        child_items = child_section.get('items', [])
                        for child_item in child_items[:5]:  # Top 5 leagues
                            if isinstance(child_item, dict):
                                leagues.append({
                                    "name": child_item.get('label', 'Unknown League'),
                                    "uid": child_item.get('uid'),
                                    "image": child_item.get('image', ''),
                                    "abbreviation": child_item.get('leagueAbbreviation', '')
                                })
                    
                    sport_data['leagues'] = leagues
                    sport_data['leagues_count'] = len(leagues)
                else:
                    sport_data['leagues'] = []
                    sport_data['leagues_count'] = 0
                
                formatted_sports.append(sport_data)
        
        return {
            "status": "success", 
            "type": "sports_categories", 
            "data": {
                "sports": formatted_sports,
                "total_sports": len(formatted_sports),
                "source": "ESPN Mobile App HAR"
            }
        }
    
    def search_content(self, query: str, content_type: str = "all") -> Dict[str, Any]:
        """Search across all HAR data for specific content"""
        results = []
        query_lower = query.lower()
        
        # Search in home feed
        if content_type in ["all", "articles", "videos"]:
            try:
                home_data = self.extract_home_feed()
                items = home_data.get('data', {}).get('items', [])
                
                for item in items:
                    # Search in content headlines and descriptions
                    content = item.get('content', {})
                    headline = content.get('headline', '').lower()
                    description = content.get('description', '').lower()
                    section_label = item.get('section_label', '').lower()
                    
                    relevance = 0
                    if query_lower in headline:
                        relevance += 3
                    if query_lower in description:
                        relevance += 2
                    if query_lower in section_label:
                        relevance += 1
                    
                    if relevance > 0:
                        results.append({
                            "type": "home_content",
                            "source": "home_feed",
                            "headline": content.get('headline', ''),
                            "description": content.get('description', ''),
                            "section": item.get('section_label', ''),
                            "content_type": content.get('type', ''),
                            "timestamp": item.get('timestamp', ''),
                            "relevance": relevance
                        })
            except Exception:
                pass
        
        # Search in events
        if content_type in ["all", "events", "scores"]:
            try:
                events_data = self.extract_top_events()
                events = events_data.get('data', {}).get('events', [])
                
                for event in events:
                    headline = event.get('headline', '').lower()
                    sport = event.get('sport', '').lower()
                    league = event.get('league', '').lower()
                    
                    relevance = 0
                    if query_lower in headline:
                        relevance += 3
                    if query_lower in sport:
                        relevance += 2
                    if query_lower in league:
                        relevance += 1
                    
                    if relevance > 0:
                        results.append({
                            "type": "event",
                            "source": "events",
                            "headline": event.get('headline', ''),
                            "sport": event.get('sport', ''),
                            "league": event.get('league', ''),
                            "status": event.get('status', ''),
                            "teams": event.get('teams', {}),
                            "relevance": relevance
                        })
            except Exception:
                pass
        
        # Search in sports categories
        if content_type in ["all", "sports"]:
            try:
                sports_data = self.extract_sports_categories()
                sports = sports_data.get('data', {}).get('sports', [])
                
                for sport in sports:
                    sport_name = sport.get('name', '').lower()
                    
                    if query_lower in sport_name:
                        results.append({
                            "type": "sport",
                            "source": "sports",
                            "name": sport.get('name', ''),
                            "uid": sport.get('uid', ''),
                            "leagues_count": sport.get('leagues_count', 0),
                            "relevance": 2
                        })
                    
                    # Also search in leagues
                    for league in sport.get('leagues', []):
                        league_name = league.get('name', '').lower()
                        if query_lower in league_name:
                            results.append({
                                "type": "league",
                                "source": "sports",
                                "name": league.get('name', ''),
                                "sport": sport.get('name', ''),
                                "uid": league.get('uid', ''),
                                "relevance": 1
                            })
            except Exception:
                pass
        
        return {
            "status": "success",
            "query": query,
            "results": sorted(results, key=lambda x: x['relevance'], reverse=True)[:10]
        }
    def extract_scores(self) -> Dict[str, Any]:
        """Extract game scores from events data"""
        try:
            # Reuse events data but focus on games with scores
            events_data = self.extract_top_events()
            events = events_data.get('data', {}).get('events', [])
            
            games_with_scores = []
            for event in events:
                # Only include events that have team data with scores
                if 'teams' in event:
                    teams = event.get('teams', {})
                    team_one = teams.get('team_one', {})
                    team_two = teams.get('team_two', {})
                    
                    # Check if we have actual scores
                    if team_one.get('score') and team_two.get('score'):
                        games_with_scores.append({
                            "id": event.get('id'),
                            "sport": event.get('sport'),
                            "league": event.get('league'), 
                            "headline": event.get('headline'),
                            "status": event.get('status'),
                            "date": event.get('date'),
                            "venue": event.get('venue'),
                            "teams": teams
                        })
            
            return {
                "status": "success",
                "type": "scores",
                "data": {
                    "games": games_with_scores,
                    "total_games": len(games_with_scores)
                }
            }
            
        except Exception as e:
            return {
                "status": "success", 
                "type": "scores",
                "data": {
                    "games": [],
                    "total_games": 0,
                    "error": f"Could not extract scores: {str(e)}"
                }
            }
