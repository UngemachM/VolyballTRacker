# src/modules/data/models.py

from dataclasses import dataclass, field
from typing import Optional, List
import datetime

@dataclass
class Player:
    """Definiert einen einzelnen Spieler."""
    name: str
    jersey_number: Optional[int] = None
    player_id: Optional[int] = None 
    position: Optional[str] = None

@dataclass
class Team:
    """Definiert ein Team (eigen oder gegnerisch)."""
    name: str
    team_id: Optional[int] = None

@dataclass
class Game:
    """Definiert ein einzelnes Spiel."""
    date_time: datetime.datetime
    home_team_id: int
    guest_team_id: int
    game_id: Optional[int] = None

@dataclass
class Set:
    """Definiert einen Satz innerhalb eines Spiels."""
    game_id: int
    set_number: int  # 1, 2, 3, etc.
    score_own: int = 0
    score_opponent: int = 0
    set_id: Optional[int] = None

@dataclass
class Action:
    """
    Definiert eine einzelne Aktion/Statistik-Eingabe.
    """
    set_id: int
    action_type: str        
    executor_player_id: int 
    
    # Ergebnis-Details
    result_type: Optional[str] = None   
    
    # NEU: Detaillierte Angaben zum Punktgewinn/-verlust
    point_detail_type: Optional[str] = None # Dieses Feld wurde hinzugefügt
    
    # Nur relevant für 'Zuspiel zu' oder Block/Punkt des Gegners
    target_player_id: Optional[int] = None 
    
    # Punktwert (für 'Unser Punkt' oder automatische Punkte)
    point_for: Optional[str] = None 
    
    timestamp: datetime.datetime = field(default_factory=datetime.datetime.now)
    action_id: Optional[int] = None