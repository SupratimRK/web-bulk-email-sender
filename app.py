import os
import re
import csv
import io
import smtplib
import markdown
import html2text
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, flash
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from werkzeug.utils import secure_filename

# Load environment variables from .env
load_dotenv()
DEFAULT_DISPLAY_NAME = os.getenv('display_name', 'Default Sender Name')
SENDER_EMAIL = os.getenv('sender_email')
PASSWORD = os.getenv('password')

# Load SMTP configuration
MAILER_HOST = os.getenv('MAILER_HOST', "smtp.mailersend.net")
MAILER_PORT = int(os.getenv('MAILER_PORT', "587"))

# Basic validation for required env vars
if not SENDER_EMAIL or not PASSWORD:
    print("Error: SENDER_EMAIL and PASSWORD must be set in the .env file.")
    # Consider exiting or handling this more gracefully depending on deployment
    # exit(1)

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', "a_default_but_less_secure_key")

ALLOWED_EXTENSIONS_TEMPLATE = {'html', 'htm', 'md', 'txt'} # Added htm
ALLOWED_EXTENSIONS_CSV = {'csv'}

def allowed_file(filename, allowed_extensions):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

def process_csv_data(csv_content):
    try:
        csv_io = io.StringIO(csv_content)
        # Handle potential BOM (Byte Order Mark) which can interfere with sniffing/headers
        if csv_io.getvalue().startswith('\ufeff'):
             csv_io = io.StringIO(csv_content.lstrip('\ufeff'))

        # Increase sample size for sniffing if needed, though 1024 is often enough
        try:
            dialect = csv.Sniffer().sniff(csv_io.read(2048)) # Increased sample size
        except csv.Error:
             # If sniffing fails, assume standard comma-separated CSV
             print("Warning: CSV Sniffing failed, assuming comma delimiter.")
             dialect = csv.excel # Default fallback
        csv_io.seek(0)

        reader = csv.DictReader(csv_io, dialect=dialect)
        if not reader.fieldnames:
            print("Error processing CSV: No header row found.")
            return None, None
        headers = [header.strip().lower() for header in reader.fieldnames]
        # Check for empty headers which can cause issues
        if '' in headers:
             print("Warning: Empty column header(s) found in CSV.")
             # Option: filter them out or raise error depending on strictness
             headers = [h for h in headers if h]

        # Re-create reader with cleaned headers to ensure consistency
        csv_io.seek(0)
        reader = csv.DictReader(csv_io, dialect=dialect) # Reread with potentially cleaned headers
        reader.fieldnames = [h.strip().lower() for h in reader.fieldnames] # Ensure lowercase/strip again

        rows = list(reader)
        return rows, headers
    except Exception as e:
        print(f"Error processing CSV: {e}")
        return None, None

def generate_message(template, row, headers):
    message = template
    # Ensure row keys are lowercase for case-insensitive matching
    row_lower = {str(k).lower(): str(v) for k, v in row.items() if k is not None}
    for header in headers:
        # Get value using the lowercase header, provide empty string if missing
        value = row_lower.get(header, "")
        # Use regex for robust replacement ($header and ${header})
        # Ensure header is properly escaped for regex if it contains special chars
        escaped_header = re.escape(header)
        message = re.sub(rf'\${{{escaped_header}}}|\${escaped_header}', value, message, flags=re.IGNORECASE)
    return message

def extract_subject_and_body(content):
    # Improved Title Extraction (handles attributes, case-insensitivity better)
    pattern = r"<title[^>]*>(.*?)</title>"
    match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
    if match:
        subj = match.group(1).strip()
        # Remove the title tag and surrounding whitespace carefully
        content = re.sub(pattern, "", content, count=1, flags=re.IGNORECASE | re.DOTALL).strip()
        # Remove potential leftover empty lines at the beginning
        content = re.sub(r"^\s*\n", "", content)
        return subj, content

    # Fallback: First non-empty, non-tag-like line as subject
    lines = content.splitlines()
    subj = "No Subject" # Default if no suitable line found
    body_start_index = 0
    for i, line in enumerate(lines):
        stripped_line = line.strip()
        if stripped_line: # Is it a non-empty line?
             # Check if it looks like a tag
             if not re.match(r"^\s*<", stripped_line):
                 subj = stripped_line
                 body_start_index = i + 1
                 break # Found subject
             else:
                 # It's a tag-like line, assume no plain text subject exists before HTML
                 body_start_index = i # Start body from this line
                 break
    body_content = "\n".join(lines[body_start_index:]).strip()
    return subj, body_content


