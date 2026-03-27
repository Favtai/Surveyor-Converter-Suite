# Use official Python image
FROM python:3.11

# Set up a new user named "user" with user ID 1000
RUN useradd -m -u 1000 user
USER user

# Set environment variables
ENV PATH="/home/user/.local/bin:$PATH"
WORKDIR /app

# Copy requirements and install them
COPY --chown=user requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your app's code
COPY --chown=user . /app

# Expose the Hugging Face port
EXPOSE 7860

# Command to run the application
CMD ["python", "main.py"]
