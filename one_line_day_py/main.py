from .src.app import JournalController, EntryController
from litestar import Litestar


def main():
    print("Hello World")

def make_app():
    return Litestar(route_handlers=[EntryController, JournalController])
    
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "one_line_day_py.main:make_app",
        factory=True,
        port=8000,
        reload=True,
    )