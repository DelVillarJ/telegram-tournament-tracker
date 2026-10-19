"""Client for TopDeck.gg's Tournaments V2 API."""

import logging
from typing import Any, Dict, List, Optional, Union

import requests

logger = logging.getLogger(__name__)


class TopDeckAPI:
    """Client for TopDeck.gg's Tournaments V2 API."""

    def __init__(self, api_key: str, base_url: str = "https://topdeck.gg"):
        if not api_key.strip():
            raise ValueError("A TopDeck API key is required.")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.api_base_url = (
            self.base_url if self.base_url.endswith("/api") else f"{self.base_url}/api"
        )
        self.tournaments_url = f"{self.api_base_url}/v2/tournaments"
        self.my_tournaments_url = f"{self.api_base_url}/v2/me/tournaments?filter=all"
        self.headers = {
            "Authorization": self.api_key,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def get_my_tournaments(self) -> List[Dict[str, Any]]:
        """Return tournaments belonging to the account associated with this API key."""
        try:
            response = requests.get(
                self.my_tournaments_url,
                headers=self.headers,
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
        except requests.RequestException:
            logger.exception("TopDeck account tournaments request failed.")
            raise

        if not isinstance(data, list) or not all(
            isinstance(tournament, dict) for tournament in data
        ):
            raise ValueError(
                "TopDeck account tournaments endpoint returned an unexpected response."
            )
        return data

    def search_tournaments(
        self,
        tid: Optional[Union[str, List[str]]] = None,
        game: Optional[str] = None,
        format: Optional[str] = None,
        start: Optional[int] = None,
        end: Optional[int] = None,
        last: Optional[int] = None,
        participant_min: Optional[int] = None,
        participant_max: Optional[int] = None,
        columns: Optional[List[str]] = None,
        rounds: Union[bool, List[str]] = False,
        tables: Optional[List[str]] = None,
        players: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Search completed tournaments using the documented V2 request fields."""
        payload: Dict[str, Any] = {}

        if tid is not None:
            if isinstance(tid, str):
                valid_tid = bool(tid.strip())
            else:
                valid_tid = bool(tid) and all(
                    isinstance(tournament_id, str) and tournament_id.strip()
                    for tournament_id in tid
                )
            if not valid_tid:
                raise ValueError("TID must be a non-empty string or list of strings.")
            payload["TID"] = tid
        else:
            if game is None or not game.strip() or format is None:
                raise ValueError(
                    "Both game and format are required when TID is not provided."
                )
            payload["game"] = game
            payload["format"] = format

            if last is not None and (start is not None or end is not None):
                raise ValueError("Use last or start/end; they cannot be combined.")
            if start is not None:
                payload["start"] = start
            if end is not None:
                payload["end"] = end
            if last is not None:
                payload["last"] = last
            if participant_min is not None:
                payload["participantMin"] = participant_min
            if participant_max is not None:
                payload["participantMax"] = participant_max

        if columns is not None:
            payload["columns"] = columns
        if rounds:
            payload["rounds"] = rounds
        if tables is not None:
            payload["tables"] = tables
        if players is not None:
            payload["players"] = players

        try:
            response = requests.post(
                self.tournaments_url,
                json=payload,
                headers=self.headers,
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
        except requests.RequestException:
            logger.exception("TopDeck Tournaments V2 request failed.")
            raise

        if not isinstance(data, list) or not all(
            isinstance(tournament, dict) for tournament in data
        ):
            raise ValueError("TopDeck Tournaments V2 returned an unexpected response.")
        return data
