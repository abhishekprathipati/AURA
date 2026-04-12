from app import app

with app.app_context():
    print("Flask-Mail Configuration:")
    print(f"MAIL_SERVER: {app.config.get('MAIL_SERVER')}")
    print(f"MAIL_PORT: {app.config.get('MAIL_PORT')}")
    print(f"MAIL_USE_TLS: {app.config.get('MAIL_USE_TLS')}")
    print(f"MAIL_USERNAME: {app.config.get('MAIL_USERNAME')}")
    print(f"MAIL_DEFAULT_SENDER: {app.config.get('MAIL_DEFAULT_SENDER')}")
    print()

    print("Flask extensions available:")
    print(f"Extensions dict: {list(app.extensions.keys())}")
    print(f"'mail' in extensions: {'mail' in app.extensions}")
    print()

    if 'mail' in app.extensions:
        mail_ext = app.extensions['mail']
        print(f"Mail extension: {mail_ext}")
        print(f"Mail object type: {type(mail_ext)}")
    else:
        print("[ERROR] 'mail' NOT found in extensions!")
