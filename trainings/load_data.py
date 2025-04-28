# load_initial_data.py
import os
import django
import sys

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'training_monitor.settings')
  # <<== CHANGE THIS to your real project folder
django.setup()

# Import models
from trainings.models import Province, District

# Optional: Clear old data (only if needed)
Province.objects.all().delete()
District.objects.all().delete()

# Create Provinces
kigali = Province.objects.create(name="Kigali")
southern = Province.objects.create(name="Southern")
northern = Province.objects.create(name="Northern")
eastern = Province.objects.create(name="Eastern")
western = Province.objects.create(name="Western")

# Create Districts

# Kigali
District.objects.create(name="Gasabo", province=kigali)
District.objects.create(name="Kicukiro", province=kigali)
District.objects.create(name="Nyarugenge", province=kigali)

# Southern
District.objects.create(name="Gisagara", province=southern)
District.objects.create(name="Huye", province=southern)
District.objects.create(name="Kamonyi", province=southern)
District.objects.create(name="Muhanga", province=southern)
District.objects.create(name="Nyamagabe", province=southern)
District.objects.create(name="Nyanza", province=southern)
District.objects.create(name="Nyaruguru", province=southern)
District.objects.create(name="Ruhango", province=southern)

# Northern
District.objects.create(name="Burera", province=northern)
District.objects.create(name="Gakenke", province=northern)
District.objects.create(name="Gicumbi", province=northern)
District.objects.create(name="Musanze", province=northern)
District.objects.create(name="Rulindo", province=northern)

# Eastern
District.objects.create(name="Bugesera", province=eastern)
District.objects.create(name="Gatsibo", province=eastern)
District.objects.create(name="Kayonza", province=eastern)
District.objects.create(name="Kirehe", province=eastern)
District.objects.create(name="Ngoma", province=eastern)
District.objects.create(name="Nyagatare", province=eastern)
District.objects.create(name="Rwamagana", province=eastern)

# Western
District.objects.create(name="Karongi", province=western)
District.objects.create(name="Ngororero", province=western)
District.objects.create(name="Nyabihu", province=western)
District.objects.create(name="Nyamasheke", province=western)
District.objects.create(name="Rubavu", province=western)
District.objects.create(name="Rusizi", province=western)
District.objects.create(name="Rutsiro", province=western)

print("✅ Provinces and Districts loaded successfully!")
