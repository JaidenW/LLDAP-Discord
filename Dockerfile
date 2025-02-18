# Use the full Python image instead of the slim version
FROM python:3.12

# Set the working directory
WORKDIR /usr/src/app

# Copy application files
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Run the bot
CMD ["python", "main.py"]
