# GraphCMDB

A Django-based Configuration Management Database (CMDB) using Neo4j graph database for dynamic inventory management.

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- Neo4j database (running on `bolt://neo4j:7687`)
- Node.js and npm (for Tailwind CSS)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/erichester76/GraphCMDB.git
   cd GraphCMDB
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install Node.js dependencies** (for Tailwind CSS)
   ```bash
   npm install
   ```

4. **Run database migrations**
   ```bash
   python manage.py migrate
   ```

5. **Create your first admin user** ⭐
   
   This is the most important step! You need an admin user to log in and manage the system.
   
   **Option 1: Interactive (Recommended)**
   ```bash
   python manage.py createsuperuser
   ```
   
   You'll be prompted for:
   - Username
   - Email address (optional)
   - Password (entered twice for confirmation)
   
   **Option 2: Using the setup script**
   ```bash
   python setup_admin.py
   ```
   
   This script will guide you through creating your first admin user.
   
   **Option 3: Non-interactive (for automation)**
   ```bash
   # Set password via environment variable
   export DJANGO_SUPERUSER_PASSWORD='your-secure-password'
   python manage.py createsuperuser --noinput --username admin --email admin@example.com
   ```

6. **Compile Tailwind CSS**
   ```bash
   npm run build
   ```

7. **Start the development server**
   ```bash
   python manage.py runserver
   ```

8. **Access the application**
   - Main application: http://localhost:8000/cmdb/
   - Login page: http://localhost:8000/users/login/
   - Admin panel: http://localhost:8000/admin/

## 🔐 First Time Login

After creating your admin user:

1. Navigate to http://localhost:8000/users/login/
2. Enter your username and password
3. You'll be redirected to the dashboard
4. From the sidebar, you can access:
   - **Users** - Manage system users
   - **Groups (Roles)** - Manage user roles and permissions
   - **Admin** - Access Django admin panel for detailed configuration

## 📚 Features

### Core Features
- **Dynamic Node Types**: Create and manage custom node types via feature packs
- **Graph Relationships**: Connect nodes with typed relationships
- **Audit Logging**: Track all changes to nodes and relationships
- **Feature Packs**: Modular system for extending functionality
- **Dark Mode**: Full dark mode support across the entire UI

### Authentication & RBAC
- **User Authentication**: Secure login/logout with session management
- **Role-Based Access Control**: Fine-grained permissions via groups
- **Three Permission Levels**:
  - **Superuser**: Full system access
  - **Staff**: User management + broad permissions
  - **Regular User**: Group-based permissions

### Feature Packs
- **Network Pack**: Interfaces, Cables, Circuits, VLANs
- **IPAM Pack**: Networks, IP Addresses, MAC Addresses
- **Data Center Pack**: Racks, Devices, Rack Units
- **Organization Pack**: People, Departments, Sites, Buildings
- **Virtualization Pack**: Virtual Machines, Hosts, Clusters
- **ITSM Pack**: Issues, Problems, Changes, Releases, Events
- **DNS Pack**: DNS Zones, Records, Views
- **DHCP Pack**: DHCP Scopes, Leases
- **Vendor Management Pack**: Vendors, Contracts
- **Audit Log Pack**: Comprehensive audit trail

## 📖 Documentation

- **[Users and RBAC Guide](docs/USERS_AND_RBAC.md)** - Complete guide to authentication and permissions
- **[Users Implementation Summary](USERS_RBAC_SUMMARY.md)** - Overview of the auth system
- **[Audit Log Implementation](AUDIT_LOG_IMPLEMENTATION.md)** - Audit logging details
- **[Dark Mode Implementation](DARK_MODE_AUDIT_LOG.md)** - Dark mode features

## 🛠️ Common Tasks

### Creating Additional Users

**Via Web Interface:**
1. Log in as an admin
2. Click "Users" in the sidebar
3. Click "Add User" button
4. Fill in user details
5. Assign to groups for permissions

**Via Command Line:**
```bash
python manage.py createsuperuser  # Creates another admin
# or use the Django admin interface for regular users
```

### Managing Permissions

1. Navigate to http://localhost:8000/users/groups/
2. Create groups representing roles (e.g., "Operators", "Viewers")
3. Assign permissions to groups
4. Add users to groups

### Importing Data

Navigate to any node type list page and click the "Import" button to bulk import data from CSV/Excel files.

## 🔧 Configuration

### Database Settings

Edit `core/settings.py`:

```python
# Neo4j connection
NEO4J_BOLT_URL = 'bolt://neo4j:7687'

# Django auth database (SQLite by default)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
```

### Authentication Settings

```python
LOGIN_URL = '/users/login/'
LOGIN_REDIRECT_URL = '/cmdb/'
LOGOUT_REDIRECT_URL = '/users/login/'
```

## 🧪 Testing

Run the test suite:

```bash
# All tests
python manage.py test

# Just user authentication tests
python manage.py test users

# Specific test class
python manage.py test users.tests.AuthenticationTestCase
```

## 🚨 Troubleshooting

### "I can't log in"

1. **Did you create an admin user?** 
   - Run `python manage.py createsuperuser` if you haven't yet
   
2. **Is the user active?**
   - Check in Django admin or database that `is_active=True`
   
3. **Forgot password?**
   - Reset via Django admin or command line:
     ```bash
     python manage.py changepassword username
     ```

### "Neo4j connection failed"

- Ensure Neo4j is running on `bolt://neo4j:7687`
- Check Neo4j credentials
- The app will still work for user authentication even if Neo4j is down

### "Static files not loading"

```bash
# Rebuild Tailwind CSS
npm run build

# Collect static files (production)
python manage.py collectstatic
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `python manage.py test`
5. Submit a pull request

## 📝 License

[Add your license here]

## 🙋 Support

For issues and questions:
- Check the documentation in the `docs/` folder
- Open an issue on GitHub
- Review the troubleshooting section above

## 🎯 Quick Reference

| Task | Command/URL |
|------|-------------|
| Create first admin | `python manage.py createsuperuser` |
| Login page | http://localhost:8000/users/login/ |
| Admin panel | http://localhost:8000/admin/ |
| Dashboard | http://localhost:8000/cmdb/ |
| Run server | `python manage.py runserver` |
| Run tests | `python manage.py test` |
| Build CSS | `npm run build` |
| Create user | Django admin → Users → Add user |
| Manage permissions | http://localhost:8000/users/groups/ |
