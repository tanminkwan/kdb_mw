Step-by-Step Dockerfile Creation

#### 1. Create requirements.txt

```pip freeze > requirements.txt```

#### 2. Create the Base Image

The base image will include all necessary libraries and settings but exclude the source code.

Dockerfile for Base Image

```Dockerfile

# Base Image
FROM python:3.12.4-slim-bookworm

# Set working directory
WORKDIR /app

# Install git and other dependencies
RUN apt-get update && apt-get install -y git && apt-get clean

# Copy necessary files
COPY requirements.txt requirements.txt

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# The base image does not define a CMD or ENTRYPOINT
# It will be defined in the final image Dockerfile
```

Build the base image using this Dockerfile.

```bash
docker build -t mwm-base -f Dockerfile.base .
```
#### 3. Create the App Image

The final image will use the base image, add the source code, and set up the web server to run.

Dockerfile for App Image

```Dockerfile

# Use the base image
FROM mwm-base

# Set working directory (should match the base image's WORKDIR)
WORKDIR /app

# Copy the source code
COPY app app
COPY config.py config.py
COPY run.py run.py

# Copy Gunicorn configuration file
COPY gunicorn_config.py gunicorn_config.py

# Expose the port the application will run on
EXPOSE 8000

# Use Gunicorn to run the application
CMD ["gunicorn", "-c", "gunicorn_config.py", "app:app"]
```

Build the final image using this Dockerfile.

```bash
docker build -t mwm-app -f Dockerfile.app .
```
Example Directory Structure

Your project directory structure should look like this:

```arduino

myapp/
│
├── app/
│   ├── __init__.py
│   ├── ...
│
├── Dockerfile.base
├── Dockerfile.app
├── requirements.txt
├── config.py
├── run.py
└── gunicorn_config.py
```

Try to run the App
`docker run -d -p 8000:8000 -e MWM_DATABASE_URI=172.17.0.1:5432 mwm-app`

#### 4. Summary

- Build the Base Image: The base image includes all necessary libraries and configurations except the source code. Use Dockerfile.base for this.
- Build the App Image: The app image is built on top of the base image and includes the application source code. Use Dockerfile.App for this.
- Image Management: By separating the source code and dependencies, you can manage and update them independently, making builds faster and more efficient.

This setup allows for better separation of concerns and faster build times when the source code changes.