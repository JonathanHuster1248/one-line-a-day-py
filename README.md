This is a pet project by Jonathan Huster to make a digital one line a day journal book like the [5 year journal](https://www.amazon.com/One-Line-Day-Five-Year-Memory/dp/0811870197). 

To run the main API call 

```
python -m one_line_day_py.main
```

A Docker implementation also exists, with separate images for the backend (`backend.Dockerfile`) and frontend (`frontend/Dockerfile`). Use Docker Compose to build and run both together:

```
docker compose up --build
```

This serves the backend at `http://localhost:8000` and the frontend at `http://localhost:3000`, and bind-mounts `one_line_day_py/src/data/journal_entries.db` into the backend container so the database persists on the host.

To run the frontend cd to ./frontend and run 

`npm run dev`