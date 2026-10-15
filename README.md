# HackHeist 2026

Official website for **HackHeist 2026**, organized by **GDG on Campus MIET**.

- **Live Site**: [https://hackheist-steel.vercel.app](https://hackheist-steel.vercel.app)
- **Registration**: [HackHeist 2026 Google Form](https://docs.google.com/forms/d/e/1FAIpQLSfVNx0ANEqMHLlsm-qei1T_ARVQa9C97G1bzYVMt-OGNvQSBg/viewform?usp=publish-edito)

---

## About The Event

HackHeist 2026 is a student-led hackathon and tech gathering focused on learning, building prototypes, and connecting students with developer communities and mentors.

### Highlights
- **Hackathon**: Team-based problem solving and prototyping
- **Workshops**: Practical, hands-on skill development sessions
- **Tech Sessions**: Tech talks and insights from industry developers
- **Networking**: Community networking with student developers and mentors

---

## Tech Stack

- **Backend**: Python 3, Flask
- **Frontend**: Semantic HTML5, Modern CSS3 (Variables, Flexbox, Grid), Vanilla JavaScript
- **Database**: SQLite3
- **Deployment**: Vercel Serverless (with Render support via Gunicorn)

---

## Project Structure

```text
hackheist/
├── api/
│   └── index.py            # Vercel serverless entrypoint
├── assets/                 # Brand assets and images
│   ├── gdg-logo.png
│   └── images/
├── templates/              # Jinja2 templates (Admin portal)
│   ├── admin_login.html
│   └── admin_dashboard.html
├── tests/                  # Automated test suite
│   └── test_app.py
├── app.py                  # Flask application & API routes
├── index.html              # Main event landing page
├── style.css               # Website styling & responsive design
├── script.js               # Frontend interactions & API bindings
├── vercel.json             # Vercel deployment configuration
├── render.yaml             # Render deployment configuration
└── requirements.txt        # Python dependencies
```

---

## Local Development

### Prerequisites
- Python 3.10+
- pip

### Setup

1. **Clone the repository**:
   ```sh
   git clone https://github.com/ayushraj10092002-dotcom/hackheist.git
   cd hackheist
   ```

2. **Create and activate a virtual environment**:
   ```sh
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies**:
   ```sh
   pip install -r requirements.txt
   ```

4. **Run the development server**:
   ```sh
   flask --app app run --debug
   ```

5. Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser.

---

## Testing

Run the automated test suite with:

```sh
python -m unittest discover -s tests -v
```

---

## Admin Portal

- **URL**: `/admin/login`
- Requires `ADMIN_PASSWORD_HASH` configured in environment variables.
- View participant and team records in the dashboard.

---

## License & Credits

Organized by **GDG on Campus MIET**. All rights reserved.
