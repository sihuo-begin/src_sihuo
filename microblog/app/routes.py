from flask import render_template, flash, redirect, url_for
from app import app
from .forms import LoginForm


@app.route('/')
@app.route('/index')
def index():
    user = {"username": "Simon"}
    posts = [
        {
            'author': {'username': 'John'},
            'body': 'Beautiful day in Portland!'
        },
        {
            'author': {'username': 'Susan'},
            'body': 'The Avenger movie was so cool'
        },
    ]
    # return render_template('index.html', title='Home', user=user)
    return render_template('index.html', title='Home', user=user, posts=posts)
    # return '''
# <html>
#     <head>
#         <title>Home Page - Microblog</title>
#     </head>
#     <body>
#         <h1>Hello, '''+ user["user_name"] + '''!</h1>
#     </body>
# </html>'''
@app.route("/login", methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        flash("Login request for user {}, remember_me={}".format(form.username.data, form.remember_me.data))
        return redirect(url_for('index'))
    return render_template('login.html', title='Sign In', form=form)

