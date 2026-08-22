"""FastAPI routers."""
from app.routers.verification import router as verification_router
from app.routers.prediction import router as prediction_router
from app.routers.policy_simulator import router as policy_simulator_router

__all__ = [
    "verification_router",
    "prediction_router",
    "policy_simulator_router",
]
