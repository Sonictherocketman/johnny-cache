from .server import app

# Bootstrap for Gunicorn
application = app  # noqa

if __name__ == "__main__":
    app.run()
