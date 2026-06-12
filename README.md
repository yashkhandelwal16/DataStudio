# 📊 Data Studio 

Data Studio is a high-performance web application designed for immersive data exploration. It allows users to upload complex datasets (CSV, Excel, JSON) and automatically transforms them into interactive 3D statistical models, providing AI-driven narrative insights through a premium Neo-Brutalist design system.

---

## 🚀 Key Features

*   **Pro Authentication System**: Secure Email/Password login, OTP verification for registration, and robust password recovery powered by Supabase.
*   **Immersive 3D Visualization**: Renders 3D Distribution, Trend, and Volumetric charts using a high-performance WebGL engine (Plotly).
*   **AI-Driven Insights**: Automated narrative generation that tells the "story" behind your data.
*   **Neo-Brutalist UI/UX**: High-contrast design featuring glassmorphism, smooth animations, and full dark mode support.
*   **Multi-Format Data Engine**: Native support for `.csv`, `.xlsx`, `.xls`, and `.json` with ultra-fast C-based parsing.
*   **Cloud Dataset Archival**: Non-blocking background synchronization with Supabase Storage for secure data persistence.

---

## 🛠️ Technology Stack

| Layer | Technology |
| :--- | :--- |
| **Backend** | Flask (Python 3.12+), Flask-Compress, Gunicorn |
| **Frontend** | Vite 7.3, Node.js, Jinja2, Bootstrap 5.3 |
| **Data Processing** | Pandas, NumPy |
| **Visualization** | Plotly (WebGL Engine) |
| **Database & Auth** | Supabase (PostgreSQL & Auth) |
| **Cloud Storage** | Supabase Storage API |
| **Design System** | Custom Neo-Brutalist Tokens, CSS3 |

---

## 📂 Project Structure

```text
/
├── app.py              # Main Flask server (Routing & logic)
├── utils/              # Calculation, Insights, and Viz engines
├── static/             # CSS design tokens, Theme JS, and assets
├── templates/          # Jinja2 HTML templates (Auth, Dashboard, Settings)
├── src/                # Vite source assets and JS modules
├── supabase_setup.sql  # SQL schema for database configuration
├── storage_setup.sql   # SQL for Supabase storage bucket policies
├── requirements.txt    # Python backend dependencies
└── package.json        # Frontend tooling dependencies
```

---

## ⚙️ Local Setup Instructions

Follow these steps to get the project running on your local machine:

### 1. Prerequisites
- **Python 3.12+** installed.
- **Node.js** (Latest LTS) installed.
- A **Supabase** account and project created.

### 2. Clone the Repository
```bash
git clone <your-repository-url>
cd DataStudio
```

### 3. Backend Setup
Create a virtual environment and install the required Python packages:
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 4. Frontend Setup
Install Node dependencies for Vite tooling:
```bash
npm install
```

### 5. Environment Configuration
Create a `.env` file in the root directory and populate it with your credentials:
```env
SUPABASE_URL="your_supabase_project_url"
SUPABASE_KEY="your_supabase_anon_key"
SUPABASE_SECRET_KEY="your_supabase_service_role_key"
SUPABASE_BUCKET="your_storage_bucket_name"
FLASK_SECRET_KEY="your_random_secret_key"
```

### 6. Database & Storage Setup
- Run the queries in `supabase_setup.sql` in your Supabase SQL Editor to set up the necessary tables and triggers.
- Run the queries in `storage_setup.sql` to configure the storage bucket policies for file uploads.

---

## 🏃 Running the Application

1.  **Start the Backend**:
    ```bash
    python app.py
    ```
    The application will typically be available at `http://127.0.0.1:5000`.

2.  **Start Vite (Development)**:
    If you are modifying frontend assets in `src/`:
    ```bash
    npm run dev
    ```

---

## 🎨 Design Philosophy
Data Studio utilizes a **Neo-Brutalist** aesthetic characterized by:
- **High Contrast**: Yellow and Black primary palette.
- **Sharp Geometry**: Bold borders and distinct shadows.
- **Dynamic Feedback**: Scale-up hover effects and heartbeat animations.
- **Glassmorphism**: Subtle translucency on cards and navigation elements.

---

## 🤝 Contributing
Contributions are welcome! Please feel free to submit a Pull Request or open an issue for any bugs or feature requests.

## 📄 License
© 2025–2026 Yash Khandelwal. All Rights Reserved.
Made with ❤️ by [Yash Khandelwal](https://github.com/yashkhandelwal16)
