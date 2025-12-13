from src.app import JournalController, EntryController
from litestar import Litestar


def main():
    print("Hello World")

app = Litestar(route_handlers=[EntryController, JournalController])
    
    # main()
