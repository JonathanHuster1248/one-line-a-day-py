This is a pet project by Jonathan Huster to make a digital one line a day journal book like the [5 year journal](https://www.amazon.com/One-Line-Day-Five-Year-Memory/dp/0811870197). 

To run the main API call 

```
python -m one_line_day_py.main
```

A Docker implementation also exists. Run the build command below to create the image then run the run command to use that image:

```
docker build . -t one-line-a-day:latest
docker run -p 127.0.0.1:8000:8000 one-line-a-day:latest
```