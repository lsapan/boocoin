FROM python:3.6

WORKDIR /home/docker/code

# Install python dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Add the code
COPY . .

# Container configuration
CMD ["./manage.py", "runserver", "0.0.0.0:9811"]
EXPOSE 9811
