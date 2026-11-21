"""Rooms: where players gather to play one game together.

`registry` keeps track of the rooms, who has a seat in each, and who is
connected. `routes` is the API: HTTP for listing, creating, joining, and
leaving rooms, and a WebSocket for following one live. `connection` is a
player's live connection, and `views` is how rooms look from outside.

There are no accounts, only the shared site password, so a seat is how the
server knows a player. Joining gives you a seat with a display name and a
secret token. The token lets you take your seat back after a refresh or a
dropped connection, rather than joining again as someone new.
"""
