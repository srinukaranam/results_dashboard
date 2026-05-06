from app import create_app
import os

# Get environment from FLASK_ENV, default to 'development'
env = os.environ.get("FLASK_ENV", "development")
app = create_app(env)

if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "True").lower() == "true"
    app.run(debug=debug, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
