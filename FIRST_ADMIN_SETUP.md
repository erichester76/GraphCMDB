# First Admin User Setup - Quick Guide

## ❓ Problem: "I can't log in because I don't have a user!"

**Solution**: You need to create your first admin user. Here's how to do it in 30 seconds.

---

## 🚀 Method 1: Interactive Setup Script (Easiest)

Just run this command:

```bash
python setup_admin.py
```

**You'll see:**

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

Additional resources:
  - Dashboard: http://localhost:8000/cmdb/
  - Admin Panel: http://localhost:8000/admin/
  - User Management: http://localhost:8000/users/list/
  - Documentation: docs/USERS_AND_RBAC.md
```

---

## 🎯 Method 2: Django Command (Standard Way)

```bash
python manage.py createsuperuser
```

**You'll be prompted:**

```
Username (leave blank to use 'yourname'): admin
Email address: admin@example.com
Password: 
Password (again): 
Superuser created successfully.
```

---

## ⚡ Method 3: Non-Interactive (For Scripts)

```bash
export DJANGO_SUPERUSER_PASSWORD='YourSecurePassword123!'
python manage.py createsuperuser \
  --noinput \
  --username admin \
  --email admin@example.com
```

This is useful for automated deployments or Docker containers.

---

## 🎉 After Creating Your Admin User

### 1. Start the server

```bash
python manage.py runserver
```

### 2. Go to the login page

Open your browser to: **http://localhost:8000/users/login/**

### 3. Log in with your credentials

Enter the username and password you just created.

### 4. You're in! 🎊

You'll see the dashboard with full admin access.

---

## 📋 What You Can Do Now

As an admin, you have access to:

### From the Navigation Bar (Top Right)
- **Profile** - View your account details
- **Admin** - Access Django admin panel
- **Logout** - Sign out

### From the Sidebar (Left)
- **Dashboard** - Overview of your CMDB
- **Audit Log** - Track all changes
- **Feature Packs** - Manage feature packs
- **Users** - Create and manage users
- **Groups (Roles)** - Set up permissions

### Create More Users

1. Click **"Users"** in the sidebar
2. Click **"Add User"** button
3. Fill in the details
4. Assign to groups for appropriate permissions
5. Save

### Set Up Roles

1. Click **"Groups (Roles)"** in the sidebar
2. Click **"Add Group"** button
3. Name it (e.g., "IT Operators", "Viewers")
4. Select permissions
5. Save

Now you can assign users to these groups!

---

## 🆘 Common Issues

### "I already ran the command but can't remember my password"

Reset it:
```bash
python manage.py changepassword admin
```

### "I see 'User already exists' error"

You already have users! Check who they are:
```bash
python manage.py shell
>>> from django.contrib.auth.models import User
>>> for u in User.objects.all():
...     print(f"{u.username} - {'Admin' if u.is_superuser else 'Regular'} - {'Active' if u.is_active else 'Inactive'}")
```

If you don't know the password for any of them, use `changepassword` to reset one.

### "django.db.utils.OperationalError: no such table"

You need to run migrations first:
```bash
python manage.py migrate
```

Then try creating the user again.

---

## 🔐 Security Tips

✅ **DO:**
- Use strong passwords (mix of letters, numbers, symbols)
- Create separate accounts for each person
- Use groups to assign permissions

❌ **DON'T:**
- Share admin credentials
- Use simple passwords like "admin123"
- Give everyone superuser access

---

## 📚 More Help

- **Full documentation**: [docs/USERS_AND_RBAC.md](docs/USERS_AND_RBAC.md)
- **Getting started guide**: [GETTING_STARTED.md](GETTING_STARTED.md)
- **Main README**: [README.md](README.md)

---

**Still stuck?** Open an issue on GitHub with:
- What command you ran
- What error you got
- What you were trying to do
