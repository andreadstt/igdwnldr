# Project Structure Documentation

```
igdwnld/
├── app/
│   ├── __init__.py                 # Flask app factory
│   ├── routes/                     # Route handlers
│   │   ├── __init__.py
│   │   ├── main.py                 # Main UI routes (home, downloads)
│   │   ├── api.py                  # Instagram API endpoints
│   │   └── twitter.py              # Twitter routes
│   │
│   ├── services/                   # Business logic (organized by platform)
│   │   ├── __init__.py
│   │   ├── instagram/              # Instagram services
│   │   │   ├── __init__.py
│   │   │   ├── downloader.py       # Instagram downloader service
│   │   │   └── README.md
│   │   └── twitter/                # Twitter services
│   │       ├── __init__.py
│   │       ├── thread_adjuster.py  # Thread splitter (rule-based)
│   │       └── README.md
│   │
│   ├── templates/                  # HTML templates (organized by platform)
│   │   ├── base.html
│   │   ├── home.html               # Tools directory
│   │   ├── downloads.html          # Downloaded items list
│   │   ├── instagram/              # Instagram templates
│   │   │   ├── ig_reposter.html
│   │   │   └── README.md
│   │   └── twitter/                # Twitter templates
│   │       ├── twitter_thread.html
│   │       └── README.md
│   │
│   ├── static/                     # Static assets
│   │   ├── css/
│   │   ├── js/
│   │   │   └── app.js
│   │   ├── images/
│   │   │   ├── logo.png
│   │   │   ├── miniLogo.png
│   │   │   └── coverTemplate.png
│   │   └── uploads/
│   │
│   └── images/                     # Source images (backup)
│       ├── miniLogo.png
│       └── coverTemplate.png
│
├── config.py                       # Flask & app configuration
├── run.py                          # Development server
├── wsgi.py                         # Production WSGI entry
├── requirements.txt                # Python dependencies
├── README.md                       # Main documentation
└── STRUCTURE.md                    # This file

## Import Paths

### Services
```python
# Instagram
from app.services.instagram import IGDownloader

# Twitter
from app.services.twitter import ThreadAdjuster
```

### Templates
```python
# Instagram
render_template('instagram/ig_reposter.html')

# Twitter
render_template('twitter/twitter_thread.html')
```

## Organization Benefits

1. **Modularity**: Each platform isolated in its own folder
2. **Scalability**: Easy to add new platforms (TikTok, Facebook, etc)
3. **Maintainability**: Clear separation of concerns
4. **Team Collaboration**: Multiple devs can work on different platforms
5. **Testing**: Easier to write platform-specific tests

## Adding New Platform

1. Create folders:
   - `app/services/{platform}/`
   - `app/templates/{platform}/`

2. Create service:
   - `app/services/{platform}/__init__.py`
   - `app/services/{platform}/service_name.py`

3. Create route:
   - `app/routes/{platform}.py`

4. Register blueprint in `app/__init__.py`:
   ```python
   from app.routes import platform
   app.register_blueprint(platform.bp)
   ```

5. Add tool card to `home.html`
