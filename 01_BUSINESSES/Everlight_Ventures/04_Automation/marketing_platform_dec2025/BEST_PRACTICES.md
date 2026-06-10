== BEST PRACTICES (Perplexity) ==
## Recommended Project Structure
```
project/
├── app/
│   ├── __init__.py      # create_app() factory
│   ├── config.py        # Config classes (DevConfig, TestConfig, ProdConfig)
│   ├── extensions.py    # db = SQLAlchemy() etc.
│   ├── main/            # Blueprint: core routes
│   │   ├── __init__.py
│   │   └── routes.py
│   ├── auth/            # Blueprint: auth routes (feature-based)
│   │   ├── __init__.py
│   │   └── routes.py
│   └── templates/       # Jinja2 templates (base.html + feature-specific)
├── tests/               # pytest files
│   ├── conftest.py      # test app factory
│   └── test_main.py
├── instance/
│   └── config.py        # Prod secrets (gitignored)
├── .env                 # Dev secrets (SECRET_KEY, DATABASE_URL)
├── requirements.txt
├── pytest.ini
└── run.py               # if __name__ == '__main__': app = create_app()
```
Organize blueprints by **features** (auth, main, admin), not HTTP methods.[1][2][4]

## Core Code Patterns

### 1. Application Factory (`app/__init__.py`)
```python
from flask import Flask
from .extensions import db
from .main import bp as main_bp
from .auth import bp as auth_bp  # Add more blueprints

def create_app(config_class='config.DevConfig'):
    app = Flask(__name__)
    app.config.from_object(config_class)
    app.config.from_pyfile('instance/config.py', silent=True)  # Prod secrets
    
    # Init extensions AFTER config
    db.init_app(app)
    
    # Register blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    return app
```
Enables isolated test instances, env-specific configs, no circular imports.[1][2][3][4]

### 2. SQLite + SQLAlchemy (`app/extensions.py`)
```python
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# In models.py (e.g., app/models.py)
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True)
```
Use `SQLALCHEMY_DATABASE_URI = 'sqlite:///app.db'` in configs. Init db via CLI or factory.[1][4]

### 3. Blueprint Example (`app/main/__init__.py` + `routes.py`)
```python
# app/main/__init__.py
from flask import Blueprint
bp = Blueprint('main', __name__, template_folder='templates')

# app/main/routes.py
from . import bp
from flask import render_template

@bp.route('/')
def index():
    return render_template('index.html')
```
Register in factory. Templates inherit from `base.html` in `app/templates/`.[1][4]

### 4. Config Classes (`app/config.py`)
```python
import os
from dotenv import load_dotenv
load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///app.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

class DevConfig(Config): pass
class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
class ProdConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
```
Pass to `create_app('config.TestConfig')` for tests.[1][3]

### 5. Templates (`app/templates/base.html`)
```html
<!DOCTYPE html>
<html>
<head><title>{% block title %}App{% endblock %}</title></head>
<body>{% block content %}{% endblock %}</body>
</html>
```
Extend in feature templates: `{% extends "base.html" %}`.[4]

## Testing with Pytest (`tests/conftest.py`)
```python
import pytest
from app import create_app
from app.extensions import db

@pytest.fixture(scope='function')
def app():
    app = create_app('config.TestConfig')
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()
```
Run: `pytest -v`. Use in-memory SQLite for isolation.[1][2][3]

## Best Practices Summary
- **Configs**: Classes + `.env` (dev), `instance/config.py` (prod, gitignore).[1]
- **Extensions**: Define in `extensions.py`, init with `init_app(app)`.[1][4]
- **CLI**: Add `flask --app run.py` support in `run.py`.[3]
- **Tools**: `pytest`, `black`, `flake8`; document in `README.md`.[1]
- **SQLite**: Fine for small apps; use `:memory:` for tests.[2]

This scales from small to large apps while staying testable.[1][2][3][4][5]
