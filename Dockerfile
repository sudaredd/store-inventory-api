# Use an official lightweight Python image.
# https://hub.docker.com/_/python
FROM python:3.10-slim

# Allow statements and log messages to immediately appear in the Knative logs
ENV PYTHONUNBUFFERED True

# Copy local code to the container image.
ENV APP_HOME /app
WORKDIR $APP_HOME
COPY . ./

# Install production dependencies.
RUN pip install --no-cache-dir -r requirements.txt

# Run the web service on container startup. 
# We run init_db.py first to ensure the database schema exists.
# Then we start the Flask app using gunicorn (better for production than python main.py).
CMD python init_db.py && exec gunicorn --bind :8080 --workers 1 --threads 8 --timeout 0 main:app
