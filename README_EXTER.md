# SDM Manager

A web-based MCQ (Multiple Choice Question) Manager with AI-powered intent detection, Azure AD CIAM authentication, and CSV file upload support.

---

## 🌐 Live App

👉 [https://sdm-manager-app.azurewebsites.net](https://sdm-manager-app.azurewebsites.net)

---

## 🚀 Features

- Upload CSV files with MCQ questions
- AI-powered chat to add, edit, delete questions
- Azure AD CIAM login (sign up with any email)
- Group-based question management
- Auto-deploy via GitHub Actions

---

## 🛠️ Local Setup

### Prerequisites

- Python 3.11
- Git
- A Groq API key (get one free at [https://console.groq.com](https://console.groq.com))

### Step 1 — Clone the repo

```bash
git clone https://github.com/Kishoth02/sdm-manager.git
cd sdm-manager
```

### Step 2 — Create virtual environment

```bash
python -m venv .venv
```

Activate it:

- **Windows:** `.venv\Scripts\activate`
- **Mac/Linux:** `source .venv/bin/activate`

### Step 3 — Install dependencies

```bash
pip install -r requirements.txt
```

### Step 4 — Create `.env` file

Create a file named `.env` in the root folder and add these values:

```env
GROQ_API_KEY=your_groq_api_key_here
CLIENT_ID=your_azure_client_id
TENANT_ID=your_azure_tenant_id
CLIENT_SECRET=your_azure_client_secret
TENANT_SUBDOMAIN=your_tenant_subdomain
REDIRECT_URI=http://localhost:8002/auth/callback
SESSION_SECRET=any_random_string_here
```

> ⚠️ Never commit your `.env` file to GitHub — it's already in `.gitignore`

### Step 5 — Run the app

```bash
python main.py
```

Open your browser and go to: [http://localhost:8002](http://localhost:8002)

---

## 👥 Contributing (For Teammates)

### Step 1 — Create your own branch

```bash
git checkout -b feature/your-feature-name
```

### Step 2 — Make your changes

Edit the code, test locally, then:

```bash
git add .
git commit -m "describe what you changed"
git push origin feature/your-feature-name
```

### Step 3 — Create a Pull Request

- Go to [https://github.com/Kishoth02/sdm-manager](https://github.com/Kishoth02/sdm-manager)
- Click **"Compare & pull request"**
- Describe your changes
- Submit for review

Once the Pull Request is merged to `master`, GitHub Actions will **automatically deploy** to Azure. No manual steps needed!

---

## 📁 Project Structure

```
sdm-manager/
├── main.py              # FastAPI app entry point
├── ms_auth.py           # Azure AD CIAM authentication
├── auth.py              # Auth helpers
├── requirements.txt     # Python dependencies
├── routes/
│   └── api.py           # API routes
├── services/
│   ├── ai_service.py    # Groq AI intent detection
│   └── file_manager.py  # CSV file management
├── static/
│   └── index.html       # Frontend UI
└── .github/
    └── workflows/
        └── deploy.yml   # GitHub Actions auto-deploy
```

---

## ⚙️ Environment Variables

| Variable | Description |
|---|---|
| `GROQ_API_KEY` | Groq API key for AI intent detection |
| `CLIENT_ID` | Azure AD CIAM app client ID |
| `TENANT_ID` | Azure AD CIAM tenant ID |
| `CLIENT_SECRET` | Azure AD CIAM client secret |
| `TENANT_SUBDOMAIN` | Azure CIAM tenant subdomain |
| `REDIRECT_URI` | Auth callback URL |
| `SESSION_SECRET` | Secret key for session encryption |

---

## 🔄 Deployment

Deployment is fully automated via GitHub Actions.

Every push to `master` branch automatically deploys to Azure Web App.

```
git push origin master → GitHub Actions → Azure App Service
```

> ⚠️ Environment variables are stored in Azure App Settings — not in the code. Contact the project owner for production credentials.

---

## 📞 Contact

For access to environment variables or Azure credentials, contact the project owner.