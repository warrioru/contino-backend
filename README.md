django backend

api crud
howdy post listener for requests
Installation

virtualenv -p /usr/bin/python3 env
source env/bin/activate
pip3 install Django
pip3 install djangorestframework

##para modificar schema
python3.7 manage.py makemigrations
python3.7 manage.py migrate

#correr el server
python3.7 manage.py runserver

#git
pip3 install gitpython
pip3 install pydriller

#postgres
pip3 install psycopg2

#comando de git para patch
git format-patch -1 --stdout > a.patch

#limpiar dir
git clean -fdx
git reset --hard

#volver a master branch
git reset --hard @{u}

#API conexion a Github
pip3 install PyGithub

#comando para ver q hay en el hash id
(printf "commit %s\0" $(git cat-file commit HEAD | wc -c); git cat-file commit HEAD)

#apscheduler
pip3 install apscheduler

