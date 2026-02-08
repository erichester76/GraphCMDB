# Getting Started with GraphCMDB

## ⚠️ Important: First Time Setup

**You can't log in without a user!** This guide will help you create your first admin user.

## Step-by-Step Setup

### 1. Install Dependencies

```bash
# Python dependencies
pip install -r requirements.txt

# Node.js dependencies (for Tailwind CSS)
npm install
```

### 2. Setup Database

```bash
# Run Django migrations to create auth tables
python manage.py migrate
```

This creates the SQLite database file `db.sqlite3` which stores user accounts.

### 3. Create Your First Admin User ⭐

**This is the most important step!** You have three options:

#### Option A: Interactive Setup (Recommended for First-Time Users)

```bash
python setup_admin.py
```

This script provides:
- ✅ Friendly prompts and validation
- ✅ Checks for existing users
- ✅ Clear next steps after completion

**Example interaction:**
```
============================================================
  GraphCMDB - First Admin User Setup
============================================================

Welcome! This script will help you create your first admin user.
You'll need this user to log in and manage the system.

Checking database setup...
✓ Database is ready

------------------------------------------------------------
Please provide the following information:
------------------------------------------------------------

Username: admin
Email address (optional, press Enter to skip): admin@example.com
Password: ********
Password (again): ********

Creating admin user...

============================================================
  ✅ SUCCESS! Admin user created successfully!
============================================================

Username: admin

Next steps:

1. Start the development server:
   python manage.py runserver

2. Open your browser and navigate to:
   http://localhost:8000/users/login/

3. Log in with your username and password

4. Start managing your CMDB!
```

#### Option B: Django Management Command (Quick & Standard)

```bash
python manage.py createsuperuser
```

You'll be prompted for:
```
Username: admin
Email address: admin@example.com
Password: ********
Password (again): ********
```

#### Option C: Non-Interactive (For Scripts/Automation)

```bash
# Set password via environment variable
export DJANGO_SUPERUSER_PASSWORD='MySecurePassword123!'
python manage.py createsuperuser --noinput --username admin --email admin@example.com
```

### 4. Build Static Files (Optional but Recommended)

```bash
# Compile Tailwind CSS
npm run build
```

### 5. Start the Server

```bash
python manage.py runserver
```

The server will start on http://localhost:8000

### 6. Log In! 🎉

1. Navigate to: http://localhost:8000/users/login/
2. Enter your username and password
3. Click "Sign in"
4. You'll be redirected to the dashboard

## What's Next?

After logging in as an admin, you can:

### Create More Users

1. From the sidebar, click **"Users"**
2. Click **"Add User"** button
3. Enter user details
4. Save

Or visit the Django admin panel: http://localhost:8000/admin/

### Set Up Roles (Groups)

1. From the sidebar, click **"Groups (Roles)"**
2. Click **"Add Group"** button
3. Name the group (e.g., "Operators", "Viewers")
4. Select permissions
5. Save

### Organize Users by Permissions

**Example Role Structure:**
- **Administrators** - Superuser flag for full access
- **IT Operators** - Staff + change permissions for devices/networks
- **Network Team** - Edit access to network-related nodes only
- **Viewers** - Read-only access to specific node types

### Start Adding Data

Navigate to any node type from the dashboard and start creating entries:
- Devices
- Networks
- IP Addresses
- Departments
- People
- And more...

## Troubleshooting

### "I forgot my password!"

Reset it using Django's command:
```bash
python manage.py changepassword username
```

### "No users found" when running setup_admin.py

That's fine! It means you're starting fresh. Continue with the setup.

### "User already exists"

If you already have users but can't remember the password:

1. **Check existing users:**
   ```bash
   python manage.py shell
   >>> from django.contrib.auth.models import User
   >>> User.objects.values_list('username', 'is_superuser', 'is_active')
   ```

2. **Reset a password:**
   ```bash
   python manage.py changepassword existing_username
   ```

3. **Or create a new admin:**
   ```bash
   python manage.py createsuperuser --username newadmin
   ```

### "Cannot connect to Neo4j"

Don't worry! User authentication works independently of Neo4j. You can still:
- Log in
- Create users
- Manage permissions

Neo4j is only needed for the CMDB features (nodes, relationships, etc.).

### "Permission denied" errors

Make sure you're using a superuser account. If you created a regular user by mistake:

```bash
python manage.py shell
>>> from django.contrib.auth.models import User
>>> user = User.objects.get(username='username')
>>> user.is_superuser = True
>>> user.is_staff = True
>>> user.save()
>>> exit()
```

## Security Notes

### Password Requirements

Django enforces these password rules by default:
- At least 8 characters
- Not entirely numeric
- Not too similar to username
- Not a commonly used password

### Best Practices

1. **Use strong passwords** - Mix uppercase, lowercase, numbers, symbols
2. **Don't share admin credentials** - Create separate accounts for each person
3. **Use groups for permissions** - Don't give everyone superuser access
4. **Deactivate unused accounts** - Set `is_active=False` instead of deleting
5. **Regular audits** - Review user list periodically

## Need Help?

- **Full Documentation**: See `docs/USERS_AND_RBAC.md`
- **Quick Reference**: See `README.md`
- **Issues**: Open an issue on GitHub

## Quick Command Reference

| Task | Command |
|------|---------|
| Create first admin | `python setup_admin.py` or `python manage.py createsuperuser` |
| Reset password | `python manage.py changepassword username` |
| List all users | `python manage.py shell` → `User.objects.all()` |
| Make user admin | In Django admin or shell: `user.is_superuser = True; user.save()` |
| Run migrations | `python manage.py migrate` |
| Start server | `python manage.py runserver` |

---

**Still stuck?** Check the troubleshooting section in `README.md` or open an issue!
