m #!/bin/bash
echo "========================================="
echo "  OnyxPOS Backend Deployment Readiness"
echo "========================================="
echo ""

# Check critical files exist
echo "📁 Checking critical files..."
files=(
    "app.py"
    "models.py"
    "database.py"
    "config.py"
    "requirements.txt"
    "Procfile"
    "railway.json"
    "runtime.txt"
    "middleware/subscription_guard.py"
    "services/stripe_metered.py"
    "services/email.py"
    "jobs/monthly_billing.py"
    "jobs/dunning_check.py"
    "jobs/trial_reminders.py"
)

all_exist=true
for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✅ $file"
    else
        echo "  ❌ $file MISSING!"
        all_exist=false
    fi
done

echo ""
echo "📦 Checking requirements.txt..."
required_packages=("flask" "sqlalchemy" "stripe" "sendgrid" "gunicorn" "psycopg2-binary")
for pkg in "${required_packages[@]}"; do
    if grep -q "$pkg" requirements.txt; then
        echo "  ✅ $pkg"
    else
        echo "  ❌ $pkg MISSING!"
    fi
done

echo ""
echo "🔧 Checking configuration files..."
if grep -q "release: python database.py" Procfile; then
    echo "  ✅ Procfile has release command"
else
    echo "  ❌ Procfile missing release command"
fi

if grep -q "python-3.11" runtime.txt; then
    echo "  ✅ Runtime set to Python 3.11"
else
    echo "  ⚠️  Runtime not set to Python 3.11"
fi

if [ -f ".gitignore" ]; then
    echo "  ✅ .gitignore present"
else
    echo "  ⚠️  .gitignore missing"
fi

echo ""
echo "🚀 Checking API blueprints in app.py..."
blueprints=("auth_bp" "billing_bp" "billing_gmv_bp" "diagnostics_bp")
for bp in "${blueprints[@]}"; do
    if grep -q "$bp" app.py; then
        echo "  ✅ $bp registered"
    else
        echo "  ❌ $bp NOT registered"
    fi
done

echo ""
echo "========================================="
if $all_exist; then
    echo "✅ READY TO DEPLOY!"
    echo ""
    echo "Next steps:"
    echo "1. Push to GitHub: git add . && git commit -m 'Ready for deployment' && git push"
    echo "2. Go to Railway.app and deploy from GitHub"
    echo "3. Add PostgreSQL database"
    echo "4. Configure environment variables"
    echo "5. Deploy and test!"
else
    echo "❌ NOT READY - Fix missing files above"
fi
echo "========================================="
