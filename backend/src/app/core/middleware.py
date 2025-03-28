from functools import wraps
from dependency_injector.wiring import inject as di_inject
from app.services.base_service import BaseService


def inject(func):
    @di_inject
    @wraps(func)
    async def wrapper(*args, **kwargs):
        result = await func(*args, **kwargs)
        injected_services = [arg for arg in kwargs.values() if isinstance(arg, BaseService)]
        if len(injected_services) == 0:
            return result
        else:
            try:
                await injected_services[-1].close_scoped_session()
            except Exception as e:
                print(e)

        return result

    return wrapper
