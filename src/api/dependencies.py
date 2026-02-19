from fastapi import Depends

def common_parameters(limit: int = 10, offset: int = 0):
    """
    Common query parameters for pagination.
    """
    return {"limit": limit, "offset": offset}