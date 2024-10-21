
def send_confirmation_email(user_id):
    user = User.query.get_or_404(user_id)
    token = generate_confirmation_token(user.email)
    confirm_url = url_for('confirm_email', token=token, _external=True)
    html = render_template('email_confirmation.html', confirm_url=confirm_url)
    msg = Message('Подтверждение регистрации', recipients=[user.email], html=html)
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