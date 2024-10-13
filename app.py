from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField
from wtforms.fields.simple import PasswordField
from wtforms.validators import DataRequired
from flask_wtf.file import FileField, FileRequired
import os
from werkzeug.utils import secure_filename
from datetime import datetime
from flask_login import UserMixin, login_required, current_user, LoginManager, login_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/img/advertisements/'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///listings.db'
app.config['SECRET_KEY'] = 'your_secret_key'
db = SQLAlchemy(app)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
login_manager = LoginManager()
login_manager.init_app(app)


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    password_hash = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(50), nullable=False, default='user')
    listings = db.relationship('Listing', backref='author', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Listing(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.String(100), nullable=False)
    image_filename = db.Column(db.String(150), nullable=True)
    formatted_time = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


class ListingForm(FlaskForm):
    title = StringField('Название', validators=[DataRequired()])
    description = TextAreaField('Описание', validators=[DataRequired()])
    price = StringField('Цена', validators=[DataRequired()])
    image = FileField('Изображение')
    submit = SubmitField('Добавить объявление')


class RegistrationForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    submit = SubmitField('Зарегистрироваться')


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    listings = Listing.query.order_by(Listing.id.desc()).all()  # Покажем объявления всем
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            # Логика для админа
            pass
    return render_template('index.html', listings=listings)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/profile')
@login_required
def profile():
    user = current_user
    # Проверяем, является ли пользователь администратором
    if user.role == 'admin':
        # Если администратор, выбираем все объявления
        listings = Listing.query.order_by(Listing.id.desc()).all()
    else:
        # Если обычный пользователь, выбираем только его объявления
        listings = Listing.query.filter_by(author=user).order_by(Listing.id.desc()).all()
    return render_template('profile.html', listings=listings)


@app.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete_listing(id):
    listing = Listing.query.get_or_404(id)
    if current_user.role != 'admin' and listing.author != current_user:
        return "Доступ запрещён", 403
    if listing.image_filename:
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], listing.image_filename)
        if os.path.exists(image_path):
            os.remove(image_path)
    db.session.delete(listing)
    db.session.commit()
    return redirect(url_for('profile'))


@app.route('/create_admin')
def create_admin():
    if User.query.filter_by(username='admin').first():
        return "Администратор уже существует."
    hashed_password = generate_password_hash('12345')
    admin_user = User(username='admin', password_hash=hashed_password, role='admin')
    db.session.add(admin_user)
    db.session.commit()
    return "Администратор создан!"


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()  # Используйте форму для регистрации, а не ListingForm
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        if User.query.filter_by(username=username).first():
            flash('Пользователь с таким именем уже существует!')
            return redirect(url_for('register'))
        hashed_password = generate_password_hash(password)
        new_user = User(username=username, password_hash=hashed_password, role='user')
        db.session.add(new_user)
        db.session.commit()
        flash('Регистрация прошла успешно! Войдите в систему.')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)


@app.route('/create', methods=['GET', 'POST'])
@login_required
def create_listing():
    form = ListingForm()
    if form.validate_on_submit():
        image_file = form.image.data
        if image_file and allowed_file(image_file.filename):
            filename = secure_filename(image_file.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image_file.save(image_path)
        else:
            flash("Неверный формат файла. Пожалуйста, загрузите изображение.")
            return render_template('create_listing.html', form=form)
        # Создаем новое объявление
        new_listing = Listing(
            title=form.title.data,
            description=form.description.data,
            price=form.price.data,
            image_filename=filename if image_file else None,
            formatted_time=datetime.now().strftime("%d.%m.%y %H:%M"),
            author=current_user
        )
        db.session.add(new_listing)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('create_listing.html', form=form)


@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_listing(id):
    listing = Listing.query.get_or_404(id)
    # Проверяем, что пользователь имеет права для редактирования
    if current_user.role != 'admin' and listing.author != current_user:
        return "Доступ запрещён", 403
    form = ListingForm()
    if form.validate_on_submit():
        # Обновляем данные объявления
        listing.title = form.title.data
        listing.description = form.description.data
        listing.price = form.price.data
        # Обрабатываем изображение
        image_file = form.image.data
        if image_file and allowed_file(image_file.filename):
            # Удаляем старое изображение, если оно было загружено ранее
            if listing.image_filename:
                old_image_path = os.path.join(app.config['UPLOAD_FOLDER'], listing.image_filename)
                if os.path.exists(old_image_path):
                    os.remove(old_image_path)
            # Сохраняем новое изображение
            filename = secure_filename(image_file.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image_file.save(image_path)
            listing.image_filename = filename
        elif image_file:  # Если файл есть, но недопустимый формат
            flash("Неверный формат файла. Пожалуйста, загрузите изображение.")
            return redirect(url_for('edit_listing', id=listing.id))
        # Обновляем время изменения
        listing.formatted_time = datetime.now().strftime("%d.%m.%y %H.%M")
        # Сохраняем изменения в базе данных
        db.session.commit()
        return redirect(url_for('profile'))
    # Заполняем форму текущими данными, если это GET-запрос
    elif request.method == 'GET':
        form.title.data = listing.title
        form.description.data = listing.description
        form.price.data = listing.price
    return render_template('edit_listing.html', form=form, listing=listing)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Неправильное имя пользователя или пароль')
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True)