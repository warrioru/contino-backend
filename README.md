django backend

api crud
howdy post listener for requests
Installation

virtualenv -p /usr/bin/python3 env
source env/bin/activate
pip install Django
pip install djangorestframework

##para modificar schema
python manage.py makemigrations
python manage.py migrate

#correr el server
python manage.py runserver

#git
pip install gitpython
pip install pydriller

#postgres
pip install psycopg2

#comando de git para patch
git format-patch -1 --stdout > a.patch

#limpiar dir
git clean -fdx
git reset --hard

#volver a master branch
git reset --hard @{u}

#API conexion a Github
pip install PyGithub

#comando para ver q hay en el hash id
(printf "commit %s\0" $(git cat-file commit HEAD | wc -c); git cat-file commit HEAD)

