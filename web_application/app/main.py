from flask import render_template, url_for
from app import webapp

@webapp.route('/')
def main():
    """
    Render the main page of the web application.

    Returns:
        Response: Rendered HTML template for the main page.
    """
    return render_template("main.html")