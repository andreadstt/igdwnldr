# � Social Media Tools - Internal

A fast, lightweight collection of social media tools for content management. Built for internal use with focus on simplicity and performance.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-3.0+-green.svg)
![License](https://img.shields.io/badge/License-Personal%20Use-orange.svg)

## 🎯 Tools

### ✅ Instagram Reposter
- **Fast download** of posts, reels, and IGTV
- **Auto cover composition** - saved as separate `.cover` file (original preserved)
- **Repost caption** - Auto-generates `#Repost from @username` + original caption
- **Local storage** - Files saved directly to `~/Downloads/IG DOWNLOADS/`
- **CLI-like performance** - Optimized for speed

### 🔜 Coming Soon
- Twitter downloader
- Instagram Stories saver
- Thread archiver

## ✨ Key Features

- ⚡ **Super Fast**: CLI-level performance, minimal overhead
- 🎨 **Reposter-Focused**: Automatic caption generation for reposting
- 📁 **Local First**: Direct save to Downloads folder
- 🔄 **Non-Destructive**: Cover saved separately, originals preserved
- 🎛️ **Toggle Caption**: On/off switch for repost caption
- 🗂️ **Smart Organization**: Numbered files + caption.txt

## 📋 Requirements

- Python 3.8 or higher
- pip (Python package manager)

## 🚀 Quick Start

### 1. Installation

```bash
# Clone or download this repository
cd igdwnld

# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Run the Application

```bash
python run.py
```

Open `http://localhost:5000` in your browser.

## 📖 Usage

### Instagram Reposter

1. **Navigate** to Instagram Reposter from home
2. **Paste** Instagram post/reel URL
3. **Toggle** repost caption (on by default)
4. **Click Download** - super fast!
5. **Copy caption** and **Open folder** when complete

### Output Structure

```
~/Downloads/IG DOWNLOADS/20251214_123456_ABC123/
├── 01.jpg              # Original first image
├── 01.cover.jpg        # Composed cover with template
├── 02.jpg              # Second image (if carousel)
├── 03.mp4              # Video (if present)
└── caption.txt         # #Repost from @username + original caption

```bash
# Development mode
python run.py

# Or using Flask directly
export FLASK_APP=run.py
flask run
```

The application will start on `http://127.0.0.1:5000`

### 4. Open in Browser

Navigate to `http://localhost:5000` in your web browser.

## 📖 Usage

### Web Interface

1. **Enter URL or Username**
   - Paste Instagram post/reel URL: `https://instagram.com/p/ABC123/`
   - Or enter username: `@username`

2. **Click "Check"** to validate the input

3. **Click "Start Download"** to begin downloading

4. **Monitor Progress** with real-time updates

5. **Download or View** your files when complete

### CLI Mode (Original)

The original CLI tool is still available:
```bash
python main.py
```

## 📁 Project Structure

```
igdwnld/
├── app/
│   ├── __init__.py          # Flask app factory
│   ├── routes/
│   │   ├── main.py          # UI routes
│   │   └── api.py           # API endpoints
│   ├── services/
│   │   └── downloader.py    # Download logic
│   ├── templates/           # HTML templates
│   │   ├── base.html
│   │   ├── index.html
│   │   └── downloads.html
│   └── static/
│       ├── js/
│       │   └── app.js       # Frontend JavaScript
│       └── downloads/       # Downloaded files
├── config.py                # Configuration
├── run.py                   # Development server
├── wsgi.py                  # Production WSGI
├── requirements.txt         # Python dependencies
└── main.py                  # Original CLI tool
```

## 🛠️ Development

### Tech Stack

- **Backend**: Flask (Python)
- **Frontend**: HTML5, Tailwind CSS, Vanilla JavaScript
- **Instagram API**: Instaloader
- **Image Processing**: Pillow

### Running in Development

```bash
# Enable debug mode
export FLASK_ENV=development
export FLASK_DEBUG=1

python run.py
```

## 🚀 Production Deployment

### Using Gunicorn

```bash
pip install gunicorn

# Run with Gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 wsgi:app
```

### Using Docker (optional)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8000", "wsgi:app"]
```

### Deployment Options

- **DigitalOcean**: Droplet with Nginx + Gunicorn
- **Railway.app**: Easy deployment with free tier
- **Render.com**: One-click deployment
- **Heroku**: Platform as a Service

## ⚙️ Configuration

Edit `config.py` for customization:

```python
# Image composition settings
COVER_W = 849          # Cover width
COVER_H = 1061         # Cover height
POS_X = 109           # X position
POS_Y = 137           # Y position

# Template path
DEFAULT_TEMPLATE = "imgTemplate/your-template.png"
```

## 🔧 Troubleshooting

### Downloads folder not found
The app automatically creates `app/static/downloads/` folder. Ensure write permissions.

### Template not found
Place your template image in `imgTemplate/` folder and update `DEFAULT_TEMPLATE` in `config.py`.

### Login issues
For private posts, use the original CLI tool (`main.py`) which supports interactive login.

## ⚠️ Disclaimer

This tool is for **personal use only**. Please respect:
- Instagram's Terms of Service
- Copyright laws
- Content creators' rights
- Rate limits and fair use

**Do not use this tool to:**
- Download private content without permission
- Violate copyright or intellectual property rights
- Redistribute downloaded content
- Abuse Instagram's services

## 📝 License

For personal use only. Not for commercial distribution.

## 🤝 Contributing

This is a personal project. Feel free to fork and modify for your own use.

## 📞 Support

For issues or questions, check the original `main.py` implementation or Flask documentation.

## 🙏 Credits

- [Instaloader](https://instaloader.github.io/) - Instagram download library
- [Flask](https://flask.palletsprojects.com/) - Web framework
- [Tailwind CSS](https://tailwindcss.com/) - UI styling

---

Made with ❤️ using Flask
