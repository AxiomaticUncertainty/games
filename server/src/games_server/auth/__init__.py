"""Site-wide password gate.

The whole site sits behind one shared password. The pieces:

- `tokens`: issues and checks the signed session cookie.
- `gate`: middleware that turns away any request without a valid cookie.
- `throttle`: limits failed login attempts per client.
- `routes`: the login and logout endpoints.
"""