def send_email(receiver, subject, html_message, attachments, display_name):
    """Create and send an email with HTML, plain text, attachments, and custom display name."""
    if not SENDER_EMAIL or not PASSWORD:
        return False, "Sender email or password not configured."

    multipart_msg = MIMEMultipart("alternative")
    multipart_msg["Subject"] = subject
    # Use the passed 'display_name' and format the From header correctly
    multipart_msg["From"] = f"{display_name} <{SENDER_EMAIL}>"
    multipart_msg["To"] = receiver

    # Generate plain text version
    try:
        h = html2text.HTML2Text()
        h.ignore_links = False
        h.body_width = 0 # Don't wrap lines
        plain_text_message = h.handle(html_message)
    except Exception as e:
        print(f"Warning: Could not generate plain text for {receiver}: {e}")
        plain_text_message = "HTML content could not be converted to plain text. Please view this email in an HTML-compatible client."

    part1 = MIMEText(plain_text_message, "plain", "utf-8")
    part2 = MIMEText(html_message, "html", "utf-8")
    multipart_msg.attach(part1)
    multipart_msg.attach(part2)

    # Handle Attachments
    if attachments:
        for file in attachments:
            # Ensure file object is valid and has a filename
            if file and hasattr(file, 'filename') and file.filename:
                try:
                    filename = secure_filename(file.filename)
                    if not filename: # secure_filename might return empty string for weird names
                         filename = "attachment" # Provide a default name
                    file.seek(0) # Ensure reading from the start
                    file_data = file.read()
                    file.seek(0) # Reset pointer if file needs to be read again elsewhere
                    attach_part = MIMEBase("application", "octet-stream")
                    attach_part.set_payload(file_data)
                    encoders.encode_base64(attach_part)
                    attach_part.add_header("Content-Disposition", f"attachment; filename=\"{filename}\"") # Use quotes for filenames with spaces
                    multipart_msg.attach(attach_part)
                except Exception as e:
                    print(f"Error attaching file {getattr(file, 'filename', 'N/A')}: {e}")
                    # Decide whether to fail the whole email or just skip the attachment
                    log_msg = f"Warning: Could not attach file {getattr(file, 'filename', 'N/A')} for {receiver}. Error: {e}. Email sent without it."
                    print(log_msg) # Log locally
                    # Optionally return a specific status/message indicating attachment failure? For now, just log.
                    # return False, f"Error attaching file {file.filename}: {e}" # This would stop the email

    # Send Email via SMTP
    try:
        # Context manager ensures server.quit() is called
        with smtplib.SMTP(host=MAILER_HOST, port=MAILER_PORT, timeout=30) as server:
            server.ehlo()
            # Start TLS if not using implicit TLS port (465)
            if MAILER_PORT != 465:
                server.starttls()
                server.ehlo() # Re-identify after starting TLS
            server.login(user=SENDER_EMAIL, password=PASSWORD)
            server.sendmail(SENDER_EMAIL, receiver, multipart_msg.as_string())
        return True, f"Email successfully sent to {receiver}"
    except smtplib.SMTPAuthenticationError as e:
        error_msg = f"SMTP Authentication Error: {e}. Check SENDER_EMAIL and PASSWORD in .env."
        print(error_msg)
        return False, error_msg
    except smtplib.SMTPServerDisconnected:
        error_msg = f"SMTP Server Disconnected unexpectedly for {receiver}. Check connection/server limits."
        print(error_msg)
        return False, error_msg
    except smtplib.SMTPException as e:
        error_msg = f"SMTP Error sending to {receiver}: {e}"
        print(error_msg)
        return False, error_msg
    except OSError as e: # Handle potential network/socket errors
         error_msg = f"Network/OS Error sending to {receiver}: {e}"
         print(error_msg)
         return False, error_msg
    except Exception as e:
        # Catch broader exceptions as a fallback
        error_msg = f"An unexpected error occurred sending to {receiver}: {e.__class__.__name__} - {e}"
        print(error_msg)
        return False, error_msg


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        email_content_raw = ""
        is_markdown = False
        is_plain_text = False # Flag for potential plain text

        # --- 1. Get Email Content ---
        template_source = request.form.get("template_source")
        if template_source == "upload":
            template_file = request.files.get("template_file")
            if not template_file or not template_file.filename:
                flash("Please select a template file to upload.", "error")
                return redirect(request.url)
            if not allowed_file(template_file.filename, ALLOWED_EXTENSIONS_TEMPLATE):
                 flash(f"Invalid template file type. Allowed: {', '.join(ALLOWED_EXTENSIONS_TEMPLATE)}", "error")
                 return redirect(request.url)
            try:
                # Read as bytes first to handle potential encoding issues, then decode
                email_content_bytes = template_file.read()
                try:
                    # Try UTF-8 first, common standard
                    email_content_raw = email_content_bytes.decode("utf-8")
                except UnicodeDecodeError:
                    # Fallback to latin-1 or others if needed
                    try:
                        email_content_raw = email_content_bytes.decode("latin-1")
                        flash("Warning: Template file wasn't standard UTF-8, decoded using Latin-1.", "warning")
                    except Exception as decode_err:
                         flash(f"Error decoding template file: {decode_err}. Ensure it's UTF-8 or Latin-1 encoded.", "error")
                         return redirect(request.url)

                filename_lower = template_file.filename.lower()
                if filename_lower.endswith('.md'):
                    is_markdown = True
                elif filename_lower.endswith('.txt'):
                    is_plain_text = True # Explicitly TXT
                # Heuristic: If no common HTML tags detected early, treat as markdown/plain
                elif not re.search(r'<html|<body|<div|<p|<br|</?a\s|</?img\s', email_content_raw[:1000], re.IGNORECASE):
                    is_markdown = True # Treat as markdown if unsure and not TXT
                    flash("Info: Uploaded content doesn't look like HTML, attempting Markdown conversion.", "info")

            except Exception as e:
                flash(f"Error reading the uploaded file: {e}", "error")
                return redirect(request.url)
        else: # Source is 'draft'
            email_content_raw = request.form.get("email_content")
            if not email_content_raw or not email_content_raw.strip():
                flash("Please draft your email content before sending.", "error")
                return redirect(request.url)
            # For drafted content, assume it's HTML unless explicitly plain text
            # The preview logic already handles potential markdown conversion if needed based on context

        # --- 2. Get Subject and Custom Display Name ---
        user_subject_template = request.form.get("subject", "").strip()
        custom_display_name = request.form.get("custom_display_name", "").strip()
        final_display_name = custom_display_name if custom_display_name else DEFAULT_DISPLAY_NAME

        # --- 3. Get Attachments ---
        attachments = request.files.getlist("attachments")

        # --- 4. Prepare Sending List and Parameters ---
        send_method = request.form.get("send_method")
        log_messages = []
        sent_count = 0
        failed_count = 0
        skipped_count = 0 # Track skipped rows explicitly
        recipients_data = []
        headers = []

        if send_method == "bulk":
            csv_file = request.files.get("csv_file")
            if not csv_file or not csv_file.filename:
                flash("CSV file is required for bulk sending!", "error")
                return redirect(request.url)
            if not allowed_file(csv_file.filename, ALLOWED_EXTENSIONS_CSV):
                flash("Invalid file type for recipients. Please upload a CSV file.", "error")
                return redirect(request.url)
            try:
                # Read as bytes and decode carefully
                csv_content_bytes = csv_file.read()
                try:
                    csv_content = csv_content_bytes.decode("utf-8-sig") # Handles UTF-8 with BOM
                except UnicodeDecodeError:
                     try:
                         csv_content = csv_content_bytes.decode("latin-1")
                         flash("Warning: CSV file wasn't standard UTF-8, decoded using Latin-1.", "warning")
                     except Exception as decode_err:
                         flash(f"Error decoding CSV file: {decode_err}. Ensure it's UTF-8 or Latin-1 encoded.", "error")
                         return redirect(request.url)
            except Exception as e:
                flash(f"Error reading CSV file: {e}", "error")
                return redirect(request.url)

            rows, headers = process_csv_data(csv_content)
            if rows is None:
                flash("Error processing CSV file. Check format, encoding, and headers.", "error")
                return redirect(request.url)

            # More robust email header detection
            email_column_name = None
            possible_headers = ['email', 'email address', 'email_address', 'e-mail', 'recipient']
            if headers: # Check only if headers exist
                 for ph in possible_headers:
                     if ph in headers:
                         email_column_name = ph
                         break
                 if email_column_name is None: # Still not found? Try finding any header containing 'mail'
                     for h in headers:
                         if 'mail' in h:
                             email_column_name = h
                             flash(f"Warning: Standard 'email' header not found. Using '{h}' as the email column.", "warning")
                             break

            if email_column_name is None:
                flash(f"CSV must contain a recognized email header (e.g., 'email', 'email_address'). Found: {', '.join(headers) if headers else 'None'}", "error")
                return redirect(request.url)

            for i, row in enumerate(rows):
                # Check if row is completely empty (can happen with extra newlines in CSV)
                if not any(row.values()):
                    log_messages.append(f"Skipping row {i+2}: Empty row.") # +2 because header is row 1, data starts row 2
                    skipped_count += 1
                    continue

                receiver = row.get(email_column_name, "").strip()
                # Basic email format check (presence of '@')
                if not receiver or '@' not in receiver:
                    log_messages.append(f"Skipping row {i+2}: Invalid or missing email in '{email_column_name}' column ('{receiver}').")
                    skipped_count += 1
                    continue
                recipients_data.append({'email': receiver, 'data': row})

        else: # Manual sending
            manual_email = request.form.get("manual_email", "").strip()
            if not manual_email or '@' not in manual_email:
                flash("Please provide a valid recipient email address for manual sending.", "error")
                return redirect(request.url)
            recipients_data.append({'email': manual_email, 'data': {}})
            headers = [] # No headers for manual send

        # --- 5. Process and Send Emails ---
        if not recipients_data:
             # *** ADDED: Handle no valid recipients even if CSV was processed ***
             final_status = "warning"
             if skipped_count > 0 :
                 flash(f"Processing complete. No valid recipients found. Skipped {skipped_count} row(s).", final_status)
             else:
                  flash("No recipients specified or found in the provided source.", final_status)

             # *** ADDED: Prepare navbar status for no recipients case ***
             navbar_status_icon = "bi-exclamation-triangle-fill text-warning"
             navbar_status_text = f"Finished: 0 sent, {skipped_count} skipped." if skipped_count > 0 else "Finished: No recipients."
             navbar_status_html = f'<i class="bi {navbar_status_icon} me-1"></i>{navbar_status_text}'

             return render_template("result.html",
                                    log_messages=log_messages,
                                    navbar_status_html=navbar_status_html) # Pass status

        # Configure Markdown parser
        md = markdown.Markdown(extensions=['extra', 'nl2br', 'smarty']) # Added smarty for quotes etc.

        for recipient_info in recipients_data:
            receiver = recipient_info['email']
            row_data = recipient_info['data']

            personalized_content = generate_message(email_content_raw, row_data, headers)

            # Determine Subject
            if user_subject_template:
                subject_line = generate_message(user_subject_template, row_data, headers)
                body_to_process = personalized_content
            else:
                subject_line, body_to_process = extract_subject_and_body(personalized_content)
                if subject_line == "No Subject":
                     subject_line = f"{final_display_name} Information" # More specific default

            # Convert body to HTML if necessary
            try:
                if is_markdown:
                    final_html_body = md.convert(body_to_process)
                elif is_plain_text:
                     # Convert plain text to basic HTML (preserving line breaks)
                     final_html_body = f"<pre style='font-family: sans-serif; white-space: pre-wrap;'>{body_to_process}</pre>"
                else:
                    # Assume it's already HTML or the draft editor provided HTML
                    final_html_body = body_to_process
            except Exception as e:
                log_messages.append(f"FAILED: Error preparing content for {receiver}: {e}. Skipping email.")
                failed_count += 1
                md.reset() # Reset parser state
                continue # Skip sending this email

            # Send the email
            # Pass 'final_display_name' to send_email
            success, message = send_email(receiver, subject_line, final_html_body, attachments, final_display_name)

            if success:
                sent_count += 1
                log_messages.append(f"SUCCESS: {message}")
            else:
                failed_count += 1
                # Ensure the message from send_email is logged as failure reason
                log_messages.append(f"FAILED: {message}")

            # Reset markdown parser state for next email, crucial if using extensions with state
            md.reset()

        # --- 6. Report Results ---
        final_status = "info" # Default status
        if failed_count > 0 and sent_count == 0 and skipped_count == 0:
            final_status = "danger" # All attempts failed
        elif failed_count > 0 or skipped_count > 0:
            final_status = "warning" # Partial success or some issues
        elif sent_count > 0:
             final_status = "success" # All attempted emails sent successfully

        # Prepare summary message for flash and navbar
        summary_parts = []
        if sent_count > 0: summary_parts.append(f"{sent_count} sent")
        if failed_count > 0: summary_parts.append(f"{failed_count} failed")
        if skipped_count > 0: summary_parts.append(f"{skipped_count} skipped")
        if not summary_parts: summary_parts.append("No emails processed")

        summary_message = f"Processing complete. {', '.join(summary_parts)}."
        flash(summary_message, final_status)

        # *** ADDED: Prepare Navbar Status HTML for Result Page ***
        navbar_status_icon = "bi-info-circle text-secondary" # Default
        if final_status == "success":
            navbar_status_icon = "bi-check-circle-fill text-success"
        elif final_status == "warning":
            navbar_status_icon = "bi-exclamation-triangle-fill text-warning"
        elif final_status == "danger":
            navbar_status_icon = "bi-x-octagon-fill text-danger"

        # Use a concise version for the navbar text
        navbar_status_text = ', '.join(summary_parts)
        navbar_status_html = f'<i class="bi {navbar_status_icon} me-1"></i>{navbar_status_text}'

        return render_template("result.html",
                               log_messages=log_messages,
                               navbar_status_html=navbar_status_html) # Pass the generated HTML

    # For GET request
    return render_template("index.html") # No need to pass navbar status here, JS handles it

if __name__ == "__main__":
    # Use host='0.0.0.0' to make it accessible on your network
    # Use debug=False in production
    app.run(host='0.0.0.0', port=5000, debug=True)