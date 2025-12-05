# Developer Guide for ChupChap Pathshala

Welcome to the team! Follow these instructions to set up the project and contribute code.

## 1. Initial Setup

### Step 1: Clone the Repository
Open your terminal (Command Prompt or Git Bash) and run:
```bash
git clone https://github.com/rakibulhasanrihad10/ChupChapPathshala.git
cd ChupChapPathshala
```

### Step 2: Create a Virtual Environment
It's important to keep our project dependencies isolated.
```bash
# Windows
python -m venv venv
venv\Scripts\activate
```
*You should see `(venv)` at the start of your command line.*

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables
We use a hidden `.env` file for secrets. You need to create one.
1.  Copy the example file:
    ```bash
    copy .env.example .env
    ```
2.  (Optional) Edit `.env` if you need to change the secret key, but the default is fine for development.

### Step 5: Setup Database
Initialize the database and add some sample books so the app isn't empty.
```bash
flask db upgrade
python seed_books.py
```

### Step 6: Run the App
```bash
flask run
```
Go to `http://localhost:5000` in your browser.

---

## 2. Contribution Workflow

**IMPORTANT:** Never push directly to the `main` branch. Always work on your own branch.

### Step 1: Update your Main Branch
Before starting new work, make sure you have the latest code.
```bash
git checkout main
git pull origin main
```

### Step 2: Create a New Branch
Name your branch based on what you are doing (e.g., `add-login-page`, `fix-cart-bug`).
```bash
git checkout -b your-feature-name
```

### Step 3: Write Code & Save
Make your changes. When you are done:
```bash
git add .
git commit -m "Description of what you changed"
```

### Step 4: Publish Your Branch
```bash
git push origin your-feature-name
```

### Step 5: Create a Pull Request (PR)
1.  Go to the GitHub repository page.
2.  You will see a prompt "Compare & pull request". Click it.
3.  Write a description of your changes and click **Create Pull Request**.
4.  Wait for a team member to review and merge your code.
