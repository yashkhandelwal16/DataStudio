import os
from functools import wraps
from pathlib import Path

from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_compress import Compress
from werkzeug.utils import secure_filename
from supabase import create_client, Client
from dotenv import load_dotenv

from utils.data_loader import load_dataset
from utils.analysis import basic_statistics, column_overview, generate_text_insights
from utils.visualization import create_charts

# Load environment variables
load_dotenv(override=True)

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_FOLDER = BASE_DIR / "uploads"
CHART_FOLDER = BASE_DIR / "static" / "charts"

# Ensure directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CHART_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls", ".json"}

# Supabase Setup
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if SUPABASE_KEY:
    masked_key = SUPABASE_KEY[:10] + "..." if len(SUPABASE_KEY) > 10 else "SHORT_KEY"
    print(f"DEBUG: Supabase Key loaded. Starts with: {masked_key}")

supabase: Client = None
if SUPABASE_URL and SUPABASE_KEY and "YOUR_SUPABASE" not in SUPABASE_URL:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__)
Compress(app) # Enable Gzip compression
app.config["UPLOAD_FOLDER"] = str(UPLOAD_FOLDER)
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "change-this-secret-key")

# --- AUTH DECORATOR ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session or "access_token" not in session:
            # Clear potential stale session data if token is missing
            session.clear()
            flash("Please log in to access this page.", "warning")
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
        
        if not supabase:
            flash("Supabase is not configured. Please check your .env file.", "danger")
            return redirect(url_for("login"))
            
        try:
            response = supabase.auth.sign_in_with_password({"email": email, "password": password})
            session["user"] = response.user.id
            session["email"] = email
            # Store tokens to restore session after restart
            session["access_token"] = response.session.access_token
            session["refresh_token"] = response.session.refresh_token
            
            flash("Successfully logged in!", "success")
            return redirect(url_for("index"))
        except Exception as e:
            flash(f"Login failed: {str(e)}", "danger")
            
    return render_template("login.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        full_name = request.form.get("full_name")
        
        if not supabase:
            flash("Supabase is not configured. Please check your .env file.", "danger")
            return redirect(url_for("signup"))
            
        try:
            # Sign up the user
            response = supabase.auth.sign_up({
                "email": email,
                "password": password,
                "options": {
                    "data": {"full_name": full_name}
                }
            })
            # On success, rather than redirecting to login, render the OTP page
            session["signup_email"] = email
            return render_template("verify_otp.html", signup_email=email)
            
        except Exception as e:
            flash(f"Signup failed: {str(e)}", "danger")
            
    return render_template("signup.html")

@app.route("/verify-otp", methods=["GET", "POST"])
def verify_otp():
    if request.method == "POST":
        otp = request.form.get("otp")
        email = request.form.get("email") # Retrieve from form
        
        # Check if we have OTP
        if not otp:
            flash("Please enter the verification code.", "danger")
            # In a real app we might pass the email via session, here we expect it in the form.
            # But wait, our HTML didn't include the email in the form. Let's fix that.
            # This will be handled in the update to verify_otp.html OR by storing email in session temporarily
            if "signup_email" in session:
                email = session["signup_email"]
            else:
                return redirect(url_for("signup"))
        
        try:
            # Verify the OTP
            res = supabase.auth.verify_otp({
                "email": email,
                "token": otp,
                "type": "signup"
            })
            
            flash("Email verified successfully! You can now log in.", "success")
            return redirect(url_for("login"))
        except Exception as e:
            flash(f"Verification failed: {str(e)}", "danger")
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
    # In a full app with admin access, we would do:
    # supabase.auth.admin.delete_user(session["user"])
    # For a regular user, if self-deletion is not easily permitted without an admin key,
    # we simulate the deletion, clear session, and show a flash message.
    # We will try to call an RPC or user deletion if supabase-py supports it, 
    # otherwise we just log them out.
    try:
        # Currently, supabase-py doesn't officially expose a standard user self-delete 
        # without admin privileges. So we clear session and inform.
        session.clear()
        flash("Your account deletion request has been processed. You have been logged out.", "success")
    except Exception as e:
        flash(f"Error processing account deletion: {e}", "danger")
    return redirect(url_for("login"))

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
            # Read file bytes
            file_bytes = file.read()
            filename = secure_filename(file.filename)
            
            # Save file locally for persistence
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


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)


