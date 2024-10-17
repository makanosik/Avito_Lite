from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField
from wtforms.fields.choices import SelectField
from wtforms.fields.simple import PasswordField
from wtforms.validators import DataRequired
from flask_wtf.file import FileField
import os
from werkzeug.utils import secure_filename
from datetime import datetime
from flask_login import UserMixin, login_required, current_user, LoginManager, login_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer


app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/img/advertisements/'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///listings.db'
app.config['SECRET_KEY'] = '12345'
db = SQLAlchemy(app)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
login_manager = LoginManager()
login_manager.init_app(app)
app.config['MAIL_DEFAULT_SENDER'] = 'bigxxuser@gmail.com'
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'bigxxuser@gmail.com'
app.config['MAIL_PASSWORD'] = 'trgr xsbg koqo zbwl'
mail = Mail(app)


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    password_hash = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(50), nullable=False, default='user')
    listings = db.relationship('Listing', backref='author', lazy=True)
    email = db.Column(db.String(150), nullable=False, unique=True)
    phone = db.Column(db.String(20), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    confirmed = db.Column(db.Boolean, default=False)
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
    category = db.Column(db.String(100), nullable=False)


class ListingForm(FlaskForm):
    title = StringField('Название', validators=[DataRequired()])
    description = TextAreaField('Описание', validators=[DataRequired()])
    price = StringField('Цена', validators=[DataRequired()])
    image = FileField('Изображение')
    category = SelectField('Категория', choices=[
        ('Транспорт', 'Транспорт'),
        ('Недвижимость', 'Недвижимость'),
        ('Работа', 'Работа'),
        ('Услуги', 'Услуги'),
        ('Личные вещи', 'Личные вещи'),
        ('Для дома и дачи', 'Для дома и дачи'),
        ('Запчасти и аксессуары', 'Запчасти и аксессуары'),
        ('Электроника', 'Электроника'),
        ('Хобби и отдых', 'Хобби и отдых'),
        ('Животные', 'Животные'),
        ('Бизнес и оборудование', 'Бизнес и оборудование')
    ], validators=[DataRequired()])
    submit = SubmitField('Добавить объявление')


class RegistrationForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired()])
    email = StringField('E-mail', validators=[DataRequired()])
    phone = StringField('Телефон', validators=[DataRequired()])
    city = StringField('Город', validators=[DataRequired()])
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
    admin_user = User(username='admin', password_hash=hashed_password, email="drslik@yandex.ru", phone="7(777)777", city="Чусик", confirmed=True, role='admin')
    db.session.add(admin_user)
    db.session.commit()
    return "Администратор создан!"


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        username = form.username.data
        email = form.email.data
        phone = form.phone.data
        city = form.city.data
        password = form.password.data
        if User.query.filter_by(username=username).first() or User.query.filter_by(email=email).first():
            flash('Пользователь с таким именем или почтой уже существует!')
            return redirect(url_for('register'))
        hashed_password = generate_password_hash(password)
        new_user = User(username=username, email=email, phone=phone, city=city, password_hash=hashed_password,
                        confirmed=False, role='user')
        db.session.add(new_user)
        db.session.commit()
        send_confirmation_email(new_user.id)  # Отправка письма для подтверждения
        flash('Регистрация прошла успешно! Проверьте почту для подтверждения аккаунта.')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)


@app.route('/confirm/<token>')
def confirm_email(token):
    try:
        email = confirm_token(token)
    except:
        flash('Ссылка для подтверждения недействительна или истекла.')
        return redirect(url_for('index'))
    user = User.query.filter_by(email=email).first_or_404()
    if user.confirmed:
        flash('Аккаунт уже подтвержден. Пожалуйста, войдите.')
    else:
        user.confirmed = True
        db.session.commit()
        flash('Ваш email подтвержден!')
    return redirect(url_for('login'))


@app.route('/send_confirmation_email/<int:user_id>')
def send_confirmation_email(user_id):
    user = User.query.get_or_404(user_id)
    token = generate_confirmation_token(user.email)
    confirm_url = url_for('confirm_email', token=token, _external=True)
    html = render_template('email_confirmation.html', confirm_url=confirm_url)
    msg = Message(
        'Подтверждение регистрации',
        sender=app.config['MAIL_DEFAULT_SENDER'],  # Указываем отправителя
        recipients=[user.email],
        html=html
    )
    mail.send(msg)
    return "Письмо отправлено!"


def generate_confirmation_token(email):
    # Создаем объект URLSafeTimedSerializer с использованием секретного ключа приложения
    serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])

    # Генерируем токен, передавая в него email
    return serializer.dumps(email, salt='email-confirmation-salt')


def confirm_token(token, expiration=3600):
    # Создаем объект URLSafeTimedSerializer с использованием секретного ключа приложения
    serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])

    try:
        # Декодируем токен с указанием срока действия (в секундах)
        email = serializer.loads(token, salt='email-confirmation-salt', max_age=expiration)
    except:
        return False
    return email


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
            author=current_user,
            category = form.category.data
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
        category = form.category.data
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

        # Ищем пользователя в базе данных по имени
        user = User.query.filter_by(username=username).first()
        if user:
            # Проверяем подтверждён ли email
            if not user.confirmed:
                flash('Вам необходимо подтвердить email перед входом в систему.')
                return redirect(url_for('login'))

            # Проверяем правильность пароля
            if user.check_password(password):
                login_user(user)
                return redirect(url_for('index'))
            else:
                flash('Неправильное имя пользователя или пароль')
        else:
            flash('Пользователь не найден')
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True)