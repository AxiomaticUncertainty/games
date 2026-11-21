"""Rooms: where players gather to play one game together.

`registry` keeps track of the rooms and who has a seat in each. `routes` is
the HTTP API for listing, creating, joining, and leaving them.

There are no accounts, only the shared site password, so a seat is how the
server knows a player. Joining gives you a seat with a display name and a
secret token. The token lets you take your seat back after a refresh or a
dropped connection, rather than joining again as someone new.
"""
