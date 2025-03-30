echo "INSTALLING DEPENDENCIES"
python3.9 -m pip install -r requirements.txt

echo "COLLECTING STATIC FILES"
python3.9 manage.py collectstatic --noinput 