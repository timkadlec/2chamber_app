from app import create_app


# Create the app using the config class
app = create_app()


if __name__ == "__main__":
    app.run(host="localhost", port=5000)
