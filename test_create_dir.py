import os
from pathlib import Path


def tool_create_directory(target_name):
    """
    Creates a folder on the user's Desktop.
    :param target_name: Name of the folder to create.
    :return: Dictionary matching our output_schema.
    """
    try:
        # 1. Automatically find the Desktop path for any OS
        # desktop_path = Path.home() / "Desktop" / target_name
        desktop_path = "D:/siddhant-files/projects/ai_assistant/ai-server"
        
        # 2. Create the directory
        # exist_ok=True prevents errors if the folder already exists
        os.makedirs(desktop_path, exist_ok=True)
        
        return {
            "success": True,
            "actionCompletedMessage": f"Successfully created folder: {target_name}",
            "data": {
                "path": str(desktop_path),
                "created_at": str(Path(desktop_path).stat().st_ctime)
            }
        }
    except Exception as e:
        return {
            "success": False,
            "actionCompletedMessage": f"Failed to create folder. Error: {str(e)}",
            "data": None
        }

# Example Usage:
result = tool_create_directory("Secret_Project")
print(result)

print(Path.home()/"Desktop")