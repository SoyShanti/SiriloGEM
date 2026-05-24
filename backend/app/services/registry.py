from backend.app.services.lm_studio import LMStudioClient
from backend.app.services.ace_step import ACEStepService
from backend.app.services.knowledge_base import KnowledgeBase
from backend.app.services.hit_predictor import HitPredictorService

lm_studio = LMStudioClient()
ace_step = ACEStepService()
knowledge_base = KnowledgeBase()
hit_predictor = HitPredictorService()
