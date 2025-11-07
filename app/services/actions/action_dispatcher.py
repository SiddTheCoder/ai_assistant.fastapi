from app.features.app_features.open_app import open_app


# {
#   "answer": "string",
#   "action": "string",
#   "emotion": "neutral",
#   "actionDetails": {
#     "type": "string", [e.g., "play_song", "make_call", "message", "search", "open_app", or "" if none]
#     "query": "string",
#     "title": "string",
#     "artist": "string",
#     "topic": "string",
#     "platforms": [
#       "string"
#     ],
#     "app_name": "string",
#     "target": "string",
#     "location": "string",
#     "confirmation": {
#       "isConfirmed": true,
#       "actionRegardingQuestion": "string"
#     },
#     "additional_info": {
#       "additionalProp1": {}
#     }
#   }
# }

def play_song(details):
    print(f"🎵 Playing: {details['query']}")
    # code to call your music handler

def make_call(details):
    print(f"📞 Calling {details['target']} via {details.get('platforms', ['phone'])[0]}")
    # code to trigger phone call function

def message(details):
    print(f"💬 Sending message: {details['additional_info'].get('message_content', '')} to {details['target']}")
    # your message sending logic

def search(details):
    print(f"🔍 Searching for: {details['query']}")
    # open browser or search system

# def open_app(details):
#     print(f"📂 Opening app: {details['app_name']}")
#     # your app opener logic

# Default handler
def unknown_action(details):
    print(f"⚠️ Unknown action type: {details.get('type')}")


# Dispatcher map
ACTION_MAP = {
    "play_song": play_song,
    "make_call": make_call,
    "message": message,
    "search": search,
    "open_app": open_app
}


def dispatch_action(action_type, details):
    """
    Dynamically calls the correct handler function
    based on 'actionDetails.type'.
    """
    handler = ACTION_MAP.get(action_type, unknown_action)
    handler(details)
