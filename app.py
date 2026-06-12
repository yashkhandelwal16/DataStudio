import os
from functools import wraps
from pathlib import Path

# pyrefly: ignore [missing-import]
from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
# pyrefly: ignore [missing-import]
from flask_compress import Compress
# pyrefly: ignore [missing-import]
from werkzeug.utils import secure_filename
# pyrefly: ignore [missing-import]
from supabase import create_client, Client
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv

from utils.data_loader import load_dataset
from utils.analysis import basic_statistics, column_overview, generate_text_insights
from utils.visualization import create_charts

# Load environment variables
load_dotenv(override=True)

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_FOLDER = BASE_DIR / "uploads"
CHART_FOLDER = BASE_DIR / "static" / "charts"

# Ensure directories exist and are clean
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CHART_FOLDER, exist_ok=True)

# Clear local uploads folder on server start to keep deployment storage clean
if UPLOAD_FOLDER.exists():
    for f in os.listdir(UPLOAD_FOLDER):
        file_p = UPLOAD_FOLDER / f
        if file_p.is_file():
            try:
                os.remove(file_p)
            except:
                pass

ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls", ".json"}

# Supabase Setup
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY") # service_role key

if SUPABASE_KEY:
    masked_key = SUPABASE_KEY[:10] + "..." if len(SUPABASE_KEY) > 10 else "SHORT_KEY"
    print(f"DEBUG: Supabase Key loaded. Starts with: {masked_key}")

if SUPABASE_SECRET_KEY:
    masked_secret = SUPABASE_SECRET_KEY[:10] + "..." if len(SUPABASE_SECRET_KEY) > 10 else "SHORT_KEY"
    print(f"DEBUG: Supabase Secret Key loaded. Starts with: {masked_secret}")

# --- Supabase Client with Auto-Reconnect ---
# We keep a cached client but recreate it transparently if the project was
# paused (free-tier) and the connection has gone stale.
_supabase_client: Client = None
_supabase_admin_client: Client = None

def _make_client(key: str) -> Client | None:
    """Create a fresh Supabase client, or return None if not configured."""
    if SUPABASE_URL and key and "YOUR_SUPABASE" not in SUPABASE_URL:
        return create_client(SUPABASE_URL, key)
    return None

def get_supabase(force_new: bool = False) -> Client | None:
    """Return the cached Supabase client, creating it if needed."""
    global _supabase_client
    if force_new or _supabase_client is None:
        _supabase_client = _make_client(SUPABASE_KEY)
        if force_new:
            print("DEBUG: Supabase client recreated (reconnect).")
    return _supabase_client

def get_supabase_admin(force_new: bool = False) -> Client | None:
    """Return the cached Supabase admin client, creating it if needed."""
    global _supabase_admin_client
    if force_new or _supabase_admin_client is None:
        _supabase_admin_client = _make_client(SUPABASE_SECRET_KEY)
        if force_new:
            print("DEBUG: Supabase admin client recreated (reconnect).")
    return _supabase_admin_client

# Initialise on startup (kept for backward-compat with non-auth routes)
supabase: Client = get_supabase()
supabase_admin: Client = get_supabase_admin()

from datetime import timedelta

app = Flask(__name__)
Compress(app) # Enable Gzip compression
app.config["UPLOAD_FOLDER"] = str(UPLOAD_FOLDER)
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "change-this-secret-key")
# Make session last for a long time (1 year)
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=365)

# --- AUTH UTILITIES ---
def refresh_supabase_session():
    """Attempts to refresh the Supabase session if tokens are present."""
    access_token = session.get("access_token")
    refresh_token = session.get("refresh_token")
    
    if not access_token or not refresh_token or not supabase:
        return False

    try:
        # Check if current session is valid by trying to get user
        supabase.auth.set_session(access_token, refresh_token)
        supabase.auth.get_user(access_token)
        return True
    except:
        # Token likely expired, try refreshing
        try:
            res = supabase.auth.refresh_session(refresh_token)
            session["access_token"] = res.session.access_token
            session["refresh_token"] = res.session.refresh_token
            session["user"] = res.user.id
            session.permanent = True # Ensure cookie respects lifetime
            return True
        except Exception as e:
            print(f"DEBUG: Session refresh failed: {e}")
            return False

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("login"))
            
        # Try to refresh/verify session
        if not refresh_supabase_session():
            session.clear()
            flash("Session expired. Please log in again.", "warning")
            return redirect(url_for("login"))
            
        return f(*args, **kwargs)
    return decorated_function

