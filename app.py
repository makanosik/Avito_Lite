from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField
from wtforms.validators import DataRequired
from flask_wtf.file import FileField, FileRequired
import os
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/img/advertisements/'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///listings.db'
app.config['SECRET_KEY'] = 'your_secret_key'
db = SQLAlchemy(app)
current_datetime = datetime.now()
#formatted_time = current_datetime.strftime("%d.%m.%y %H.%M")

class Listing(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.String(100), nullable=False)
    image_filename = db.Column(db.String(150), nullable=True)
    formatted_time = db.Column(db.String(100), nullable=False)

class ListingForm(FlaskForm):
    title = StringField('Название', validators=[DataRequired()])
    description = TextAreaField('Описание', validators=[DataRequired()])
    price = StringField('Цена', validators=[DataRequired()])
    image = FileField('Изображение', validators=[FileRequired()])
    submit = SubmitField('Добавить объявление')


@app.route('/')
def index():
    listings = Listing.query.all()
    return render_template('index.html', listings=listings)


@app.route('/create', methods=['GET', 'POST'])
def create_listing():
    form = ListingForm()
    if form.validate_on_submit():
        image_file = form.image.data
        filename = secure_filename(image_file.filename)
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        image_file.save(image_path)

        new_listing = Listing(title=form.title.data,
                              description=form.description.data,
                              image_filename=filename,
                              formatted_time=current_datetime.strftime("%d.%m.%y %H.%M"),
                              price=form.price.data)
        db.session.add(new_listing)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('create_listing.html', form=form)


if __name__ == '__main__':
    #db.create_all()
    app.run(debug=True)
