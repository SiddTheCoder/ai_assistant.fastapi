from app.features.app_features.open_app import open_app
from app.features.web_features.search_web import search_web




def play_song(details):
    print(f"🎵 Playing: {details['query']}")
    # code to call your music handler

def make_call(details):
    print(f"📞 Calling {details['target']} via {details.get('platforms', ['phone'])[0]}")
    # code to trigger phone call function

def message(details):
    print(f"💬 Sending message: {details['additional_info'].get('message_content', '')} to {details['target']}")
    # your message sending logic



# Default handler
def unknown_action(details):
    print(f"⚠️ Unknown action type: {details.actionDetails.type}")


# Dispatcher map
ACTION_MAP = {
    "play_song": play_song,
    "make_call": make_call,
    "message": message,
    "search": search_web,
    "open_app": open_app,
    "unknown": unknown_action
}


def dispatch_action(action_type, details):
    """
    Dynamically calls the correct handler function
    based on 'actionDetails.type'.
    """
    handler = ACTION_MAP.get(action_type, unknown_action)
    if(handler != unknown_action):
        handler(details)
    else :    
        unknown_action(details)
