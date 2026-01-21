from app.client_core.utils.system_search import SystemSearcher

def find_app(app_name: str) :
    """
    Find the full path of an application by its name.
    """
    searcher = SystemSearcher()
    return searcher.find_app(app_name)


if __name__ == "__main__":
    print(find_app("camera"))  # Example usage  