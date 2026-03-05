from .user import UserModel
from .chat import ChatModel
from .mood import MoodModel
from .stress import StressModel
from .grievance import GrievanceModel
from .parent import ParentModel
from .connect_hub import (
    ConnectionModel, GroupModel, EventModel, ResourceModel,
    HubActivityModel, PeerMessageModel, GroupMessageModel,
    HubFeedModel, HubNotificationModel
)

def init_models():
    """Registry of all model classes for MongoDB."""
    return {
        'UserModel': UserModel,
        'ChatModel': ChatModel,
        'MoodModel': MoodModel,
        'StressModel': StressModel,
        'GrievanceModel': GrievanceModel,
        'ParentModel': ParentModel,
        'ConnectionModel': ConnectionModel,
        'GroupModel': GroupModel,
        'EventModel': EventModel,
        'ResourceModel': ResourceModel,
        'HubActivityModel': HubActivityModel,
        'PeerMessageModel': PeerMessageModel,
        'GroupMessageModel': GroupMessageModel,
        'HubFeedModel': HubFeedModel,
        'HubNotificationModel': HubNotificationModel,
    }
