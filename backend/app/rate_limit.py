"""Instancia única de rate limiter, compartida por toda la app.

Importante: se define UNA sola vez aquí y se importa desde donde haga
falta, en vez de crear un Limiter() distinto en cada archivo — así todos
los endpoints comparten el mismo almacén de límites por IP.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
