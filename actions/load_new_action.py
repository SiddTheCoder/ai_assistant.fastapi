# import importlib.util
# import os

# if os.path.exists("new_action_handlers.py"):
#     spec = importlib.util.spec_from_file_location("new_action_handlers", "new_action_handlers.py")
#     new_actions = importlib.util.module_from_spec(spec)
#     spec.loader.exec_module(new_actions)
#     ACTION_MAP.update({
#         name: getattr(new_actions, name)
#         for name in dir(new_actions)
#         if callable(getattr(new_actions, name)) and not name.startswith("_")
#     })