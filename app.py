import os
import re
import csv
import io
import smtplib
import markdown
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, flash
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

# Load environment variables from .env
load_dotenv()
DISPLAY_NAME = os.getenv('display_name')
SENDER_EMAIL = os.getenv('sender_email')
PASSWORD = os.getenv('password')

# Load SMTP configuration from environment variables with fallback defaults
MAILER_HOST = os.getenv('MAILER_HOST', "smtp.mailersend.net")
MAILER_PORT = int(os.getenv('MAILER_PORT', "587"))

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Change for production

def process_csv_data(csv_content):
    """Process CSV content from a string and return list of rows and header names."""
    csv_io = io.StringIO(csv_content)
    reader = csv.DictReader(csv_io)
    rows = list(reader)
    headers = reader.fieldnames
    return rows, headers

def generate_message(template, row, headers):
    """Replace placeholders in the template with CSV row data."""
    message = template
    for header in headers:
        value = row.get(header, "")
        message = message.replace(f"${header}", value)
    return message

def extract_subject_and_body(content):
    """
    Extract email subject from content.
    If content contains a <title> tag, use its text as subject and remove it.
    Otherwise, take the first non-empty line as subject (for Markdown) and remove it from the body.
    """
    # Attempt HTML extraction
    pattern = r"<title>(.*?)</title>"
    match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
    if match:
        subj = match.group(1).strip()
        # Remove the <title> tag from content
        content = re.sub(pattern, "", content, flags=re.IGNORECASE | re.DOTALL)
        return subj, content

    # Fallback to Markdown: use first non-empty line as subject
    lines = content.splitlines()
    for i, line in enumerate(lines):
        if line.strip():
            subj = line.strip()
            # Remove the subject line from the content
            new_lines = lines[:i] + lines[i+1:]
            content = "\n".join(new_lines)
            return subj, content

    return "No Subject", content

def send_email(receiver, subject, text_message, html_message, attachments):
    """Create and send an email with text, HTML parts, and optional attachments."""
    multipart_msg = MIMEMultipart("alternative")
    multipart_msg["Subject"] = subject
    multipart_msg["From"] = f"{DISPLAY_NAME} <{SENDER_EMAIL}>"
    multipart_msg["To"] = receiver

    # Attach plain text and HTML versions.
    part1 = MIMEText(text_message, "plain")
    part2 = MIMEText(html_message, "html")
    multipart_msg.attach(part1)
    multipart_msg.attach(part2)

    # Attach each uploaded file (if any).
    if attachments:
        for file in attachments:
            if file.filename == "":
                continue
            filename = file.filename
            file_data = file.read()
            file.seek(0)
            attach_part = MIMEBase("application", "octet-stream")
            attach_part.set_payload(file_data)
            encoders.encode_base64(attach_part)
            attach_part.add_header("Content-Disposition", f"attachment; filename={filename}")
            multipart_msg.attach(attach_part)

    try:
        server = smtplib.SMTP(host=MAILER_HOST, port=MAILER_PORT)
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(user=SENDER_EMAIL, password=PASSWORD)
        server.sendmail(SENDER_EMAIL, receiver, multipart_msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"Error sending email to {receiver}: {e}")
        return False

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        # Choose email content source: upload template vs draft in app.
        template_source = request.form.get("template_source")
        if template_source == "upload":
            template_file = request.files.get("template_file")
            if not template_file:
                flash("Please upload a template file.", "error")
                return redirect(request.url)
            try:
                email_content = template_file.read().decode("utf-8")
            except Exception as e:
                flash("Error reading the uploaded file.", "error")
                return redirect(request.url)
        else:
            email_content = request.form.get("email_content")
            if not email_content or email_content.strip() == "":
                flash("Please draft your email before sending.", "error")
                return redirect(request.url)
        
        # Retrieve user-input subject (if any)
        user_subject = request.form.get("subject", "").strip()
        
        # Get attachments (if any)
        attachments = request.files.getlist("attachments")

        # Determine sending method: bulk vs manual.
        send_method = request.form.get("send_method")
        log_messages = []
        sent_count = 0
        failed_count = 0

        if send_method == "bulk":
            csv_file = request.files.get("csv_file")
            if not csv_file:
                flash("CSV file is required for bulk sending!", "error")
                return redirect(request.url)
            csv_content = csv_file.read().decode("utf-8")
            rows, headers = process_csv_data(csv_content)
            if not headers or "EMAIL" not in headers:
                flash("CSV must contain an 'EMAIL' header", "error")
                return redirect(request.url)
            for row in rows:
                receiver = row.get("EMAIL")
                if not receiver:
                    log_messages.append("Missing EMAIL for one row, skipping.")
                    continue
                msg_full = generate_message(email_content, row, headers)
                if user_subject:
                    subject_line = user_subject
                    body_to_send = msg_full
                else:
                    subject_line, body_to_send = extract_subject_and_body(msg_full)

                try:
                    html_version = body_to_send if "<html" in body_to_send.lower() else markdown.markdown(body_to_send)
                except Exception as e:
                    html_version = body_to_send

                if send_email(receiver, subject_line, body_to_send, html_version, attachments):
                    sent_count += 1
                    log_messages.append(f"Email sent to {receiver}")
                else:
                    failed_count += 1
                    log_messages.append(f"Failed to send email to {receiver}")
            flash(f"Emails sent: {sent_count}. Failed: {failed_count}", "info")
        else:
            # Manual sending method: single recipient.
            manual_email = request.form.get("manual_email")
            if not manual_email:
                flash("Please provide an email address for manual sending.", "error")
                return redirect(request.url)
            # For manual sending, we use the same content for all.
            if user_subject:
                subject_line = user_subject
                body_to_send = email_content
            else:
                subject_line, body_to_send = extract_subject_and_body(email_content)

            try:
                html_version = body_to_send if "<html" in body_to_send.lower() else markdown.markdown(body_to_send)
            except Exception as e:
                html_version = body_to_send

            if send_email(manual_email, subject_line, body_to_send, html_version, attachments):
                flash(f"Email sent successfully to {manual_email}.", "info")
                log_messages.append(f"Email sent to {manual_email}")
            else:
                flash(f"Failed to send email to {manual_email}.", "error")
                log_messages.append(f"Failed to send email to {manual_email}")

        return render_template("result.html", log_messages=log_messages)

    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)
