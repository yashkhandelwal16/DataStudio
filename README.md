# 📊 Data Studio

**A Next-Generation Immersive Data Exploration Web Application**

## 🚀 Project Overview
Data Studio is designed for immersive data exploration. It allows users to upload datasets (CSV, Excel, JSON) and automatically generates summary statistics and interactive 3D statistical models. The project features a premium **Neo-Brutalist** design system with a high-performance WebGL rendering engine.

---

## 🛠️ Technology Stack (The Engine)

### Backend & Core
- **Flask (Python)**: Handles routing, session management, and Gzip-compressed data transfer.
- **Pandas & NumPy**: C-Parsing Engine for ultra-fast data ingestion and multi-dimensional calculations.
- **Supabase**: Secure authentication and cloud storage.

### Visualization & Frontend
- **Plotly (3D WebGL Engine)**: Renders 3D Distribution, Trend, Categorical, and Volumetric charts.
- **Frontend**: HTML5, CSS3, JavaScript (Vanilla) + Bootstrap 5.
- **Design System**: Custom "Modern Neo-Brutalist" aesthetic with high-contrast palette and micro-interaction animations.

---

## ✨ Key Features

- **🔐 Secure Authentication**: Email/Password login with Supabase.
- **📂 Multi-Format Support**: Processes `.csv`, `.xlsx`, `.xls`, and `.json` files.
- **📤 Advanced Upload UI**: Drag & Drop interface with visual feedback.
- **📊 3D Visualization**: 360° interactive charts with zoom, pan, and hover tooltips.
- **🤖 AI Insights**: Automated storytelling and trend detection using statistical analysis.
- **⚡ Performance**: Gzip compression and C-Engine parsing for speed.

---

## ⚙️ Installation & Setup

1.  **Prerequisites**: Ensure Python 3.10+ is installed.

2.  **Clone the Repository**
    ```bash
    git clone <repository-url>
    cd Data-Studio
    ```

3.  **Set Up Virtual Environment**
    ```bash
    python -m venv venv
    .\venv\Scripts\activate  # Windows
    # source venv/bin/activate  # Mac/Linux
    ```

4.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

5.  **Environment Variables**
    Create a `.env` file in the root directory and add your Supabase credentials:
    ```env
    SUPABASE_URL=your_supabase_url
    SUPABASE_KEY=your_supabase_anon_key
    SECRET_KEY=your_flask_secret_key
    ```

6.  **Run the Application**
    ```bash
    python app.py
    # Or for production:
    # gunicorn app:app
    ```
    Open your browser and navigate to: `http://127.0.0.1:5000`

---

## 📂 Directory Structure

```text
/
├── app.py              # Main Flask application logic
├── Procfile            # Deployment instructions
├── runtime.txt         # Python version spec
├── .env                # Secret keys and credentials
├── requirements.txt    # Python dependencies
├── supabase_setup.sql  # Database configuration
├── static/
│   ├── css/style.css   # Neo-Brutalist design system
│   ├── js/theme.js     # Interaction engine
│   └── charts/         # Analysis assets
└── templates/          # HTML pages (Index, Dashboard, Login, Signup)
```

---

## 📝 Workflow

1.  **User Registration/Login**: Secure auth via Supabase.
2.  **Data Upload**: Drag & drop datasets (processed in-memory).
3.  **Analysis**: Backend processes data using Pandas.
4.  **Visualization**: Plotly generates 3D models.
5.  **Dashboard**: View interactive charts and AI-generated insights.

---

Made with ❤️ by Yash Khandelwal | © 2024–2026
