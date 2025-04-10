# 📬 Bulk Email Sender Web UI

A sleek, modern, and super handy web UI for sending customized emails in bulk or manually! Whether you're running a marketing campaign, sending invitations, or just blasting out an update — this tool has you covered. Users can either **upload their own HTML template** or **draft the email right inside the app** using a powerful rich text editor.

Built with ❤️ using **Flask**, **Bootstrap 5**, **Quill**, and **Marked.js**.

---

## ✨ Features

- ⚙️ **Dual Email Content Options**  
  - Upload a ready-made HTML or Markdown email template  
  - OR draft your email with a rich text editor and HTML editor side by side

- 🪞 **Live Email Preview**  
  Real-time rendering of your email content to see exactly what your recipient will receive.

- 📤 **Multiple Sending Modes**  
  - **Bulk Sending:** Upload a CSV with multiple email addresses (must have `EMAIL` column)  
  - **Manual Sending:** Send a one-off email to a specific recipient directly

- 📎 **Attachments Support**  
  Add one or more attachments to your emails. Great for flyers, PDFs, or sneaky memes.

- 🔐 **Secure SMTP Config via Environment Variables**  
  No need to hardcode sensitive info. Configure SMTP credentials with `.env`.

- 🧠 **Smart UI**  
  Form sections show/hide based on what you’re doing, making the whole process feel intuitive and clutter-free.

- 🙏 **Inspired By & Credit**  
  Massive props to [aahnik/bulk-email-sender](https://github.com/aahnik/bulk-email-sender) for the foundational concept.

---

## 🛠️ Setup

### ✅ Prerequisites

- Python 3.6 or newer
- `pip` package manager
- (Optional but recommended) virtual environment manager

### 🚀 Installation

1. **Clone the Repository**

   ```bash
   git clone https://github.com/supratimrk/web-bulk-email-sender.git
   cd web-bulk-email-sender
   ```

2. **Create and Activate a Virtual Environment**

   **macOS/Linux:**

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

   **Windows:**

   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```

3. **Install Dependencies**

   ```bash
   pip install Flask python-dotenv Markdown
   ```

4. **Set Up Environment Variables**

   Create a `.env` file in the project root with the following content:

   ```dotenv
   display_name=Mr.Bean
   sender_email=your@example.com
   password=your_app_password
   MAILER_HOST=smtp.mailersend.net
   MAILER_PORT=587
   ```

   > 🔐 **Note:** If using Gmail, enable 2FA and create an [App Password](https://support.google.com/accounts/answer/185833?hl=en) for security.

---

## 📁 Project Structure

```
web-bulk-email-sender/
├── app.py               # Flask app (routes + email logic)
├── .env                 # Your SMTP config (never commit this!)
└── templates/
    ├── index.html       # Main form UI with editor, options, preview
    └── result.html      # Status/result log after sending
```

---

## 🧪 How It Works

1. **Choose Email Content Source:**
   - Upload a file (HTML/Markdown)
   - OR use the built-in rich text + HTML editor

2. **Compose & Preview:**
   - Use Quill for rich text or input raw HTML
   - Click "Preview Email" to see the final render live

3. **Choose Recipients:**
   - Upload a CSV with email addresses under the `EMAIL` column  
   - OR type a single email manually

4. **(Optional) Attach Files:**
   - Upload any supporting files you want to include

5. **Click Send:**
   - Submit the form and let it fly!  
   - You’ll be redirected to a result page that logs success/failure for each recipient

---

## 🧑‍💻 Running Locally

Start the development server:

```bash
python app.py
```

Visit in browser:  
👉 [http://127.0.0.1:5000/](http://127.0.0.1:5000/)

---

## 🙌 Contributions Welcome!

Got ideas? Want to fix bugs or add features?  
**Feel free to fork this repo, make your changes, and submit a pull request.**

We love contributors! 💙

---

## 🧠 Credits

- Based on the idea from [aahnik/bulk-email-sender](https://github.com/aahnik/bulk-email-sender)
- Frontend powered by:
  - [Bootstrap 5](https://getbootstrap.com/)
  - [Quill.js](https://quilljs.com/)
  - [Marked.js](https://marked.js.org/)

---

## 📄 License

MIT License – free to use, tweak, share, or build on!  
Just don’t forget to give credit where it’s due. 😄

---

### Happy Emailing! 🚀