def allowed_file(filename: str) -> bool:
    _, ext = os.path.splitext(filename)
    return ext.lower() in ALLOWED_EXTENSIONS

# --- ROUTES ---

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        
        client = get_supabase()
        if not client:
            flash("Supabase is not configured. Please check your .env file.", "danger")
            return redirect(url_for("login"))
            
        # Try once; if it looks like a connection/stale-client error, recreate
        # the client and retry once (handles Supabase free-tier wake-up).
        for attempt in range(2):
            try:
                response = client.auth.sign_in_with_password({"email": email, "password": password})
                session["user"] = response.user.id
                session["email"] = email
                session["access_token"] = response.session.access_token
                session["refresh_token"] = response.session.refresh_token
                session.permanent = True
                flash("Successfully logged in!", "success")
                return redirect(url_for("index"))
            except Exception as e:
                err = str(e).lower()
                is_conn_err = any(k in err for k in (
                    "connect", "network", "timeout", "connection",
                    "unreachable", "refused", "reset", "eof"
                ))
                if is_conn_err and attempt == 0:
                    print(f"DEBUG: Auth connection error on attempt 1, reconnecting... ({e})")
                    client = get_supabase(force_new=True)
                    continue  # retry with fresh client
                # Genuine auth failure or second attempt failed
                flash(f"Login failed: {str(e)}", "danger")
                break
            
    return render_template("login.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        full_name = request.form.get("full_name")
        
        client = get_supabase()
        if not client:
            flash("Supabase is not configured. Please check your .env file.", "danger")
            return redirect(url_for("signup"))
            
        for attempt in range(2):
            try:
                response = client.auth.sign_up({
                    "email": email,
                    "password": password,
                    "options": {
                        "data": {"full_name": full_name}
                    }
                })
                session["signup_email"] = email
                return render_template("verify_otp.html", signup_email=email)
            except Exception as e:
                err = str(e).lower()
                is_conn_err = any(k in err for k in (
                    "connect", "network", "timeout", "connection",
                    "unreachable", "refused", "reset", "eof"
                ))
                if is_conn_err and attempt == 0:
                    print(f"DEBUG: Auth connection error on attempt 1, reconnecting... ({e})")
                    client = get_supabase(force_new=True)
                    continue
                flash(f"Signup failed: {str(e)}", "danger")
                break
            
    return render_template("signup.html")

@app.route("/verify-otp", methods=["GET", "POST"])
def verify_otp():
    if request.method == "POST":
        otp = request.form.get("otp")
        # Get email from session since it's not in the OTP form
        email = session.get("signup_email")
        
        if not email:
            flash("Session expired or invalid email. Please start over.", "danger")
            return redirect(url_for("signup"))
            
        if not otp:
            flash("Please enter the verification code.", "danger")
            return render_template("verify_otp.html", signup_email=email)
        
        try:
            # Verify the OTP
            res = supabase.auth.verify_otp({
                "email": email,
                "token": otp,
                "type": "signup"
            })
            
            flash("Identity verified! You can now log in.", "success")
            return redirect(url_for("login"))
        except Exception as e:
            err_msg = str(e)
            print(f"DEBUG: Verification error: {err_msg}")
            if "expired" in err_msg.lower():
                flash("The code has expired. Please try signing up again.", "warning")
            elif "invalid" in err_msg.lower():
                flash("Invalid code. Please check your email carefully.", "danger")
            else:
                flash(f"Verification failed: {err_msg}", "danger")
            return render_template("verify_otp.html", signup_email=email)
            
    # For GET request
    if "signup_email" not in session:
        return redirect(url_for("signup"))
    return render_template("verify_otp.html", signup_email=session["signup_email"])

@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email")
        
        if not supabase:
            flash("Supabase is not configured. Please check your .env file.", "danger")
            return redirect(url_for("forgot_password"))
            
        try:
            # Send reset email
            # We'll use the current host but redirecting to /reset-password
            redirect_url = url_for('reset_password', _external=True)
            supabase.auth.reset_password_for_email(email, {"redirect_to": redirect_url})
            flash("If an account exists, a reset link has been sent to your email.", "success")
            return redirect(url_for("login"))
        except Exception as e:
            flash(f"Error: {str(e)}", "danger")
            
    return render_template("forgot_password.html")

@app.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    # Note: On GET, the user arrives here with the token in the URL fragment from email
    # Flask cannot read the fragment, but if they submit the form, we want them to be authenticated.
    if request.method == "POST":
        new_password = request.form.get("password")
        
        # We need an active session to update user information.
        # In this simplistic Flask approach, we expect the user to have been automatically 
        # authenticated via the link (if handled by JS) OR we'd need some magic.
        # However, for a standard Supabase-Flask setup, we can try to update even without 
        # a local Flask session if they just arrived with a token (token handling needs JS).
        # Let's try the simple update_user if access_token is in session.
        
        if "access_token" not in session:
           flash("Session expired or invalid link. Please request a new reset link.", "danger")
           return redirect(url_for("forgot_password"))

        try:
            # Set the current session in the client if we have the tokens
            supabase.auth.set_session(session["access_token"], session.get("refresh_token"))
            supabase.auth.update_user({"password": new_password})
            flash("Password updated successfully! You can now log in.", "success")
            return redirect(url_for("login"))
        except Exception as e:
            flash(f"Failed to update password: {str(e)}", "danger")
            
    return render_template("reset_password.html")

@app.route("/set-session", methods=["POST"])
def set_session():
    data = request.json
    if "access_token" in data:
        session["access_token"] = data["access_token"]
        session["refresh_token"] = data.get("refresh_token")
        # Optional: decode token to get user id
        # session["user"] = ... 
        return {"status": "ok"}
    return {"status": "error"}, 400

@app.route("/logout")
def logout():
    # Cleanup local file before logging out
    filename = session.get("last_filename")
    if filename:
        local_path = UPLOAD_FOLDER / filename
        if local_path.exists():
            try:
                os.remove(local_path)
            except:
                pass
    
    session.clear()
    flash("Logged out successfully.", "success")
    return redirect(url_for("login"))

@app.route("/settings")
@login_required
def settings():
    return render_template("settings.html")

@app.route("/delete-account", methods=["POST"])
@login_required
def delete_account():
    user_id = session.get("user")
    if not user_id:
        flash("You must be logged in to delete your account.", "danger")
        return redirect(url_for("login"))
        
    try:
        # Use the admin client if available, otherwise fallback to the main client
        client_to_use = supabase_admin if supabase_admin else supabase
        
        if not client_to_use:
            flash("Supabase is not configured properly.", "danger")
            return redirect(url_for("settings"))

        # Actual deletion using Supabase Admin API
        client_to_use.auth.admin.delete_user(user_id)
        
        # Also clean up the profile explicitly just in case
        try:
            client_to_use.table("profiles").delete().eq("id", user_id).execute()
        except:
            pass

        session.clear()
        flash("Your account has been permanently deleted. We are sorry to see you go.", "success")
        return redirect(url_for("signup"))
    except Exception as e:
        print(f"DEBUG: Account deletion failed: {e}")
        # If admin API fails (e.g. not a service role key), we explain the limitation
        err_str = str(e).lower()
        if "admin" in err_str or "403" in err_str or "401" in err_str or "user not allowed" in err_str:
             flash("Account deletion failed. This action requires the Supabase 'service_role' key. Please ensure your .env file has the correct SUPABASE_SECRET_KEY.", "danger")
        else:
            flash(f"Error processing account deletion: {str(e)}", "danger")
        return redirect(url_for("settings"))

@app.route("/test-supabase")
def test_supabase():
    if not supabase:
        return "Supabase client not initialized. Check your .env file."
    try:
        print("DEBUG: Testing Supabase storage connection...")
        buckets = supabase.storage.list_buckets()
        bucket_names = [b.name for b in buckets]
        print(f"DEBUG: Found buckets: {bucket_names}")
        return {
            "status": "success",
            "buckets": bucket_names,
            "message": f"Found {len(bucket_names)} buckets.",
            "url_used": SUPABASE_URL[:20] + "..."
        }
    except Exception as e:
        import traceback
        err_msg = str(e)
        trace = traceback.format_exc()
        print(f"--- SUPABASE TEST ERROR ---")
        print(trace)
        print(f"-----------------------------")
        return {
            "status": "error",
            "message": err_msg,
            "error_type": type(e).__name__,
            "tip": "Check if your SUPABASE_KEY is a full JWT (starts with eyJ) and not a short publishable key."
        }

@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    if request.method == "POST":
        file = request.files.get("data_file")
        if file is None or file.filename == "":
            flash("Please select a file to upload.", "warning")
            return redirect(url_for("index"))

        if not allowed_file(file.filename):
            flash("Unsupported file type. Please upload CSV, Excel, or JSON.", "danger")
            return redirect(url_for("index"))

        try:
            # Cleanup previous local file if it exists to save space
            old_filename = session.get("last_filename")
            if old_filename:
                old_path = UPLOAD_FOLDER / old_filename
                if old_path.exists():
                    try:
                        os.remove(old_path)
                    except:
                        pass

            # Read file bytes
            file_bytes = file.read()
            filename = secure_filename(file.filename)
            
            # Save file locally for current session processing
            local_path = UPLOAD_FOLDER / filename
            with open(local_path, "wb") as f:
                f.write(file_bytes)
            
            # Store in session
            session["last_filename"] = filename
            
            # Get tokens from session to authenticate the background worker
            access_token = session.get("access_token")
            refresh_token = session.get("refresh_token")

            # --- SUPABASE STORAGE UPLOAD (Background) ---
            if supabase:
                import threading
                def upload_to_supabase(content, path, acc_token, ref_token):
                    import time
                    max_retries = 3
                    base_delay = 1  # seconds
                    bucket_name = os.getenv("SUPABASE_BUCKET", "upload files")
                    
                    # Create a dedicated client for this thread to avoid global state issues
                    # and ensure we are authenticated as the specific user.
                    try:
                        thread_client = create_client(SUPABASE_URL, SUPABASE_KEY)
                        if acc_token:
                            thread_client.auth.set_session(acc_token, ref_token)
                    except Exception as client_err:
                        print(f"DEBUG: Failed to initialize threaded Supabase client: {client_err}")
                        return

                    # Supabase doesn't like backslashes in paths
                    clean_path = path.replace("\\", "/").strip()

                    for attempt in range(1, max_retries + 1):
                        try:
                            # Normalize the path and bucket name
                            
                            print(f"DEBUG: Starting upload (Attempt {attempt}/{max_retries})...")
                            print(f" - Bucket: '{bucket_name}'")
                            print(f" - Path:   '{clean_path}'")
                            print(f" - Size:   {len(content)} bytes")
                            
                            res = thread_client.storage.from_(bucket_name).upload(
                                path=clean_path,
                                file=content,
                                file_options={"upsert": "true", "content-type": "application/octet-stream"}
                            )
                            print(f"DEBUG: ✅ Upload SUCCESS! Response: {res}")
                            return  # Success, exit function
                            
                        except Exception as storage_err:
                            print(f"\n❌ SUPABASE UPLOAD FAILED (Attempt {attempt}/{max_retries}) ❌")
                            print(f"Bucket: {bucket_name}")
                            print(f"File:   {path}")
                            print(f"Error:  {type(storage_err).__name__}: {storage_err}")
                            if attempt < max_retries:
                                delay = base_delay * (2 ** (attempt - 1))
                                print(f"Retrying in {delay} seconds...")
                                time.sleep(delay)
                            else:
                                print(f"Max retries reached. Upload failed permanently.")
                                print(f"-------------------------------\n")

                # Remove daemon=True so the thread completes even if the request finishes quickly
                # pass tokens explicitly
                threading.Thread(target=upload_to_supabase, args=(file_bytes, filename, access_token, refresh_token)).start()

            return redirect(url_for("dashboard"))
        except Exception as exc:
            flash(f"Error processing file: {exc}", "danger")
            return redirect(url_for("index"))

    return render_template("index.html")

@app.route("/dashboard")
@login_required
def dashboard():
    filename = session.get("last_filename")
    if not filename:
        flash("No active session found. Please upload a file.", "warning")
        return redirect(url_for("index"))

    local_path = UPLOAD_FOLDER / filename
    if not local_path.exists():
        # Cloud Fallback: Try to download from Supabase if local file is missing
        if supabase:
            try:
                bucket_name = os.getenv("SUPABASE_BUCKET", "upload files")
                with open(local_path, "wb") as f:
                    res = supabase.storage.from_(bucket_name).download(filename)
                    f.write(res)
                # After download, proceed as normal
            except Exception as e:
                print(f"DEBUG: Cloud fallback failed: {e}")
                flash("Your file is no longer available locally or in the cloud. Please re-upload.", "danger")
                session.pop("last_filename", None)
                return redirect(url_for("index"))
        else:
            flash("Session expired or file not found. Please upload again.", "danger")
            session.pop("last_filename", None)
            return redirect(url_for("index"))

    try:
        # Process the data from the saved local file
        df = load_dataset(file_path=str(local_path))
        
        preview_table = df.head(20).to_html(
            classes="table table-hover table-sm",
            border=0,
            index=False,
        )

        summary_table = basic_statistics(df)
        column_info_table = column_overview(df)
        text_insights = generate_text_insights(df)
        charts = create_charts(df)

        row_count = len(df)
        column_count = df.shape[1]

        return render_template(
            "dashboard.html",
            preview_table=preview_table,
            summary_table=summary_table,
            column_info_table=column_info_table,
            text_insights=text_insights,
            charts=charts,
            row_count=row_count,
            column_count=column_count,
            filename=filename,
        )
    except Exception as exc:
        flash(f"Error loading dashboard: {exc}", "danger")
        return redirect(url_for("index"))

@app.route("/new-file")
@login_required
def new_file():
    # Cleanup current local file before starting fresh
    filename = session.get("last_filename")
    if filename:
        local_path = UPLOAD_FOLDER / filename
        if local_path.exists():
            try:
                os.remove(local_path)
            except:
                pass
                
    session.pop("last_filename", None)
    return redirect(url_for("index"))

@app.route("/health")
def health():
    return {
        "status": "ok",
        "service": "data-studio"
    }


# --- Supabase Keep-Alive (prevents free-tier auto-pause) ---
def _supabase_keepalive():
    """Background thread: pings Supabase every 4 days so the free-tier project
    never goes idle and triggers the 'Cannot connect to authentication server' error."""
    import time
    import threading

    INTERVAL_SECONDS = 4 * 24 * 60 * 60  # 4 days

    def _ping():
        while True:
            time.sleep(INTERVAL_SECONDS)
            try:
                client = get_supabase()
                if client:
                    # A lightweight call — just checks auth is reachable
                    client.auth.get_session()
                    print("DEBUG: Supabase keep-alive ping OK.")
            except Exception as e:
                # On failure, force a fresh client so the next real request
                # gets a clean connection instead of a stale one
                get_supabase(force_new=True)
                print(f"DEBUG: Supabase keep-alive ping failed, client refreshed: {e}")

    t = threading.Thread(target=_ping, daemon=True, name="supabase-keepalive")
    t.start()

# Only start the keep-alive in the main process (not the Flask reloader child)
if not os.environ.get("WERKZEUG_RUN_MAIN"):
    _supabase_keepalive()


if __name__ == "__main__":
    # Use PORT from environment (default 5000 for local, 10000 for Render)
    port = int(os.environ.get("PORT", 5000))
    # Keep debug=True for now, but deployment platforms usually override this via environment
    app.run(host="0.0.0.0", port=port, debug=True)
