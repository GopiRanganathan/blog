from datetime import date
from flask import Flask, abort, render_template, redirect, url_for, flash, request
from flask_bootstrap import Bootstrap5
from flask_ckeditor import CKEditor
# from flask_gravatar import Gravatar
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user, login_required
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm import relationship, Mapped, mapped_column
from functools import wraps
import sqlalchemy
# Import your forms from the forms.py
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm
import hashlib

'''
Make sure the required packages are installed: 
Open the Terminal in PyCharm (bottom left). 

On Windows type:
python -m pip install -r requirements.txt

On MacOS type:
pip3 install -r requirements.txt

This will install the packages from the requirements.txt for this project.
'''

app = Flask(__name__)
app.secret_key = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap5(app)

# TODO: Configure Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)


# CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///posts.db'
db = SQLAlchemy()
db.init_app(app)

def gravatar_url(email, size=100, rating='g', default='retro', force_default=False):
    hash_value = hashlib.md5(email.lower().encode('utf-8')).hexdigest()
    return f"https://www.gravatar.com/avatar/{hash_value}?s={size}&d={default}&r={rating}&f={force_default}"    
# CONFIGURE TABLES
class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    author_id = db.Column(db.Integer, db.ForeignKey("Users.id"))
    author = relationship("User", back_populates="posts")
    # author_id: Mapped[int] = mapped_column(db.ForeignKey("Users.id"))
    # author: Mapped["User"] = relationship(back_populates="posts")
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), unique=True, nullable=False)
    # author = db.Column(db.String(250), nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    comments = relationship("Comment", back_populates="parent_post")


# TODO: Create a User table for all your registered users. 
class User(db.Model, UserMixin):
    __tablename__ = "Users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(250), nullable=False)
    email = db.Column(db.String(250), unique=True, nullable=False)
    password = db.Column(db.String(400), nullable=False)
    posts = relationship("BlogPost", back_populates="author")
    comments = relationship("Comment", back_populates="comment_author")
    # posts: Mapped[list["BlogPost"]] = relationship(back_populates="author")

class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    comment_author = relationship("User", back_populates="comments")
    author_id = db.Column(db.Integer, db.ForeignKey("Users.id"))
    post_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"))
    parent_post = relationship("BlogPost", back_populates="comments")



with app.app_context():
    db.create_all()


# TODO: Use Werkzeug to hash the user's password when creating a new user.
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        new_user = User(
            name=form.name.data,
            email = form.email.data,
            password = generate_password_hash(form.password.data, method='pbkdf2', salt_length=8)
        )
        try:
            db.session.add(new_user)
            db.session.commit()
        except sqlalchemy.exc.IntegrityError:
            flash("You are already signed up. Please Log in.")
            return redirect(url_for('login'))

        return redirect(url_for('get_all_posts'))
    return render_template("register.html", form=form, logged_in=current_user.is_authenticated)


# TODO: Retrieve a user from the database based on their email. 
@login_manager.user_loader
def load_user(user_id):
    return db.get_or_404(User, user_id)



def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.id != 1:
            return abort(403)
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.execute(db.select(User).where(User.email == form.email.data)). scalar()
        if user:
            if check_password_hash(user.password, form.password.data):
                flash("You're succesfully logged in")
                login_user(user)
                return redirect(url_for('get_all_posts'))
            else:
                flash("Invalid Password")
        else:
            flash("Email doesn't exist! Please Sign Up.")
            return redirect(url_for('register'))
    return render_template("login.html", form=form, logged_in=current_user.is_authenticated)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route('/')
def get_all_posts():
    result = db.session.execute(db.select(BlogPost))
    posts = result.scalars().all()
    return render_template("index.html" , all_posts=posts, logged_in=current_user.is_authenticated)


# TODO: Allow logged-in users to comment on posts
@app.route("/post/<int:post_id>", methods = ['POST', 'GET'])
def show_post(post_id):
    requested_post = db.get_or_404(BlogPost, post_id)
    form = CommentForm()
    if form.validate_on_submit():
        if not current_user.is_authenticated:
            flash('Please log in to comment on the post.')
            return redirect(url_for('login'))
        else:
            new_comment = Comment(
                text=form.comment.data,
                comment_author = current_user,
                parent_post = requested_post
            )
            db.session.add(new_comment)
            db.session.commit()
    return render_template("post.html", post=requested_post, form=form, logged_in=current_user.is_authenticated, gravatar=gravatar_url)


# TODO: Use a decorator so only an admin user can create a new post

@app.route("/new-post", methods=["GET", "POST"])
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form, logged_in=current_user.is_authenticated)


# TODO: Use a decorator so only an admin user can edit a post
@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
@admin_only
def edit_post(post_id):
    post = db.get_or_404(BlogPost, post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author = current_user
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))
    return render_template("make-post.html", form=edit_form, is_edit=True, logged_in=current_user.is_authenticated)


# TODO: Use a decorator so only an admin user can delete a post
@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = db.get_or_404(BlogPost, post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'), logged_in=current_user.is_authenticated)


@app.route("/about")
def about():
    return render_template("about.html", logged_in=current_user.is_authenticated)


@app.route("/contact")
def contact():
    return render_template("contact.html", logged_in=current_user.is_authenticated)


if __name__ == "__main__":
    app.run(debug=True, port=5001)
