# Salon Backend

A robust backend service for a Salon application, built with modern Python technologies.

## Tech Stack
- **Framework:** FastAPI
- **Database ORM:** SQLAlchemy
- **Database Driver:** psycopg2-binary
- **Data Validation:** Pydantic
- **Web Automation:** Selenium (WebDriver Manager)
- **Deployment:** Procfile included for PaaS (like Heroku)

## Getting Started

### Prerequisites
- Python 3.8+
- PostgreSQL (or your preferred relational database)

### Installation

1. **Clone the repository:**
   ```bash
   git clone <repository_url>
   cd salon-backend
   ```

2. **Set up a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Variables:**
   Create a `.env` file in the root directory and copy the contents from `.env.example`. Adjust the values according to your local setup.

5. **Run the Application:**
   ```bash
   # Make sure to update 'app.main:app' to your actual FastAPI entry point if it differs.
   uvicorn app.main:app --reload
   ```

## Project Structure
- `app/` - Core application logic and routes.
- `whatsapp_session/` - Contains local session data for WhatsApp automation (ignored in version control).
- `requirements.txt` - Python dependencies.
- `Procfile` - Configuration for deployment.
