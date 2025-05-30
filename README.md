# Gliding Club Student Management System

A comprehensive web-based management system for gliding clubs to track student training records, ground briefings, and licensing information. Built with Django and designed to support both English and Hebrew languages with full RTL support.

This project was mostly "vibe-coded" with the majority of code (all HTML code) generate by Claude Sonnet 3.7 

## 🛩️ Features

### Core Functionality
- **Student Training Records Management** - Track flight sessions, exercises, and progress
- **Ground Briefing System** - Manage theoretical training sessions records 
- **Exercise Performance Tracking** - Detailed tracking of pre-solo and post-solo exercises as required by local regulation
- **Digital Sign-off Process** - Instructors can sign off student flights

### Reports & Exports
- **PDF Export** - Full training reports with Hebrew/English support
- **CSV Export** - Data export for external analysis
- **Exercise Matrix** - Visual progress tracking grid for submission to local CAA

### Internationalization
- **Bilingual Support** - Full English and Hebrew language support
- **RTL Layout** - Proper right-to-left text direction for Hebrew
- **Localization** - Date formats and UI elements adapted for both languages

## 🚀 Technology Stack

- **Backend**: Django 4.2+ with Python 3.11+
- **Database**: PostgreSQL 17+
- **Frontend**: Bootstrap 5 with RTL support
- **PDF Generation**: WeasyPrint with Hebrew font support
- **Authentication**: Django's built-in auth with django-axes for security

## 📋 Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development)
- PostgreSQL 17 (if running locally)

## 🔧 Quick Start with Docker

1. **Clone the repository**
   ```bash
   git clone https://github.com/pelegw/studentlog.git
   cd studentlog
   ```

2. **Create environment file**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start the application**
   ```bash
   docker-compose up -d
   ```

4. **Initialize the database**
   ```bash
   docker-compose exec web python manage.py migrate
   docker-compose exec web python manage.py createsuperuser
   docker-compose exec web python manage.py import_initial_data
   ```

5. **Access the application**
   - Main application: http://localhost:80
   - Admin interface: http://localhost:80/admin

## 🛠️ Development Setup

1. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**
   ```bash
   cd gliding_club
   pip install -r requirements.txt
   ```

3. **Configure database**
   ```bash
   # Update settings.py for local development
   python manage.py migrate
   python manage.py createsuperuser
   ```

4. **Load initial data**
   ```bash
   python manage.py import_initial_data
   python manage.py import_ground_briefings data/ground_briefings.xlsx
   ```

5. **Run development server**
   ```bash
   python manage.py runserver
   ```

## 📊 Data Management

### Import Initial Data
The system includes Excel files with training topics, exercises, and ground briefing topics:

```bash
# Import all initial data
python manage.py import_initial_data

# Import ground briefing data
python manage.py import_ground_briefings data/ground_briefings.xlsx
```

### Backup and Restore
```bash
# Create backup
docker-compose exec backup pg_dump -h db -U postgres gliding_club > backup.sql

# Restore backup
docker-compose exec db psql -U postgres -d gliding_club < backup.sql
```

## 🎨 Customization

### Club Branding
Update the club name and branding in `settings.py`:
```python
CLUB_NAME = "Your Gliding Club Name"
```

### Language Support
The system supports both English and Hebrew. Users can switch languages using the dropdown in the navigation bar.

### Adding New Exercises
1. Use the Django admin interface
2. Import from Excel files using the management command
3. Add programmatically through the Exercise model

## 🔒 Security Features

- **Content Security Policy (CSP)** - Prevents XSS attacks
- **Django Axes** - Brute force protection
- **Secure Headers** - HSTS, X-Frame-Options, etc.
- **Digital Signatures** - Tamper-proof record sign-offs
- **Audit Logging** - Complete activity tracking
- **File Upload Security** - Validation and sanitization

## 🌐 Production Deployment

### Environment Variables
Key environment variables for production:

```bash
SECRET_KEY=your-secret-key
DEBUG=False
ALLOWED_HOSTS=your-domain.com
POSTGRES_DB=gliding_club
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your-password
CSRF_TRUSTED_ORIGINS=https://your-domain.com
```

### SSL Configuration
The system is designed to work with SSL/HTTPS. Update your nginx configuration and set:
```python
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
```

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🏆 Acknowledgments

- Built for our gliding club community with compliance to local requirements in mind
- Hebrew localization and RTL support for Israeli users as our club is in Israel
- The app did not go through extensive penetration testing, use at your own risk
- Special thanks to the Django and Bootstrap communities

---

**Note**: This system is designed for internal training record management and should be used in conjunction with official certification processes as required by your local aviation authority.
