from .user import UserModel
from .chat import ChatModel
from .mood import MoodModel
from .stress import StressModel

def init_models():
    # Placeholder: models are defined as schema helpers for MongoDB
    return {
        'UserModel': UserModel,
        'ChatModel': ChatModel,
        'MoodModel': MoodModel,
        'StressModel': StressModel,
    }
